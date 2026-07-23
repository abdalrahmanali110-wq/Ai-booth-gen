"""Fixed guided-questionnaire question set (client spec)."""

from typing import Any

OTHER_OPTION = {
    "id": "other",
    "label": "Other",
    "allows_text": True,
}

QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "q1_event_type",
        "number": 1,
        "prompt": "What type of event is this booth for?",
        "purpose": "Establishes context and industry framing for the render.",
        "type": "single",
        "required": True,
        "options": [
            {"id": "trade_show", "label": "Trade show / exhibition"},
            {"id": "corporate_activation", "label": "Corporate activation"},
            {"id": "retail_popup", "label": "Retail pop-up"},
            {"id": "product_launch", "label": "Product launch"},
            {"id": "conference", "label": "Conference / summit"},
            {**OTHER_OPTION},
        ],
    },
    {
        "id": "q2_industry",
        "number": 2,
        "prompt": "What industry or sector is your brand in?",
        "purpose": "Steers visual tone and material choices.",
        "type": "single",
        "required": True,
        "options": [
            {"id": "technology", "label": "Technology"},
            {"id": "automotive", "label": "Automotive"},
            {"id": "fashion", "label": "Fashion / Lifestyle"},
            {"id": "fnb", "label": "F&B"},
            {"id": "real_estate", "label": "Real Estate / Construction"},
            {"id": "finance", "label": "Finance / Corporate"},
            {**OTHER_OPTION},
        ],
    },
    {
        "id": "q3_booth_size",
        "number": 3,
        "prompt": "What is your approximate booth size?",
        "purpose": "Affects layout complexity and structural elements.",
        "type": "single",
        "required": True,
        "options": [
            {"id": "small", "label": "Small (up to 20 sqm)"},
            {"id": "medium", "label": "Medium (20-50 sqm)"},
            {"id": "large", "label": "Large (50-100 sqm)"},
            {"id": "xlarge", "label": "Extra Large (100+ sqm)"},
            {**OTHER_OPTION},
        ],
    },
    {
        "id": "q4_layout",
        "number": 4,
        "prompt": "What is the booth's floor position / layout type?",
        "purpose": "Determines open sides and structural framing.",
        "type": "single",
        "required": True,
        "options": [
            {"id": "inline", "label": "Inline (one open side)"},
            {"id": "corner", "label": "Corner (two open sides)"},
            {"id": "peninsula", "label": "Peninsula (three open sides)"},
            {"id": "island", "label": "Island (fully open, four sides)"},
            {**OTHER_OPTION},
        ],
    },
    {
        "id": "q5_style",
        "number": 5,
        "prompt": "What overall design style are you going for?",
        "purpose": "Primary driver of aesthetic language in the prompt.",
        "type": "single",
        "required": True,
        "options": [
            {"id": "minimalist", "label": "Minimalist / modern"},
            {"id": "futuristic", "label": "Futuristic / tech-forward"},
            {"id": "luxury", "label": "Luxury / premium"},
            {"id": "industrial", "label": "Industrial / raw materials"},
            {"id": "warm", "label": "Warm / natural (wood, greenery)"},
            {**OTHER_OPTION},
        ],
    },
    {
        "id": "q6_colors",
        "number": 6,
        "prompt": "What is your brand's primary color palette?",
        "purpose": "Locks in color direction for brand identity.",
        "type": "single",
        "required": True,
        "options": [
            {"id": "black_gold", "label": "Black & gold"},
            {"id": "white_accent", "label": "White & one bold accent color"},
            {"id": "deep_tones", "label": "Deep tones (crimson, navy, forest)"},
            {"id": "vibrant", "label": "Bright / vibrant multi-color"},
            {"id": "neutral", "label": "Neutral (beige, grey, cream)"},
            {**OTHER_OPTION},
        ],
    },
    {
        "id": "q7_features",
        "number": 7,
        "prompt": "Which features must the booth include?",
        "purpose": "Multi-select. Adds functional elements the render must depict.",
        "type": "multi",
        "required": True,
        "min_selections": 1,
        "max_selections": 4,
        "options": [
            {"id": "led_wall", "label": "LED video wall"},
            {"id": "product_display", "label": "Product display shelving / plinths"},
            {"id": "meeting_lounge", "label": "Meeting room / private lounge"},
            {"id": "demo_stations", "label": "Interactive / demo stations"},
            {"id": "reception", "label": "Reception desk"},
            {"id": "double_deck", "label": "Double-deck (second floor)"},
            {**OTHER_OPTION},
        ],
    },
    {
        "id": "q8_materials",
        "number": 8,
        "prompt": "What materials or finishes do you prefer?",
        "purpose": "Adds surface and texture detail for realism.",
        "type": "single",
        "required": True,
        "options": [
            {"id": "matte", "label": "Matte panels"},
            {"id": "backlit", "label": "Backlit / illuminated panels"},
            {"id": "wood", "label": "Wood veneer"},
            {"id": "metal", "label": "Brushed metal"},
            {"id": "glass", "label": "Glass / acrylic elements"},
            {"id": "fabric", "label": "Fabric / tension stretch"},
            {**OTHER_OPTION},
        ],
    },
    {
        "id": "q9_references",
        "number": 9,
        "prompt": "Any reference brands or booths you like the look of?",
        "purpose": "Optional steer question.",
        "type": "single",
        "required": False,
        "options": [
            {"id": "no_preference", "label": "No preference / surprise me"},
            {**OTHER_OPTION},
        ],
    },
]

QUESTION_IDS = [q["id"] for q in QUESTIONS]

PROMPT_SUFFIX = (
    "Professional exhibition photography, wide-angle view, "
    "clean studio lighting, high detail, 8k."
)

MAX_REGENERATIONS = 3
OTHER_TEXT_MAX_LENGTH = 60


def get_questions_public() -> list[dict[str, Any]]:
    """Return questions without internal purpose notes if needed later."""
    return QUESTIONS


def get_question(question_id: str) -> dict[str, Any] | None:
    for question in QUESTIONS:
        if question["id"] == question_id:
            return question
    return None
