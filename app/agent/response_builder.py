from __future__ import annotations

from app.models.api_models import ChatResponse


class ResponseBuilder:
    def build_text(
        self,
        session_id: str,
        message: str,
        cohort_id: str | None = None,
        cohort_size: int | None = None,
        filters_applied: dict | None = None,
        tables_used: list[str] | None = None,
        data: dict | None = None,
        warnings: list[str] | None = None,
        unknown_terms: list[str] | None = None,
        
    ) -> ChatResponse:
        return ChatResponse(
            session_id=session_id,
            message=message,
            cohort_id=cohort_id,
            cohort_size=cohort_size,
            filters_applied=filters_applied or {},
            tables_used=tables_used or [],
            data=data or {},
            warnings=warnings or [],
            unknown_terms=unknown_terms or [],
        )