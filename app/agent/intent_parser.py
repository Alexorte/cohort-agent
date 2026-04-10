from __future__ import annotations

from app.models.api_models import ParsedIntent
from app.agent.nlp import (
    extract_has_filters,
    normalize_text,
    extract_allergy_filters,
    extract_age_filter,
    extract_age_range,
    resolve_condition_terms,
    resolve_medication_terms,
    detect_unknown_terms,
    extract_table_filters,
)

class IntentParser:
    def parse(self, message: str, has_active_cohort: bool) -> ParsedIntent:
        text = normalize_text(message)
        unknown_terms = detect_unknown_terms(text)
        warnings = []
        filters: dict = {}

        if unknown_terms:
            warnings.append(
                "He detectado términos que no he reconocido con suficiente fiabilidad."
            )

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
            if key == "has_allergies" and (
                "include_allergies" in filters or "exclude_allergies" in filters
            ):
                continue
            filters[key] = value

        condition_terms = resolve_condition_terms(text)
        if condition_terms:
            filters.setdefault("include_conditions", []).extend(condition_terms)

        medication_terms = resolve_medication_terms(text)
        if medication_terms:
            filters.setdefault("include_medications", []).extend(medication_terms)

        table_filters = extract_table_filters(text)
        if table_filters:
            filters["table_filters"] = table_filters

        if any(word in text for word in ["estad", "resumen", "cuant", "cuanto", "cuantos"]):
            return ParsedIntent(
                intent="get_stats",
                scope="active_cohort",
                filters=filters,
                confidence=0.80,
                warnings=warnings,
                unknown_terms=unknown_terms,
            )

        if any(word in text for word in ["grafico", "histograma", "barras"]):
            chart = "age_histogram" if "edad" in text else "top_conditions"
            return ParsedIntent(
                intent="get_chart",
                scope="active_cohort",
                chart=chart,
                filters=filters,
                confidence=0.80,
                warnings=warnings,
                unknown_terms=unknown_terms,
            )

        if "guardar" in text:
            return ParsedIntent(
                intent="run_action",
                scope="active_cohort",
                action="save_cohort",
                payload={"name": "cohorte_guardada"},
                confidence=0.90,
                warnings=warnings,
                unknown_terms=unknown_terms,
            )

        if "export" in text:
            return ParsedIntent(
                intent="run_action",
                scope="active_cohort",
                action="export_cohort",
                payload={"format": "csv"},
                confidence=0.90,
                warnings=warnings,
                unknown_terms=unknown_terms,
            )

        if has_active_cohort and any(
            word in text for word in ["de esos", "de esas", "solo", "excluye", "anade", "añade", "sin", "quita", "elimina", "agrega", "agrega", "refina", "refinar", "incluye"]
        ):
            return ParsedIntent(
                intent="refine_cohort",
                scope="active_cohort",
                filters=filters,
                confidence=0.78,
                warnings=warnings,
                unknown_terms=unknown_terms,
            )

        if filters:
            return ParsedIntent(
                intent="create_cohort",
                scope="new",
                filters=filters,
                confidence=0.84,
                warnings=warnings,
                unknown_terms=unknown_terms,
            )

        return ParsedIntent(
            intent="unknown",
            confidence=0.20,
            warnings=warnings,
            unknown_terms=unknown_terms,
        )