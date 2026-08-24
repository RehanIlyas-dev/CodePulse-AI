import asyncio
import hashlib
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, BackgroundTasks, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import get_db, AsyncSessionLocal
from app.models.scan import CodeScan
from app.models.repo_scan import RepoScan
from app.schemas.scan import ScanCreateRequest, ScanResponse, RepoScanResponse
from app.services.cache_service import CacheService
from app.services.job_service import JobService
from app.services.orchestrator import run_analysis_pipeline
from app.services.tree_sitter_engine import UniversalTreeSitterEngine
from app.services.websocket_manager import ws_manager
from app.services.workspace_manager import WorkspaceManager
from app.services.orchestrator import run_repo_analysis_pipeline
from app.core.rate_limiter import RateLimiter
from app.core.guardrails import PayloadGuardrails
from app.core.security import get_current_user, get_optional_user, decode_token
from app.models.user import User

router = APIRouter(prefix="/api/v1", tags=["scans"])

_background_tasks: set = set()

# Shared rate limiter for job-submitting endpoints
_rate_limiter = RateLimiter(requests_per_minute=10)


# Endpoint to submit code for analysis (returns a job id immediately)
@router.post("/analyze", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(_rate_limiter)])
async def analyze_code(
    request: ScanCreateRequest,
    current_user: User | None = Depends(get_optional_user),
):
    # --> Validate payload size and detect minified code
    PayloadGuardrails.validate_code_snippet(request.code)

    # --> Validate code via local Tree-sitter
    ast_result = UniversalTreeSitterEngine.analyze(request.code, request.language)

    if not ast_result.get("supported"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language: {request.language}"
        )

    if ast_result.get("has_syntax_errors"):
        raise HTTPException(
            status_code=400,
            detail=f"Syntax errors detected in the submitted {request.language} code."
        )

    # --> Kick off background analysis pipeline (persisted only for signed-in users)
    code_hash = CacheService.generate_code_hash(request.code, request.language)
    job_id = str(uuid.uuid4())
    await JobService.create_job(job_id)

    task = asyncio.create_task(
        run_analysis_pipeline(
            job_id, request.title, request.code, request.language, code_hash,
            user_id=str(current_user.id) if current_user else None,
        )
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return {
        "job_id": job_id,
        "status": "PENDING",
        "websocket_url": f"/api/v1/ws/jobs/{job_id}",
    }


# Poll job status from Redis (fallback for non-WebSocket clients)
@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    state = await JobService.get_job(job_id)
    if not state:
        raise HTTPException(status_code=404, detail="Job not found or expired.")
    return state


# WebSocket endpoint for live job progress
@router.websocket("/ws/jobs/{job_id}")
async def job_websocket(websocket: WebSocket, job_id: str, token: Optional[str] = None):
    # --> Progress streaming is open to anonymous clients: the job_id is an
    # unguessable UUID minted for this client (capability token). A supplied
    # token must still be valid.
    if token:
        try:
            decode_token(token, expected_typ="access")
        except HTTPException:
            await websocket.close(code=4401)
            return

    await ws_manager.connect(job_id, websocket)
    try:
        # Send the current job state immediately on connect
        state = await JobService.get_job(job_id)
        if state:
            await websocket.send_json({"job_id": job_id, **state})
        # Keep the connection alive and detect disconnects
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(job_id)
    except Exception:
        ws_manager.disconnect(job_id)


# --> Additional endpoints for retrieving scan records
# Get all scans with pagination (history is private: only your own scans)
@router.get("/scans", response_model=List[ScanResponse])
async def get_all_scans(
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CodeScan)
        .filter(CodeScan.user_id == current_user.id)
        .order_by(CodeScan.created_at.desc()).offset(offset).limit(limit)
    )
    return result.scalars().all()

# Get a specific scan by its UUID
@router.get("/scans/{scan_id}", response_model=ScanResponse)
async def get_scan_by_id(scan_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CodeScan).filter(CodeScan.id == scan_id))
    scan = result.scalars().first()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan record not found.")

    return scan

