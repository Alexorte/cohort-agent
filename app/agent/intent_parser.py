from __future__ import annotations
from app.models.api_models import ParsedIntent
from app.agent.nlp import (
    extract_has_filters,
    normalize_text,
    extract_allergy_filters,
    extract_age_filter,
    extract_age_range,
)

class IntentParser:
    def parse(self, message: str, has_active_cohort: bool) -> ParsedIntent:
        text = normalize_text(message)
        filters: dict = {}

        age_range = extract_age_range(text)
        if age_range:
            filters["age_range"] = age_range
        else:
            age_match = extract_age_filter(text)
            if age_match:
                filters["age"] = age_match

        allergy_filters = extract_allergy_filters(text)
        for key, value in allergy_filters.items():
            filters.setdefault(key, []).extend(value)

        has_filters = extract_has_filters(text)
        for key, value in has_filters.items():
            filters[key] = value

        if "diabetes" in text:
            filters.setdefault("include_conditions", []).append("diabetes")

        if "hipertension" in text:
            filters.setdefault("include_conditions", []).append("hipertensión")

        if "asma" in text:
            filters.setdefault("include_conditions", []).append("asma")

        if "metform" in text:
            filters.setdefault("include_medications", []).append("metform")

        if any(word in text for word in ["estad", "resumen", "cuant", "cuanto", "cuantos"]):
            return ParsedIntent(
                intent="get_stats",
                scope="active_cohort",
                filters=filters,
                confidence=0.80,
            )

        if any(word in text for word in ["grafico", "histograma", "barras"]):
            chart = "age_histogram" if "edad" in text else "top_conditions"
            return ParsedIntent(
                intent="get_chart",
                scope="active_cohort",
                chart=chart,
                filters=filters,
                confidence=0.80,
            )

        if "guardar" in text:
            return ParsedIntent(
                intent="run_action",
                scope="active_cohort",
                action="save_cohort",
                payload={"name": "cohorte_guardada"},
                confidence=0.9,
            )

        if "export" in text:
            return ParsedIntent(
                intent="run_action",
                scope="active_cohort",
                action="export_cohort",
                payload={"format": "csv"},
                confidence=0.9,
            )

        if has_active_cohort and any(word in text for word in ["de esos", "de esas", "solo", "excluye", "anade"]):
            return ParsedIntent(
                intent="refine_cohort",
                scope="active_cohort",
                filters=filters,
                confidence=0.78,
            )

        if filters:
            return ParsedIntent(
                intent="create_cohort",
                scope="new",
                filters=filters,
                confidence=0.84,
            )

        return ParsedIntent(intent="unknown", confidence=0.2)
