from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProjectStatus = Literal["draft", "active", "review", "complete", "archived"]
JobStatus = Literal["queued", "running", "awaiting_review", "completed", "failed"]
DocumentStatus = Literal["uploading", "uploaded", "processing", "analyzed", "failed"]
DocumentSourceKind = Literal["document", "video", "audio"]
RiskStatus = Literal[
    "high_risk",
    "needs_review",
    "likely_clear",
    "blocked",
    "insufficient_evidence",
    "approved_for_delivery",
]
ResearchStatus = Literal["queued", "running", "completed", "partial", "failed"]
ResearchSessionStatus = Literal["planned", "running", "completed", "partial", "failed"]
ResearchTaskStatus = Literal["queued", "running", "completed", "partial", "failed"]
CardStatus = Literal["pending_review", "approved", "needs_more_research", "rejected", "escalated"]
ApprovalDecision = Literal[
    "approve_next_action",
    "request_more_research",
    "mark_not_applicable",
    "reject",
    "escalate_to_legal",
]
OutreachDraftStatus = Literal[
    "draft", "approved", "sent", "response_received", "closed", "cancelled"
]
ReportStatus = Literal["ready", "failed"]
MembershipRole = Literal["admin", "producer", "coordinator", "legal_reviewer", "post_supervisor", "viewer"]
MembershipStatus = Literal["active", "invited", "suspended"]
InvitationStatus = Literal["pending", "accepted", "revoked", "expired"]
RecheckStatus = Literal["active", "paused"]
ProjectOptionType = Literal["project_type", "territory", "distribution_mode"]


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    project_type: str = Field(default="Feature film", min_length=1, max_length=80)
    territories: list[str] = Field(default_factory=list, max_length=20)
    distribution_modes: list[str] = Field(default_factory=list, max_length=10)
    target_release_at: datetime | None = None


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    project_type: str | None = Field(default=None, min_length=1, max_length=80)
    territories: list[str] | None = Field(default=None, max_length=20)
    distribution_modes: list[str] | None = Field(default=None, max_length=10)
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


class ProjectOptionRead(BaseModel):
    id: str
    option_type: ProjectOptionType
    label: str
    is_custom: bool = False


class ProjectOptionCreate(BaseModel):
    option_type: ProjectOptionType
    label: str = Field(min_length=1, max_length=120)


class WorkspaceOverviewRead(BaseModel):
    period_days: int
    project_count: int
    assets_reviewed: int
    assets_need_attention: int
    high_priority_items: int
    evidence_coverage: int
    research_runs: int
    parallel_sources: int


class MembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    organization_name: str | None = None
    actor_id: str
    display_name: str
    role: MembershipRole
    status: MembershipStatus
    created_at: datetime
    updated_at: datetime


class OrganizationInvitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    email: str
    display_name: str | None
    role: MembershipRole
    status: InvitationStatus
    invited_by_actor_id: str
    accepted_by_actor_id: str | None
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OrganizationInvitationCreate(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    display_name: str | None = Field(default=None, max_length=160)
    role: MembershipRole = "viewer"


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    slug: str | None = Field(default=None, min_length=2, max_length=120)


class AuthIdentityRead(BaseModel):
    actor_id: str
    email: str | None
    display_name: str


class AuthMeRead(BaseModel):
    identity: AuthIdentityRead
    memberships: list[MembershipRead]


class AnalysisRunCreate(BaseModel):
    document_id: str | None = Field(default=None, max_length=120)


class MediaUploadInit(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=3, max_length=120)
    size_bytes: int = Field(gt=0)


class MediaUploadSessionRead(BaseModel):
    document_id: str
    object_key: str
    upload_url: str
    source_kind: DocumentSourceKind
    expires_in_seconds: int


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
    source_kind: DocumentSourceKind
    media_metadata: dict[str, object]
    version_number: int
    parent_document_id: str | None
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
    priority: Literal["low", "medium", "high", "critical"]
    owner_id: str | None
    due_at: datetime | None
    next_action: str | None
    created_at: datetime
    updated_at: datetime


class AssetUpdate(BaseModel):
    priority: Literal["low", "medium", "high", "critical"] | None = None
    owner_id: str | None = Field(default=None, max_length=120)
    due_at: datetime | None = None
    next_action: str | None = Field(default=None, max_length=160)


class ResearchRunCreate(BaseModel):
    objective: str = Field(min_length=10, max_length=2000)
    query: str = Field(min_length=2, max_length=500)


class ResearchSessionCreate(BaseModel):
    objective: str | None = Field(default=None, min_length=10, max_length=2000)


class ResearchFollowUpCreate(BaseModel):
    objective: str | None = Field(default=None, min_length=10, max_length=2000)


class SourceRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    research_run_id: str
    task_id: str | None
    url: str
    title: str
    excerpt: str
    source_quality: str
    provider_session_id: str | None
    retrieved_at: datetime


class ResearchFindingRead(BaseModel):
    code: str
    kind: Literal["gap", "conflict", "quality", "next_step"]
    severity: Literal["low", "medium", "high"]
    title: str
    detail: str
    action: str


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


class ResearchTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    session_id: str
    research_run_id: str
    angle: str
    title: str
    objective: str
    query: str
    status: ResearchTaskStatus
    provider_request_id: str | None
    source_count: int = Field(ge=0)
    quality_tier: str
    gap_codes: list[str]
    findings: list[ResearchFindingRead]
    sources: list[SourceRecordRead] = Field(default_factory=list)
    error_code: str | None
    created_at: datetime
    updated_at: datetime


class ResearchSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    asset_id: str
    provider: str
    objective: str
    status: ResearchSessionStatus
    total_tasks: int = Field(ge=0)
    completed_tasks: int = Field(ge=0)
    findings: list[ResearchFindingRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    tasks: list[ResearchTaskRead] = Field(default_factory=list)


class ResearchRecheckCreate(BaseModel):
    cadence_days: int = Field(default=30, ge=1, le=365)


class ResearchRecheckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    asset_id: str
    cadence_days: int
    next_run_at: datetime
    last_run_at: datetime | None
    last_session_id: str | None
    active: bool
    created_by: str
    created_at: datetime
    updated_at: datetime


class PlaybookRead(BaseModel):
    category: str
    rights_questions: list[str]
    required_evidence: list[str]
    recommended_actions: list[str]
    escalation_signals: list[str]


class ClearanceCardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    asset_id: str
    research_run_id: str
    generated_by: str
    model_name: str | None
    status: CardStatus
    risk_score: int = Field(ge=0, le=100)
    confidence_score: float = Field(ge=0, le=1)
    summary: str
    recommendation: str
    reason_codes: list[str]
    evidence_count: int = Field(ge=0)
    needs_human_review: bool
    created_at: datetime
    updated_at: datetime


class ApprovalCreate(BaseModel):
    decision: ApprovalDecision
    note: str | None = Field(default=None, max_length=2000)


class ApprovalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    asset_id: str
    clearance_card_id: str
    decision: ApprovalDecision
    note: str | None
    actor_id: str
    supersedes_id: str | None
    created_at: datetime


class OutreachDraftCreate(BaseModel):
    recipient_hint: str = Field(
        default="Rights and licensing contact", min_length=2, max_length=255
    )


class OutreachDraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    asset_id: str
    clearance_card_id: str
    recipient_hint: str
    recipient_email: str | None
    subject: str
    body: str
    terms: dict[str, str]
    response_note: str | None
    responded_at: datetime | None
    due_at: datetime | None
    status: OutreachDraftStatus
    generated_by: str
    created_by: str
    approved_by: str | None
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OutreachDraftUpdate(BaseModel):
    status: Literal["draft", "approved", "sent", "response_received", "closed", "cancelled"] | None = None
    recipient_email: str | None = Field(default=None, max_length=320)
    response_note: str | None = Field(default=None, max_length=4000)
    due_at: datetime | None = None
    terms: dict[str, str] | None = None


class AssetCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    mention_ids: list[str] = Field(default_factory=list, max_length=20)


class AssetCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    asset_id: str
    author_id: str
    body: str
    mention_ids: list[str]
    created_at: datetime
    updated_at: datetime


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    actor_id: str
    notification_type: str
    title: str
    body: str
    resource_type: str
    resource_id: str
    read_at: datetime | None
    created_at: datetime


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    actor_type: str
    actor_id: str
    action: str
    resource_type: str
    resource_id: str
    metadata_json: str | None
    created_at: datetime


class DeliveryReadinessRead(BaseModel):
    project_id: str
    status: Literal["not_ready", "conditional", "ready"]
    total_assets: int
    clear_assets: int
    unresolved_assets: int
    blocked_assets: int
    stale_rechecks: int
    open_requests: int
    required_actions: list[str]


class DocumentDiffRead(BaseModel):
    project_id: str
    from_document_id: str
    to_document_id: str
    added_lines: int
    removed_lines: int
    changed_lines: int
    added_assets: list[str]
    removed_assets: list[str]


class ProjectAttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    project_id: str
    asset_id: str | None
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    attachment_type: str
    created_by: str
    created_at: datetime


class ReviewShareCreate(BaseModel):
    label: str = Field(default="External review", min_length=2, max_length=160)
    expires_at: datetime | None = None


class ReviewShareRead(BaseModel):
    id: str
    project_id: str
    label: str
    expires_at: datetime | None
    revoked_at: datetime | None
    created_by: str
    created_at: datetime
    share_token: str | None = None


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)


class ApiKeyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    key_prefix: str
    created_by: str
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    secret: str | None = None


class WebhookEndpointCreate(BaseModel):
    url: str = Field(min_length=8, max_length=2000)
    event_types: list[str] = Field(default_factory=list, max_length=20)


class WebhookEndpointRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    url: str
    event_types: list[str]
    active: bool
    created_by: str
    created_at: datetime


class ClearanceReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    project_id: str
    report_type: str
    status: ReportStatus
    generated_by: str
    content_markdown: str
    version_number: int
    content_hash: str | None
    policy_version: str | None
    source_snapshot_at: datetime | None
    created_at: datetime
