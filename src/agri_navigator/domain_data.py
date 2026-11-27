"""Domain taxonomy, crop recognition helpers, and non-prescriptive safety rules."""

from __future__ import annotations

import re

EDUCATIONAL_DISCLAIMER = (
    "Educational information only: this guidance summarizes permitted crop-care reference "
    "documents and is non-prescriptive. Consult a local agricultural extension officer or "
    "accredited soil/plant laboratory before applying chemicals or site-specific treatments."
)

SUPPORTED_CROPS: tuple[str, ...] = ("wheat", "rice", "tomato", "maize", "potato")

CROP_ALIASES: dict[str, str] = {
    "wheat": "wheat",
    "triticum": "wheat",
    "rice": "rice",
    "paddy": "rice",
    "tomato": "tomato",
    "tomatoes": "tomato",
    "maize": "maize",
    "corn": "maize",
    "potato": "potato",
    "potatoes": "potato",
}

UNSUPPORTED_CROP_EXAMPLES: tuple[str, ...] = (
    "apple",
    "banana",
    "barley",
    "cabbage",
    "chili",
    "chilli",
    "citrus",
    "coffee",
    "cotton",
    "cucumber",
    "dragon fruit",
    "grape",
    "grapes",
    "groundnut",
    "mango",
    "millet",
    "onion",
    "orange",
    "peanut",
    "pepper",
    "soybean",
    "sugarcane",
    "sunflower",
    "tea",
)

GENERAL_SOIL_IPM_KEYWORDS: tuple[str, ...] = (
    "soil ph",
    "mulch",
    "mulching",
    "drip irrigation",
    "furrow irrigation",
    "integrated pest management",
    "ipm",
    "soil sampling",
    "soil moisture conservation",
)

AGRI_TOPIC_KEYWORDS: tuple[str, ...] = (
    "crop",
    "leaf",
    "leaves",
    "yellow",
    "yellowing",
    "chlorosis",
    "blight",
    "rust",
    "rot",
    "spot",
    "spots",
    "lesion",
    "lesions",
    "irrigate",
    "irrigation",
    "water",
    "watering",
    "flood",
    "moisture",
    "soil",
    "nutrient",
    "nitrogen",
    "phosphorus",
    "potassium",
    "calcium",
    "pest",
    "borer",
    "armyworm",
    "seed",
    "seedling",
    "tuber",
    "hilling",
    "earthing",
    "tiller",
    "tillering",
    "flowering",
    "pollination",
    "harvest",
    "storage",
    "grain",
    "pruning",
    "sucker",
    "wilt",
    "mulch",
    "fungal",
    "disease",
    "plant",
    "foliage",
    "silking",
    "tasseling",
    "panicle",
    "sprout",
    "canopy",
    "transplant",
)

PRESCRIPTIVE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(how much|how many|exact|recommend|prescribe|give me)\b.*"
        r"\b(dose|dosage|ml|gram|grams|kg|litre|liter|spray|fungicide|"
        r"pesticide|herbicide|insecticide|chemical|urea|dap)\b",
        re.I,
    ),
    re.compile(
        r"\b(which|what)\b.*\b(pesticide|fungicide|herbicide|insecticide|chemical brand)\b.*"
        r"\b(spray|buy|apply|use)\b",
        re.I,
    ),
    re.compile(r"\b(dosage|mixing ratio|spray schedule|ppm|ml per litre|ml/l)\b", re.I),
)

GREETING_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^(hi|hello|hey|good morning|good afternoon|good evening|namaste)[!. ]*$", re.I),
    re.compile(r"^(help|what can you do|how do you work|capabilities)[?.! ]*$", re.I),
)


def extract_supported_crop(text: str) -> str | None:
    """Return canonical supported crop name if explicitly mentioned in text."""
    lowered = text.lower()
    for alias, canonical in CROP_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", lowered):
            return canonical
    return None


def extract_unsupported_crop(text: str) -> str | None:
    """Return unsupported crop name if user explicitly asks about an unindexed crop."""
    lowered = text.lower()
    for crop in UNSUPPORTED_CROP_EXAMPLES:
        if re.search(rf"\b{re.escape(crop)}\b", lowered):
            return crop
    return None


def is_general_soil_ipm_query(text: str) -> bool:
    """Return True when the query clearly targets general soil/irrigation/IPM concepts."""
    lowered = text.lower()
    return any(keyword in lowered for keyword in GENERAL_SOIL_IPM_KEYWORDS)


def is_prescriptive_request(text: str) -> bool:
    """Detect requests asking for chemical dosages, brand recommendations, or prescriptions."""
    return any(pattern.search(text) for pattern in PRESCRIPTIVE_PATTERNS)


def is_greeting_or_help(text: str) -> bool:
    """Detect simple greeting or help-seeking utterances."""
    return any(pattern.match(text.strip()) for pattern in GREETING_PATTERNS)


def is_agricultural_query(text: str) -> bool:
    """Return True if the text appears related to crops, soil, or plant care."""
    if extract_supported_crop(text) or extract_unsupported_crop(text):
        return True
    if is_general_soil_ipm_query(text):
        return True
    lowered = text.lower()
    return any(re.search(rf"\b{re.escape(kw)}\b", lowered) for kw in AGRI_TOPIC_KEYWORDS)
