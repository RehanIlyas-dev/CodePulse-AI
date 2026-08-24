from pathlib import Path
import asyncio
import sentry_sdk
from app.services.workspace_manager import WorkspaceManager
from app.services.project_parser import ProjectParser
from app.services.dependency_builder import DependencyGraphBuilder
from database import AsyncSessionLocal
from app.models.scan import CodeScan
from app.models.repo_scan import RepoScan
from app.services.tree_sitter_engine import UniversalTreeSitterEngine
from app.services.llm_engine import analyze_code_with_llm
from app.services.cache_service import CacheService
from app.services.job_service import JobService
from app.services.report_formatter import format_analysis_report, format_repo_report
from app.services.websocket_manager import ws_manager


async def run_analysis_pipeline(
    job_id: str,
    title: str,
    code: str,
    language: str,
    code_hash: str,
    user_id: str | None = None,
):
    """
    Executes AST parsing and AI auditing out-of-band in a background task,
    publishing stage updates to Redis and connected WebSockets.
    """
    try:
        cached = await CacheService.get_cached_analysis(code_hash)
        if cached:
            # A cached result may have been produced anonymously (no record id).
            # Signed-in users still get a history row - no LLM call needed.
            if user_id and not cached.get("id"):
                scan_record = CodeScan(
                    user_id=user_id,
                    title=title,
                    language=language,
                    raw_code=code,
                    ast_metrics=cached.get("ast_metrics"),
                    time_complexity=cached["time_complexity"],
                    space_complexity=cached["space_complexity"],
                    security_score=cached["security_score"],
                    maintainability_score=cached["maintainability_score"],
                    refactored_code=cached["refactored_code"],
                    issues_list=cached["issues_list"],
                    summary_text=cached["summary_text"],
                )
                async with AsyncSessionLocal() as db:
                    db.add(scan_record)
                    await db.commit()
                    await db.refresh(scan_record)
                cached["id"] = str(scan_record.id)

            cached["cached"] = True
            await JobService.update_job(job_id, "CACHE_HIT", 100, cached)
            await ws_manager.send_progress(job_id, "CACHE_HIT", 100, cached)
            return

        # --> Tree-sitter AST Parsing
        await JobService.update_job(job_id, "PARSING_AST", 25)
        await ws_manager.send_progress(job_id, "PARSING_AST", 25)

        ast_result = UniversalTreeSitterEngine.analyze(
            code=code,
            language=language
        )

        # --> AI Audit via LLM
        await JobService.update_job(job_id, "RUNNING_AI_AUDIT", 65)
        await ws_manager.send_progress(job_id, "RUNNING_AI_AUDIT", 65)

        ai_result = await analyze_code_with_llm(
            code=code,
            ast_metrics=ast_result
        )

        # --> Persist scan record to PostgreSQL (signed-in users only)
        summary_text = format_analysis_report(title, language, ast_result, ai_result)
        scan_record_id = None
        if user_id:
            scan_record = CodeScan(
                user_id=user_id,
                title=title,
                language=language,
                raw_code=code,
                ast_metrics=ast_result,
                time_complexity=ai_result.time_complexity,
                space_complexity=ai_result.space_complexity,
                security_score=ai_result.security_score,
                maintainability_score=ai_result.maintainability_score,
                refactored_code=ai_result.refactored_code,
                issues_list=[issue.model_dump() for issue in ai_result.issues],
                summary_text=summary_text,
            )
            async with AsyncSessionLocal() as db:
                db.add(scan_record)
                await db.commit()
                await db.refresh(scan_record)
            scan_record_id = str(scan_record.id)

        # --> Construct Output Payload
        response_payload = {
            "id": scan_record_id,
            "language": ast_result["language"],
            "ast_metrics": ast_result,
            "time_complexity": ai_result.time_complexity,
            "space_complexity": ai_result.space_complexity,
            "security_score": ai_result.security_score,
            "maintainability_score": ai_result.maintainability_score,
            "refactored_code": ai_result.refactored_code,
            "issues_list": [issue.model_dump() for issue in ai_result.issues],
            "summary_text": summary_text,
            "cached": False,
        }

        # --> Write Result to Redis Cache
        await CacheService.set_cached_analysis(code_hash, response_payload)

        # --> Finalize Job State
        await JobService.update_job(job_id, "COMPLETED", 100, response_payload)
        await ws_manager.send_progress(job_id, "COMPLETED", 100, response_payload)

    except Exception as e:
        # Handle failures gracefully without crashing background threads
        # Background exceptions are swallowed here, so report them to Sentry explicitly
        with sentry_sdk.new_scope() as scope:
            scope.set_tag("pipeline", "code_analysis")
            scope.set_tag("job_id", job_id)
            scope.set_extra("language", language)
            sentry_sdk.capture_exception(e)

        error_payload = {"error": str(e)}
        await JobService.update_job(job_id, "FAILED", 0, error_payload)
        await ws_manager.send_progress(job_id, "FAILED", 0, error_payload)
        
