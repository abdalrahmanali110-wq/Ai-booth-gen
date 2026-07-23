"""Compile questionnaire answers into a single image-generation prompt."""

from app.services.questionnaire_config import (
    PROMPT_SUFFIX,
    QUESTIONS,
    get_question,
)

# Maps option ids to natural-language prompt fragments.
FRAGMENT_MAP: dict[str, dict[str, str]] = {
    "q1_event_type": {
        "trade_show": "at a trade show exhibition",
        "corporate_activation": "for a corporate brand activation",
        "retail_popup": "as a retail pop-up booth",
        "product_launch": "for a product launch event",
        "conference": "at a conference or summit",
    },
    "q2_industry": {
        "technology": "technology brand",
        "automotive": "automotive brand",
        "fashion": "fashion and lifestyle brand",
        "fnb": "food and beverage brand",
        "real_estate": "real estate and construction brand",
        "finance": "finance and corporate brand",
    },
    "q3_booth_size": {
        "small": "Small-sized booth (up to 20 sqm)",
        "medium": "Medium-sized booth (20-50 sqm)",
        "large": "Large booth (50-100 sqm)",
        "xlarge": "Extra-large booth (100+ sqm)",
    },
    "q4_layout": {
        "inline": "inline layout with one open side",
        "corner": "corner layout with two open sides",
        "peninsula": "peninsula layout with three open sides",
        "island": "island layout with four open sides",
    },
    "q5_style": {
        "minimalist": "Minimalist, modern design style",
        "futuristic": "Futuristic, tech-forward design style",
        "luxury": "Luxury, premium design style",
        "industrial": "Industrial design with raw materials",
        "warm": "Warm, natural design with wood and greenery",
    },
    "q6_colors": {
        "black_gold": "Primary color palette: black and gold accents",
        "white_accent": "Primary color palette: white with one bold accent color",
        "deep_tones": "Primary color palette: deep tones of crimson, navy, and forest",
        "vibrant": "Primary color palette: bright and vibrant multi-color",
        "neutral": "Primary color palette: neutral beige, grey, and cream",
    },
    "q7_features": {
        "led_wall": "an LED video wall",
        "product_display": "product display shelving and plinths",
        "meeting_lounge": "a meeting room / private lounge",
        "demo_stations": "interactive demo stations",
        "reception": "a reception desk",
        "double_deck": "a double-deck second floor",
    },
    "q8_materials": {
        "matte": "Finishes include matte panels",
        "backlit": "Finishes include backlit illuminated panels",
        "wood": "Finishes include wood veneer",
        "metal": "Finishes include brushed metal",
        "glass": "Finishes include glass and acrylic elements",
        "fabric": "Finishes include fabric and tension stretch surfaces",
    },
}


def _answer_value(answer: dict | None) -> str | list | None:
    if not answer:
        return None
    return answer.get("value")


def _other_text(answer: dict | None) -> str | None:
    if not answer:
        return None
    text = (answer.get("other_text") or "").strip()
    return text or None


def _resolve_single(question_id: str, answer: dict | None) -> str | None:
    if not answer:
        return None

    value = _answer_value(answer)
    other = _other_text(answer)

    if value == "other" or (other and value in (None, "other")):
        return other

    if isinstance(value, str):
        mapped = FRAGMENT_MAP.get(question_id, {}).get(value)
        if mapped:
            return mapped
        # Fallback: use option label from config
        question = get_question(question_id)
        if question:
            for option in question["options"]:
                if option["id"] == value:
                    return option["label"]
        return value

    return None


def _resolve_multi(question_id: str, answer: dict | None) -> list[str]:
    if not answer:
        return []

    values = _answer_value(answer)
    other = _other_text(answer)
    fragments: list[str] = []

    if isinstance(values, list):
        for value in values:
            if value == "other":
                continue
            mapped = FRAGMENT_MAP.get(question_id, {}).get(value)
            if mapped:
                fragments.append(mapped)
            else:
                question = get_question(question_id)
                if question:
                    for option in question["options"]:
                        if option["id"] == value:
                            fragments.append(option["label"].lower())
                            break
    elif isinstance(values, str) and values != "other":
        mapped = FRAGMENT_MAP.get(question_id, {}).get(values)
        fragments.append(mapped or values)

    if other:
        fragments.append(other)

    return fragments


def compile_prompt(answers: dict) -> str:
    """
    Assemble answers into one coherent DALL·E / image prompt.
    Order: event → industry → size → layout → style → colors → features → materials → references → suffix.
    """
    event = _resolve_single("q1_event_type", answers.get("q1_event_type"))
    industry = _resolve_single("q2_industry", answers.get("q2_industry"))
    size = _resolve_single("q3_booth_size", answers.get("q3_booth_size"))
    layout = _resolve_single("q4_layout", answers.get("q4_layout"))
    style = _resolve_single("q5_style", answers.get("q5_style"))
    colors = _resolve_single("q6_colors", answers.get("q6_colors"))
    features = _resolve_multi("q7_features", answers.get("q7_features"))
    materials = _resolve_single("q8_materials", answers.get("q8_materials"))
    references = _resolve_single("q9_references", answers.get("q9_references"))

    industry_phrase = industry or "brand"
    event_phrase = event or "at an exhibition"

    opening = (
        f"A photorealistic 3D architectural render of a modern exhibition booth "
        f"for a {industry_phrase} {event_phrase}."
    )

    parts = [opening]

    size_layout = []
    if size:
        size_layout.append(size)
    if layout:
        size_layout.append(layout)
    if size_layout:
        parts.append(", ".join(size_layout) + ".")

    if style:
        parts.append(f"{style}.")

    if colors:
        parts.append(f"{colors}.")

    if features:
        if len(features) == 1:
            parts.append(f"Features {features[0]}.")
        else:
            listed = ", ".join(features[:-1]) + f", and {features[-1]}"
            parts.append(f"Features {listed}.")

    if materials:
        parts.append(f"{materials}.")

    if references and references.lower() not in {
        "no preference / surprise me",
        "no preference",
        "surprise me",
    }:
        # Only add when user provided a real reference via Other
        if answers.get("q9_references", {}).get("value") == "other":
            parts.append(f"Design inspired by the look of {references}.")

    parts.append(PROMPT_SUFFIX)
    return " ".join(parts)


def validate_answers(answers: dict) -> list[str]:
    """Return list of missing/invalid question ids."""
    errors: list[str] = []

    for question in QUESTIONS:
        qid = question["id"]
        answer = answers.get(qid)
        required = question.get("required", True)

        if not answer or answer.get("value") in (None, "", []):
            if required:
                errors.append(qid)
            continue

        value = answer.get("value")
        other = (answer.get("other_text") or "").strip()

        if question["type"] == "multi":
            selected = value if isinstance(value, list) else [value]
            selected = [v for v in selected if v]
            min_sel = question.get("min_selections", 1)
            max_sel = question.get("max_selections", 4)

            if "other" in selected and not other:
                errors.append(qid)
                continue

            count = len([v for v in selected if v != "other"]) + (
                1 if other else 0
            )
            if count < min_sel or count > max_sel:
                errors.append(qid)
        else:
            if value == "other" and not other:
                errors.append(qid)

    return errors
