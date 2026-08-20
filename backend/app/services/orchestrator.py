from pathlib import Path
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
from app.services.report_formatter import format_analysis_report
from app.services.websocket_manager import ws_manager


async def run_analysis_pipeline(
    job_id: str,
    title: str,
    code: str,
    language: str,
    code_hash: str,
):
    """
    Executes AST parsing and AI auditing out-of-band in a background task,
    publishing stage updates to Redis and connected WebSockets.
    """
    try:
        cached = await CacheService.get_cached_analysis(code_hash)
        if cached:
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

        # --> AI Audit via Groq LLM
        await JobService.update_job(job_id, "RUNNING_AI_AUDIT", 65)
        await ws_manager.send_progress(job_id, "RUNNING_AI_AUDIT", 65)

        ai_result = await analyze_code_with_llm(
            code=code,
            ast_metrics=ast_result
        )

        # --> Persist scan record to PostgreSQL
        scan_record = CodeScan(
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
            summary_text=format_analysis_report(title, language, ast_result, ai_result),
        )
        async with AsyncSessionLocal() as db:
            db.add(scan_record)
            await db.commit()
            await db.refresh(scan_record)

        # --> Construct Output Payload
        response_payload = {
            "id": str(scan_record.id),
            "language": ast_result["language"],
            "ast_metrics": ast_result,
            "time_complexity": ai_result.time_complexity,
            "space_complexity": ai_result.space_complexity,
            "security_score": ai_result.security_score,
            "maintainability_score": ai_result.maintainability_score,
            "refactored_code": ai_result.refactored_code,
            "issues_list": [issue.model_dump() for issue in ai_result.issues],
            "summary_text": scan_record.summary_text,
            "cached": False,
        }

        # --> Write Result to Redis Cache
        await CacheService.set_cached_analysis(code_hash, response_payload)

        # --> Finalize Job State
        await JobService.update_job(job_id, "COMPLETED", 100, response_payload)
        await ws_manager.send_progress(job_id, "COMPLETED", 100, response_payload)

    except Exception as e:
        # Handle failures gracefully without crashing background threads
        error_payload = {"error": str(e)}
        await JobService.update_job(job_id, "FAILED", 0, error_payload)
        await ws_manager.send_progress(job_id, "FAILED", 0, error_payload)
        
async def run_repo_analysis_pipeline(job_id: str, repo_path: Path, source: str):
    """
    Background worker task for parsing and auditing an entire repository.
    """
    try:
        await JobService.update_job(job_id, "PARSING_FILES", 20)
        await ws_manager.send_progress(job_id, "PARSING_FILES", 20)

        parsed_data = ProjectParser.parse_repository(repo_path)

        await JobService.update_job(job_id, "BUILDING_DEPENDENCY_GRAPH", 50)
        await ws_manager.send_progress(job_id, "BUILDING_DEPENDENCY_GRAPH", 50)

        project_graph = DependencyGraphBuilder.build_graph(parsed_data)

        await JobService.update_job(job_id, "RUNNING_AI_AUDIT", 80)
        await ws_manager.send_progress(job_id, "RUNNING_AI_AUDIT", 80)

        # Compact summary passed to LLM instead of raw source code files
        ai_summary = await analyze_code_with_llm(
            code=f"Project Summary: {project_graph['summary']}",
            ast_metrics={"language": "project_aggregate", "file_count": project_graph['summary']['total_files']}
        )

        # --> Persist repository scan to PostgreSQL
        repo_scan = RepoScan(
            source=source,
            summary=project_graph["summary"],
            dependency_graph=project_graph["dependency_graph"],
            files=project_graph["files"],
            architecture_score=ai_summary.security_score,
            maintainability_score=ai_summary.maintainability_score,
            refactored_suggestions=ai_summary.refactored_code,
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
            "refactored_suggestions": ai_summary.refactored_code
        }

        # Step 4: Finalize Job and Notify Websocket
        await JobService.update_job(job_id, "COMPLETED", 100, response_payload)
        await ws_manager.send_progress(job_id, "COMPLETED", 100, response_payload)

    except Exception as e:
        error_payload = {"error": str(e)}
        await JobService.update_job(job_id, "FAILED", 0, error_payload)
        await ws_manager.send_progress(job_id, "FAILED", 0, error_payload)

    finally:
        WorkspaceManager.cleanup(repo_path)