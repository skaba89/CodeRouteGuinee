from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class MediaMigrationPlanEntry(BaseModel):
    question_id: str = Field(min_length=1, max_length=36)
    media_id: str = Field(min_length=1, max_length=36)

    @field_validator("question_id", "media_id", mode="before")
    @classmethod
    def strip_identifier(cls, value):
        return value.strip() if isinstance(value, str) else value


class MediaMigrationPlanRequest(BaseModel):
    dry_run: bool = True
    replace_existing: bool = False
    reason: str = Field(min_length=8, max_length=500)
    mappings: list[MediaMigrationPlanEntry] = Field(min_length=1, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def strip_reason(cls, value):
        return value.strip() if isinstance(value, str) else value
