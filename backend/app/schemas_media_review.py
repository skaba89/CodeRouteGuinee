from __future__ import annotations

from pydantic import BaseModel, Field


class MediaReviewRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class MediaRegulatoryApprovalRequest(BaseModel):
    authority_reference: str = Field(min_length=3, max_length=500)
    reason: str = Field(min_length=3, max_length=1000)


class MediaQualityGateRead(BaseModel):
    media_id: str
    passed: bool
    score: int
    checks: list[dict]
    blockers: list[str]
    human_review_required: bool
    institutional_validation_inferred: bool
