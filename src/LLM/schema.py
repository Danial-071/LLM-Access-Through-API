from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class CommitType(str, Enum):
    feat = "feat"
    fix = "fix"
    chore = "chore"
    other = "other"

class ChangelogInput(BaseModel):
    commit: str = Field(..., min_length=3, max_length=500)

class ChangelogOutput(BaseModel):
    type: CommitType
    scope: Optional[str] = Field(None, max_length=30)
    summary: str = Field(..., max_length=120)
    confidence: float = Field(..., ge=0.0, le=1.0)