async def run_repo_analysis_pipeline(job_id: str, repo_path: Path, source: str, repo_hash: str, user_id: str | None = None):
    """
    Background worker task for parsing and auditing an entire repository.
    Every supported file gets a full LLM analysis (bounded concurrency);
    repos beyond MAX_LLM_FILES get deep analysis on the most complex files only.
    """
    MAX_LLM_FILES = 8
    MAX_FILE_CHARS = 12_000

    try:
        await JobService.update_job(job_id, "PARSING_FILES", 20)
        await ws_manager.send_progress(job_id, "PARSING_FILES", 20)

        parsed_data = ProjectParser.parse_repository(repo_path)

        await JobService.update_job(job_id, "BUILDING_DEPENDENCY_GRAPH", 35)
        await ws_manager.send_progress(job_id, "BUILDING_DEPENDENCY_GRAPH", 35)

        project_graph = DependencyGraphBuilder.build_graph(parsed_data)
        files = project_graph["files"]

        # --> Per-file deep AI audit (bounded concurrency)
        sem = asyncio.Semaphore(3)

        async def analyze_one(rel_path: str, info: dict):
            async with sem:
                try:
                    abs_path = Path(repo_path) / rel_path
                    code = abs_path.read_text(encoding="utf-8", errors="ignore")[:MAX_FILE_CHARS]
                    result = await analyze_code_with_llm(code=code, ast_metrics=info["metrics"])
                    return rel_path, {
                        "time_complexity": result.time_complexity,
                        "space_complexity": result.space_complexity,
                        "security_score": result.security_score,
                        "maintainability_score": result.maintainability_score,
                        "issues": [i.model_dump() for i in result.issues],
                        "refactored_code": result.refactored_code,
                    }
                except Exception:
                    # One bad file must not fail the whole repo job
                    return rel_path, None

        candidates = sorted(
            files.keys(),
            key=lambda p: files[p]["metrics"].get("cyclomatic_complexity", 1),
            reverse=True,
        )[:MAX_LLM_FILES]

        await JobService.update_job(job_id, "RUNNING_AI_AUDIT", 40)
        await ws_manager.send_progress(job_id, "RUNNING_AI_AUDIT", 40)

        tasks = [asyncio.create_task(analyze_one(p, files[p])) for p in candidates]
        completed_count = 0
        for coro in asyncio.as_completed(tasks):
            rel_path, ai = await coro
            completed_count += 1
            if ai:
                files[rel_path]["ai"] = ai
            progress = 40 + int(45 * completed_count / max(len(candidates), 1))
            await JobService.update_job(job_id, "RUNNING_AI_AUDIT", progress)
            await ws_manager.send_progress(job_id, "RUNNING_AI_AUDIT", progress)

        # --> Aggregate project-wide audit (single compact-summary call)
        ai_summary = await analyze_code_with_llm(
            code=f"Project Summary: {project_graph['summary']}",
            ast_metrics={"language": "project_aggregate", "file_count": project_graph['summary']['total_files']}
        )

        # --> Persist repository scan to PostgreSQL (signed-in users only)
        repo_scan = RepoScan(
            user_id=user_id,
            source=source,
            summary=project_graph["summary"],
            dependency_graph=project_graph["dependency_graph"],
            files=project_graph["files"],
            architecture_score=ai_summary.security_score,
            maintainability_score=ai_summary.maintainability_score,
            refactored_suggestions=ai_summary.refactored_code,
            issues_list=[issue.model_dump() for issue in ai_summary.issues],
            summary_text=format_repo_report(
                source=source,
                summary=project_graph["summary"],
                files=project_graph["files"],
                dependency_graph=project_graph["dependency_graph"],
                architecture_score=ai_summary.security_score,
                maintainability_score=ai_summary.maintainability_score,
                refactored_suggestions=ai_summary.refactored_code,
            ),
        )
        async with AsyncSessionLocal() as db:
            db.add(repo_scan)
            await db.commit()
            await db.refresh(repo_scan)

        response_payload = {
            "id": str(repo_scan.id),
            "source": source,
            "summary": project_graph["summary"],
            "dependency_graph": project_graph["dependency_graph"],
            "files": project_graph["files"],
            "architecture_score": ai_summary.security_score,
            "maintainability_score": ai_summary.maintainability_score,
            "refactored_suggestions": ai_summary.refactored_code,
            "issues_list": [issue.model_dump() for issue in ai_summary.issues],
        }

        # --> Write Result to Redis Cache (24h TTL)
        await CacheService.set_cached_analysis(repo_hash, response_payload, key_prefix="repo:")

        # Step 4: Finalize Job and Notify Websocket
        await JobService.update_job(job_id, "COMPLETED", 100, response_payload)
        await ws_manager.send_progress(job_id, "COMPLETED", 100, response_payload)

    except Exception as e:
        # Background exceptions are swallowed here, so report them to Sentry explicitly
        with sentry_sdk.new_scope() as scope:
            scope.set_tag("pipeline", "repo_analysis")
            scope.set_tag("job_id", job_id)
            scope.set_extra("source", source)
            sentry_sdk.capture_exception(e)

        error_payload = {"error": str(e)}
        await JobService.update_job(job_id, "FAILED", 0, error_payload)
        await ws_manager.send_progress(job_id, "FAILED", 0, error_payload)

    finally:
        WorkspaceManager.cleanup(repo_path)