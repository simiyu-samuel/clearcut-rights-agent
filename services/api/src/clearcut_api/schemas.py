from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProjectStatus = Literal["draft", "active", "review", "complete", "archived"]
JobStatus = Literal["queued", "running", "awaiting_review", "completed", "failed"]
DocumentStatus = Literal["uploaded", "processing", "analyzed", "failed"]
RiskStatus = Literal[
    "high_risk", "needs_review", "likely_clear", "blocked", "insufficient_evidence"
]
ResearchStatus = Literal["queued", "running", "completed", "partial", "failed"]


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    project_type: str = Field(default="Feature film", min_length=1, max_length=80)
    territories: list[str] = Field(default_factory=list, max_length=20)
    distribution_modes: list[str] = Field(default_factory=list, max_length=10)
    target_release_at: datetime | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    title: str
    project_type: str
    territories: list[str]
    distribution_modes: list[str]
    target_release_at: datetime | None
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime


class AnalysisRunCreate(BaseModel):
    document_id: str | None = Field(default=None, max_length=120)


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    project_id: str
    job_type: str
    status: JobStatus
    error_code: str | None
    created_at: datetime
    updated_at: datetime


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    project_id: str
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    project_id: str
    document_id: str
    canonical_name: str
    category: str
    context: str
    scene_reference: str | None
    source_start: int
    source_end: int
    extraction_confidence: float
    risk_status: RiskStatus
    reason_codes: list[str]
    created_at: datetime
    updated_at: datetime


class ResearchRunCreate(BaseModel):
    objective: str = Field(min_length=10, max_length=2000)
    query: str = Field(min_length=2, max_length=500)


class SourceRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    research_run_id: str
    url: str
    title: str
    excerpt: str
    source_quality: str
    retrieved_at: datetime


class ResearchRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    asset_id: str
    provider: str
    operation: str
    objective: str
    query: str
    status: ResearchStatus
    provider_request_id: str | None
    error_code: str | None
    created_at: datetime
    updated_at: datetime
