from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
import uuid

from database import get_db
from app.models.scan import CodeScan
from app.schemas.scan import ScanCreateRequest, ScanResponse
from app.services.tree_sitter_engine import UniversalTreeSitterEngine
from app.services.llm_engine import analyze_code_with_llm
from app.services.report_formatter import format_analysis_report

router = APIRouter(prefix="/api/v1", tags=["scans"])

# Endpoint to analyze code and store results
@router.post("/analyze", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def analyze_code(request: ScanCreateRequest, db: AsyncSession = Depends(get_db)):
    # --> Execute local AST Static Analysis
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

    # --> Execute Structured AI Pipeline via Groq
    try:
        ai_result = await analyze_code_with_llm(request.code, ast_result)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to process AI analysis: {str(e)}"
        )

    # --> Save combined analysis record to PostgreSQL
    scan_record = CodeScan(
        title=request.title,
        language=request.language,
        raw_code=request.code,
        ast_metrics=ast_result,
        time_complexity=ai_result.time_complexity,
        space_complexity=ai_result.space_complexity,
        security_score=ai_result.security_score,
        maintainability_score=ai_result.maintainability_score,
        refactored_code=ai_result.refactored_code,
        issues_list=[issue.model_dump() for issue in ai_result.issues],
        summary_text=format_analysis_report(
            request.title, request.language, ast_result, ai_result
        ),
    )

    db.add(scan_record)
    await db.commit()
    await db.refresh(scan_record)

    return scan_record

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