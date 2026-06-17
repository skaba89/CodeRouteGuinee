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


class UserRead(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


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
