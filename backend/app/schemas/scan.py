from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

# --> 1. Pydantic Models for LLM  Analysis Results 
class IssueDetail(BaseModel):
    type: str = Field(..., description="Category: 'security', 'performance', 'bug', or 'style'")
    line_number: Optional[int] = Field(None, description="Line number where issue occurs")
    description: str = Field(..., description="Explanation of the issue")
    suggestion: str = Field(..., description="Actionable fix recommendation")

class AIAnalysisResult(BaseModel):
    time_complexity: str = Field(..., description="Big O time complexity, e.g., 'O(N)'")
    space_complexity: str = Field(..., description="Big O space complexity, e.g., 'O(1)'")
    security_score: int = Field(..., description="Security score from 0 to 100")
    maintainability_score: int = Field(..., description="Code quality/maintainability score from 0 to 100")
    issues: List[IssueDetail] = Field(default=[], description="List of identified vulnerabilities or issues")
    refactored_code: str = Field(..., description="Improved version of the provided code")


# --> 2. FastAPI Request & Response Schemas
class ScanCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    language: str = Field(default="python")
    code: str = Field(..., min_length=1)

class ScanResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime
    title: str
    language: str
    raw_code: str
    ast_metrics: dict
    time_complexity: str
    space_complexity: str
    security_score: int
    maintainability_score: int
    refactored_code: str
    issues_list: List[dict]
    summary_text: str

    class Config:
        from_attributes = True


# --> 3. Repository Analysis Schemas
class RepoScanResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime
    source: str
    summary: dict
    dependency_graph: dict
    files: dict
    architecture_score: int
    maintainability_score: int
    refactored_suggestions: str
    summary_text: str

    class Config:
        from_attributes = True