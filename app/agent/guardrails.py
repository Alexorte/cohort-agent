from __future__ import annotations


class Guardrails:
    ALLOWED_FILTERS = {
        "age_range",
        "age",
        "sex",
        "include_conditions",
        "exclude_conditions",
        "include_allergies",
        "exclude_allergies",
        "include_medications",
        "exclude_medications",
        "has_allergies",
        "has_conditions",
        "has_medications",
        "table_filters",
    }

    def validate_filters(self, filters: dict) -> dict:
        unknown = [k for k in filters if k not in self.ALLOWED_FILTERS]
        if unknown:
            raise ValueError(f"Unsupported filters: {unknown}")
        return filters