from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str = Field(min_length=8)
    role: Literal["super_admin", "admin", "center", "candidate"] = "candidate"


class InstitutionalUserCreate(BaseModel):
    email: str
    full_name: str
    initial_password: str = Field(min_length=12)
    role: Literal["admin", "center", "candidate"] = "center"
    reason: str = Field(min_length=5)


class UserRead(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserRoleUpdate(BaseModel):
    role: Literal["super_admin", "admin", "center", "candidate"]
    reason: str = Field(min_length=5)


class UserStatusUpdate(BaseModel):
    is_active: bool
    reason: str = Field(min_length=5)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=8)
    new_password: str = Field(min_length=12)


class UserPasswordReset(BaseModel):
    new_password: str = Field(min_length=12)
    reason: str = Field(min_length=5)


class CandidateCreate(BaseModel):
    first_name: str
    last_name: str
    identity_number: str
    phone: str
    permit_category: str = "B"


class CandidateRead(CandidateCreate):
    id: str
    reference: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CandidateOfficialImportRow(BaseModel):
    first_name: str = Field(min_length=2, max_length=120)
    last_name: str = Field(min_length=2, max_length=120)
    identity_number: str = Field(min_length=3, max_length=120)
    phone: str = Field(min_length=5, max_length=50)
    permit_category: str = Field(default="B", min_length=1, max_length=10)
    status: Literal["registered", "verified", "suspended"] = "registered"


class CandidateOfficialImportRequest(BaseModel):
    source: str = Field(min_length=3, max_length=120)
    reason: str = Field(min_length=5, max_length=255)
    candidates: list[CandidateOfficialImportRow] = Field(min_length=1, max_length=1000)


class CandidateOfficialImportResult(BaseModel):
    imported: int
    created: int
    updated: int
    skipped: int
    candidate_ids: list[str]
    references: list[str]


class CandidateIdentityCreate(BaseModel):
    candidate_id: str
    document_type: Literal["national_id", "passport", "driver_file"] = "national_id"
    document_reference: str = Field(min_length=3)
    photo_reference: str | None = None


class CandidateIdentityDecision(BaseModel):
    status: Literal["verified", "rejected", "needs_review"]
    reason: str = Field(min_length=5)


class CandidateIdentityRead(BaseModel):
    id: str
    candidate_id: str
    document_type: str
    document_reference: str
    photo_reference: str | None = None
    status: str
    verified_by_id: str | None = None
    decision_reason: str | None = None
    created_at: datetime
    decided_at: datetime | None = None

    model_config = {"from_attributes": True}


class CenterCreate(BaseModel):
    code: str
    name: str
    city: str
    address: str
    capacity: int = 20
    status: Literal["pending_audit", "active", "accredited", "suspended"] = "pending_audit"


class CenterRead(CenterCreate):
    id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CenterStatusUpdate(BaseModel):
    status: Literal["pending_audit", "active", "accredited", "suspended"]
    reason: str = Field(min_length=5)


class CenterOfficialImportRow(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=3, max_length=255)
    city: str = Field(min_length=2, max_length=120)
    address: str = Field(min_length=3, max_length=255)
    capacity: int = Field(default=20, ge=1, le=500)
    status: Literal["pending_audit", "active", "accredited", "suspended"] = "pending_audit"


class CenterOfficialImportRequest(BaseModel):
    source: str = Field(min_length=3, max_length=120)
    reason: str = Field(min_length=5, max_length=255)
    centers: list[CenterOfficialImportRow] = Field(min_length=1, max_length=500)


class CenterOfficialImportResult(BaseModel):
    imported: int
    created: int
    updated: int
    skipped: int
    codes: list[str]


class QuestionCreate(BaseModel):
    category: str
    text: str
    options: list[str]
    correct_answer: str
    explanation: str | None = None


class QuestionRead(QuestionCreate):
    id: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class QuestionOfficialImportRow(BaseModel):
    category: str = Field(min_length=2, max_length=80)
    text: str = Field(min_length=10)
    options: list[str] = Field(min_length=2, max_length=6)
    correct_answer: str = Field(min_length=1, max_length=255)
    explanation: str | None = None
    is_active: bool = True


