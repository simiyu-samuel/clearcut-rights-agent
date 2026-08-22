from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ProjectStatus = Literal["draft", "active", "review", "complete", "archived"]
JobStatus = Literal["queued", "running", "awaiting_review", "completed", "failed"]


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
