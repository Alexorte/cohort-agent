from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Conversation/session identifier")
    message: str = Field(..., min_length=1)


class AgeFilter(BaseModel):
    operator: Literal[">", ">=", "<", "<=", "="]
    value: int


class ParsedIntent(BaseModel):
    intent: Literal[
        "create_cohort",
        "refine_cohort",
        "get_stats",
        "get_chart",
        "run_action",
        "unknown",
    ]
    scope: Literal["new", "active_cohort"] = "new"
    filters: dict[str, Any] = Field(default_factory=dict)
    metric: str | None = None
    chart: str | None = None
    action: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    unknown_terms: list[str] = Field(default_factory=list)

class CohortDefinition(BaseModel):
    include_conditions: list[str] = Field(default_factory=list)
    exclude_conditions: list[str] = Field(default_factory=list)
    include_allergies: list[str] = Field(default_factory=list)
    exclude_allergies: list[str] = Field(default_factory=list)
    include_medications: list[str] = Field(default_factory=list)
    exclude_medications: list[str] = Field(default_factory=list)
    sex: str | None = None
    age: AgeFilter | None = None


class CohortResult(BaseModel):
    cohort_id: str
    patient_ids: list[str]
    size: int
    definition: dict[str, Any]


class ChatResponse(BaseModel):
    session_id: str
    message: str
    cohort_id: str | None = None
    cohort_size: int | None = None
    filters_applied: dict[str, Any] = Field(default_factory=dict)
    tables_used: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    unknown_terms: list[str] = Field(default_factory=list)