@router.post("/analyze-repo", status_code=202, dependencies=[Depends(_rate_limiter)])
async def analyze_repository(
    background_tasks: BackgroundTasks,
    github_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: User | None = Depends(get_optional_user),
):
    if not github_url and not file:
        raise HTTPException(status_code=400, detail="Provide either a github_url or a .zip file upload.")

    # --> Validate zip payload before touching it
    if file:
        PayloadGuardrails.validate_zip_upload(file)

    # --> Compute cache key BEFORE any clone/extract (avoids wasted network work on cache hit)
    if github_url:
        # Key by commit SHA so repo changes invalidate the cache naturally
        head_sha = WorkspaceManager.get_head_sha(github_url)
        repo_hash = hashlib.sha256(f"{github_url.strip().lower()}:{head_sha}".encode("utf-8")).hexdigest()
        source = github_url
    else:
        zip_bytes = await file.read()
        repo_hash = hashlib.sha256(zip_bytes).hexdigest()
        source = "zip upload"

    cached = await CacheService.get_cached_analysis(repo_hash, key_prefix="repo:")
    if cached:
        # Signed-in users get a history row even on cache hits (anon cache entries have no id)
        if current_user is not None and not cached.get("id") and "summary" in cached:
            repo_scan = RepoScan(
                user_id=str(current_user.id),
                source=source,
                summary=cached.get("summary"),
                dependency_graph=cached.get("dependency_graph"),
                files=cached.get("files"),
                architecture_score=cached.get("architecture_score", 0),
                maintainability_score=cached.get("maintainability_score", 0),
                refactored_suggestions=cached.get("refactored_suggestions", ""),
                issues_list=cached.get("issues_list", []),
                summary_text=cached.get("summary_text", ""),
            )
            async with AsyncSessionLocal() as db:
                db.add(repo_scan)
                await db.commit()
                await db.refresh(repo_scan)
            cached["id"] = str(repo_scan.id)

        cached["cached"] = True
        job_id = str(uuid.uuid4())
        await JobService.create_job(job_id)
        await JobService.update_job(job_id, "CACHE_HIT", 100, cached)
        return {"status": "CACHE_HIT", "job_id": job_id, "websocket_url": f"/api/v1/ws/jobs/{job_id}"}

    sandbox_dir = WorkspaceManager.create_sandbox()

    try:
        if github_url:
            WorkspaceManager.clone_github_repo(github_url, sandbox_dir)
        else:
            await WorkspaceManager.extract_zip(zip_bytes, sandbox_dir)

        # Create Job and Register in Redis
        job_id = str(uuid.uuid4())
        await JobService.create_job(job_id)

        #  Dispatch Heavy Task to Background Worker
        background_tasks.add_task(
            run_repo_analysis_pipeline,
            job_id=job_id,
            repo_path=sandbox_dir,
            source=source,
            repo_hash=repo_hash,
            user_id=str(current_user.id) if current_user else None,
        )

        return {"status": "PENDING", "job_id": job_id, "websocket_url": f"/api/v1/ws/jobs/{job_id}"}

    except Exception as e:
        WorkspaceManager.cleanup(sandbox_dir)
        raise HTTPException(status_code=400, detail=str(e))


# --> Repository scan history (private: only your own repo scans)
@router.get("/repo-scans", response_model=List[RepoScanResponse])
async def get_all_repo_scans(
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(RepoScan)
        .filter(RepoScan.user_id == current_user.id)
        .order_by(RepoScan.created_at.desc()).offset(offset).limit(limit)
    )
    return result.scalars().all()

# Get a specific repository scan by its UUID
@router.get("/repo-scans/{scan_id}", response_model=RepoScanResponse)
async def get_repo_scan_by_id(scan_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RepoScan).filter(RepoScan.id == scan_id))
    scan = result.scalars().first()

    if not scan:
        raise HTTPException(status_code=404, detail="Repo scan record not found.")

    return scan