from database import AsyncSessionLocal
from app.models.scan import CodeScan
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