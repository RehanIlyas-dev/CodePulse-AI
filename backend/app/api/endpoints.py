import asyncio
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import get_db
from app.models.scan import CodeScan
from app.schemas.scan import ScanCreateRequest, ScanResponse
from app.services.cache_service import CacheService
from app.services.job_service import JobService
from app.services.orchestrator import run_analysis_pipeline
from app.services.tree_sitter_engine import UniversalTreeSitterEngine
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/api/v1", tags=["scans"])

_background_tasks: set = set()


# Endpoint to submit code for analysis (returns a job id immediately)
@router.post("/analyze", status_code=status.HTTP_202_ACCEPTED)
async def analyze_code(request: ScanCreateRequest):
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

    # --> Kick off background analysis pipeline
    code_hash = CacheService.generate_code_hash(request.code, request.language)
    job_id = str(uuid.uuid4())
    await JobService.create_job(job_id)
    
    task = asyncio.create_task(
        run_analysis_pipeline(job_id, request.title, request.code, request.language, code_hash)
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
async def job_websocket(websocket: WebSocket, job_id: str):
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
# 1. Get all scans with pagination
@router.get("/scans", response_model=List[ScanResponse])
async def get_all_scans(limit: int = 10, offset: int = 0, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CodeScan).order_by(CodeScan.created_at.desc()).offset(offset).limit(limit)
    )
    return result.scalars().all()

# 2. Get a specific scan by its UUID
@router.get("/scans/{scan_id}", response_model=ScanResponse)
async def get_scan_by_id(scan_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CodeScan).filter(CodeScan.id == scan_id))
    scan = result.scalars().first()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan record not found.")

    return scan