import re
import unicodedata
from app.utils.allergies import ALLERGY_TERM_MAP
from app.utils.conditions import CONDITION_TERM_MAP
from app.utils.medications import MEDICATION_TERM_MAP
from difflib import get_close_matches

from app.utils.tables_filters import TABLE_FILTER_SCHEMA

def normalize_text(text: str) -> str:
    text = text.lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )

def extract_has_filters(text: str) -> dict:
    filters: dict = {}

    # Alergias genéricas
    if (
        "alergicos" in text
        or "alergico" in text
        or "con alergias" in text
        or "con alergia" in text
        or "alguna alergia" in text
        or "con alguna alergia" in text
        or "alergias" in text
    ):
        filters["has_allergies"] = True

    # Condiciones genéricas
    if (
        "con alguna condicion" in text
        or "con condiciones" in text
        or "con condicion" in text
        or "diagnosticados" in text
        or "con diagnosticos" in text
        or "con diagnostico" in text
        or "diagnosticos" in text
        or "alguna diagnostico" in text
        or "alguna condicion" in text
    ):
        filters["has_conditions"] = True

    # Medicación genérica
    if (
        "con medicacion" in text
        or "con medicaciones" in text
        or "medicados" in text
        or "con tratamientos" in text
        or "con tratamiento" in text
        or "tratados" in text
        or "con algun tratamiento" in text
        or "con alguna medicacion" in text
        or "medicandose" in text
    ):
        filters["has_medications"] = True

    return filters

def resolve_allergy_term(text: str) -> str | None:
    for key, canonical in ALLERGY_TERM_MAP.items():
        if key in text:
            return canonical
    return None


def extract_allergy_filters(text: str) -> dict:
    filters: dict = {}

    allergy_term = resolve_allergy_term(text)
    if not allergy_term:
        return filters

    is_negative = (
        "sin alergia a" in text
        or "sin alergicos a" in text
        or "excluir alergicos a" in text
        or "excluye alergicos a" in text
        or "excluir alérgicos a" in text
        or "excluye alérgicos a" in text
    )

    is_positive = (
        "alergicos a" in text
        or "con alergia a" in text
        or "alergia a" in text
        or "con alergias a" in text
    )

    if is_negative:
        filters.setdefault("exclude_allergies", []).append(allergy_term)
    elif is_positive:
        filters.setdefault("include_allergies", []).append(allergy_term)

    return filters

def extract_age_filter(text: str):
    patterns = [
        (r"mayor(?:es)? o igual(?:es)? a\s*(\d+)", ">="),
        (r"menor(?:es)? o igual(?:es)? a\s*(\d+)", "<="),
        (r"mayor(?:es)? o igual(?:es)? que\s*(\d+)", ">="),
        (r"menor(?:es)? o igual(?:es)? que\s*(\d+)", "<="),
        (r"(\d+)\s*o mas", ">="),
        (r"(\d+)\s*o menos", "<="),
        (r"mayor(?:es)? de\s*(\d+)", ">"),
        (r"menor(?:es)? de\s*(\d+)", "<"),
        (r"mayor(?:es)? que\s*(\d+)", ">"),
        (r"menor(?:es)? que\s*(\d+)", "<"),
        (r">=\s*(\d+)", ">="),
        (r"<=\s*(\d+)", "<="),
        (r">\s*(\d+)", ">"),
        (r"<\s*(\d+)", "<"),
    ]

    for pattern, operator in patterns:
        match = re.search(pattern, text)
        if match:
            return {"operator": operator, "value": int(match.group(1))}
    return None
    
