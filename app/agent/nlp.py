
import re
import unicodedata
from app.utils.allergies import ALLERGY_TERM_MAP

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