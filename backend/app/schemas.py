from datetime import datetime

from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str = Field(min_length=8)
    role: str = "candidate"


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


class CenterCreate(BaseModel):
    code: str
    name: str
    city: str
    address: str
    capacity: int = 20
    status: str = "pending_audit"


class CenterRead(CenterCreate):
    id: str
    created_at: datetime

    model_config = {"from_attributes": True}


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


class DashboardRead(BaseModel):
    candidates: int
    accredited_centers: int
    exam_sessions: int
    questions: int
    fraud_alerts: int = 0