def extract_age_range(text: str):
    patterns = [
        r"entre\s*(\d+)\s*y\s*(\d+)",
        r"de\s*(\d+)\s*a\s*(\d+)",
        r"desde\s*(\d+)\s*hasta\s*(\d+)",
        r"(\d+)\s*-\s*(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            a = int(match.group(1))
            b = int(match.group(2))
            low, high = sorted([a, b])
            return {
                "min": low,
                "max": high,
                "include_min": True,
                "include_max": True,
            }
    return None

def resolve_condition_terms(text: str) -> list[str]:
    matches = []
    for alias in sorted(CONDITION_TERM_MAP.keys(), key=len, reverse=True):
        if alias in text:
            canonical = CONDITION_TERM_MAP[alias]
            if canonical not in matches:
                matches.append(canonical)
    return matches


def resolve_medication_terms(text: str) -> list[str]:
    matches = []
    for alias in sorted(MEDICATION_TERM_MAP.keys(), key=len, reverse=True):
        if alias in text:
            canonical = MEDICATION_TERM_MAP[alias]
            if canonical not in matches:
                matches.append(canonical)
    return matches


CRITICAL_VOCAB = [
    "mayor", "mayores", "menor", "menores",
    "igual", "iguales", "entre", "desde", "hasta",
    "alergia", "alergias", "alergico", "alergicos",
    "condicion", "condiciones",
    "medicacion", "medicaciones", "medicado", "medicados",
    "medicandose", "medicarse", "tratamiento", "tratamientos",
    "tomando", "toma", "lleve", "lleven",
    "excluye", "excluir", "sin", "con",
]

def detect_unknown_terms(text: str, cutoff: float = 0.85) -> list[str]:
    unknown = []
    for token in text.split():
        if token.isdigit():
            continue
        if token in CRITICAL_VOCAB:
            continue
        close = get_close_matches(token, CRITICAL_VOCAB, n=1, cutoff=cutoff)
        if close:
            unknown.append(token)
    return unknown

def extract_date_literal(text: str) -> str | None:
    match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if match:
        return match.group(1)
    return None

def extract_table_filters(text: str) -> list[dict]:
    filters = []

    date_value = extract_date_literal(text)

    # MEDICATIONS - Fecha_inicio
    if date_value and any(alias in text for alias in TABLE_FILTER_SCHEMA["medications"]["columns"]["Fecha_inicio"]["aliases"]):
        filters.append({
            "table": "medications",
            "column": "Fecha_inicio",
            "operator": ">=",
            "value": date_value,
            "value_type": "date",
        })

    # MEDICATIONS - Fecha_fin
    if date_value and any(alias in text for alias in TABLE_FILTER_SCHEMA["medications"]["columns"]["Fecha_fin"]["aliases"]):
        filters.append({
            "table": "medications",
            "column": "Fecha_fin",
            "operator": "<=",
            "value": date_value,
            "value_type": "date",
        })

    # ENCOUNTERS - Fecha_inicio
    if date_value and any(alias in text for alias in TABLE_FILTER_SCHEMA["encounters"]["columns"]["Fecha_inicio"]["aliases"]):
        filters.append({
            "table": "encounters",
            "column": "Fecha_inicio",
            "operator": ">=",
            "value": date_value,
            "value_type": "date",
        })

    # ENCOUNTERS - Fecha_fin
    if date_value and any(alias in text for alias in TABLE_FILTER_SCHEMA["encounters"]["columns"]["Fecha_fin"]["aliases"]):
        filters.append({
            "table": "encounters",
            "column": "Fecha_fin",
            "operator": "<=",
            "value": date_value,
            "value_type": "date",
        })

    # ALLERGIES - Fecha_diagnostico
    if date_value and any(alias in text for alias in TABLE_FILTER_SCHEMA["allergies"]["columns"]["Fecha_diagnostico"]["aliases"]):
        filters.append({
            "table": "allergies",
            "column": "Fecha_diagnostico",
            "operator": ">=",
            "value": date_value,
            "value_type": "date",
        })

    # ENCOUNTERS - Tipo_encuentro
    if "urgencias" in text:
        filters.append({
            "table": "encounters",
            "column": "Tipo_encuentro",
            "operator": "=",
            "value": "Urgencias",
            "value_type": "text",
        })

    # MEDICATIONS - Via_administracion
    if "via oral" in text:
        filters.append({
            "table": "medications",
            "column": "Via_administracion",
            "operator": "=",
            "value": "Vía oral",
            "value_type": "text",
        })

    return filters