class QuestionOfficialImportRequest(BaseModel):
    source: str = Field(min_length=3, max_length=120)
    reason: str = Field(min_length=5, max_length=255)
    questions: list[QuestionOfficialImportRow] = Field(min_length=1, max_length=1000)


class QuestionOfficialImportResult(BaseModel):
    imported: int
    created: int
    updated: int
    skipped: int
    question_ids: list[str]


class QuestionGovernanceDecisionCreate(BaseModel):
    status: Literal["published", "suspended", "needs_revision"]
    reason: str = Field(min_length=5)


class QuestionGovernanceRead(BaseModel):
    question_id: str
    category: str
    text: str
    is_active: bool
    latest_status: str
    latest_reason: str | None = None
    decided_by_id: str | None = None
    decided_at: datetime | None = None


class InstitutionalAuthorizationCreate(BaseModel):
    authority: str = Field(min_length=3)
    reference: str = Field(min_length=3)
    title: str = Field(min_length=3)
    scope: str = Field(min_length=5)
    valid_from: datetime | None = None
    valid_until: datetime | None = None


class InstitutionalAuthorizationStatusUpdate(BaseModel):
    status: Literal["draft", "pending_signature", "approved", "expired", "revoked"]
    reason: str = Field(min_length=5)


class InstitutionalAuthorizationRead(InstitutionalAuthorizationCreate):
    id: str
    status: str
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ExamSessionCreate(BaseModel):
    center_id: str
    starts_at: datetime
    capacity: int = 20


class ExamSessionRead(BaseModel):
    id: str
    reference: str
    center_id: str
    starts_at: datetime
    capacity: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ExamStartRequest(BaseModel):
    candidate_id: str
    session_id: str


class ExamStartFromBookingRequest(BaseModel):
    booking_reference: str = Field(min_length=3)
    device_key: str | None = Field(default=None, min_length=4, max_length=160)
    device_label: str | None = Field(default=None, max_length=120)


class ExamSubmitRequest(BaseModel):
    answers: dict[str, str]


class ExamAttemptRead(BaseModel):
    id: str
    candidate_id: str
    session_id: str
    status: str
    answers: dict | None = None
    score: int | None = None
    passed: bool | None = None
    started_at: datetime
    submitted_at: datetime | None = None

    model_config = {"from_attributes": True}


class ExamCertificateVerificationRead(BaseModel):
    valid: bool
    attempt_id: str
    status: str
    candidate_reference: str | None = None
    candidate_name: str | None = None
    identity_number: str | None = None
    permit_category: str | None = None
    session_reference: str | None = None
    center_name: str | None = None
    center_city: str | None = None
    score: int | None = None
    passed: bool | None = None
    submitted_at: str | None = None
    reason: str | None = None


class CenterIncidentCreate(BaseModel):
    center_id: str
    session_id: str | None = None
    attempt_id: str | None = None
    incident_type: str = "technical_issue"
    severity: str = "medium"
    description: str = Field(min_length=5)


class CenterIncidentResolveRequest(BaseModel):
    resolution_notes: str = Field(min_length=5)
    allow_retake: bool = False


class CenterIncidentRead(BaseModel):
    id: str
    center_id: str
    session_id: str | None = None
    attempt_id: str | None = None
    incident_type: str
    severity: str
    status: str
    description: str
    resolution_notes: str | None = None
    reported_by_id: str | None = None
    resolved_by_id: str | None = None
    new_attempt_id: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True}


class BookingCreate(BaseModel):
    candidate_id: str
    session_id: str


class BookingRead(BaseModel):
    id: str
    reference: str
    candidate_id: str
    session_id: str
    status: str
    verification_code: str
    created_at: datetime

    model_config = {"from_attributes": True}


class BookingVerificationRead(BaseModel):
    valid: bool
    reference: str | None = None
    status: str | None = None


class DashboardRead(BaseModel):
    candidates: int
    accredited_centers: int
    exam_sessions: int
    questions: int
    fraud_alerts: int = 0


class AuditLogRead(BaseModel):
    id: str
    actor_id: str | None = None
    action: str
    entity: str
    entity_id: str | None = None
    details: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
