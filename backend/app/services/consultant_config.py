import json
from functools import lru_cache
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "booth_designer_config.json"


@lru_cache(maxsize=1)
def load_booth_designer_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def build_consultant_system_prompt() -> str:
    config = load_booth_designer_config()
    base = config.get("system_prompt") or (
        "You are an AI Exhibition Booth Consultant. Collect booth requirements "
        "through natural conversation and help the user refine their concept."
    )

    starters = config.get("starter_prompts") or []
    question_order = config.get("question_order") or []
    required = config.get("required_fields") or {}
    conditional = config.get("conditional_fields") or {}
    gate = config.get("generation_gate") or {}
    hard = config.get("hard_constraints") or []

    starter_lines = "\n".join(f'- "{item}"' for item in starters)
    question_lines = []
    for item in question_order:
        if not isinstance(item, dict):
            continue
        optional = " (optional)" if item.get("optional") else ""
        question_lines.append(f"- {item.get('field')}: {item.get('ask')}{optional}")

    required_lines = []
    for key, meta in required.items():
        ask = meta.get("ask", key) if isinstance(meta, dict) else str(meta)
        required_lines.append(f"- {key}: {ask}")

    conditional_lines = []
    for key, meta in conditional.items():
        if not isinstance(meta, dict):
            continue
        trigger = meta.get("trigger", "")
        ask = meta.get("ask", key)
        conditional_lines.append(f"- {key} (when {trigger}): {ask}")

    parts = [
        base,
        "",
        "STARTER PROMPTS USERS MAY CLICK:",
        starter_lines or "- Design a 6x6 fashion booth",
        "",
        "ASK THESE QUESTIONS ONE BY ONE (skip if already answered from the starter):",
        "\n".join(question_lines) or "\n".join(required_lines),
        "",
        "CONDITIONAL / OPTIONAL:",
        "\n".join(conditional_lines) or "- Slogan, event date, and logo are optional.",
        "",
        "HARD CONSTRAINTS:",
        "\n".join(f"- {item}" for item in hard) or "- Do not invent venue rules.",
        "",
        "GENERATION GATE:",
        f"- Ready when: {gate.get('ready_condition', 'all required fields are filled')}",
        f"- When ready: {gate.get('on_ready', 'Summarize and ask for confirmation before generating.')}",
        f"- When not ready: {gate.get('on_not_ready', 'Ask the next unresolved field only.')}",
        "",
        "IMPORTANT OUTPUT RULES FOR THIS APP:",
        "- You cannot generate images yourself.",
        "- When the brief is complete, show a short plain-language summary and ask the user to confirm with yes / looks good / proceed.",
        "- After confirmation language from the user, the backend will generate the image.",
        "- Speak in simple everyday language; explain technical terms briefly when used.",
        "- Ask at most 1 question per reply unless merging event name + location.",
        "- Budget answers should be treated in AED (Dirham).",
    ]
    return "\n".join(parts)


CONFIRMATION_PHRASES = (
    "yes",
    "yep",
    "yeah",
    "looks good",
    "proceed",
    "go ahead",
    "generate",
    "create it",
    "start generating",
    "confirm",
    "approved",
    "ok generate",
    "okay generate",
)


def user_confirmed_generation(message: str) -> bool:
    text = (message or "").strip().lower()
    if not text:
        return False
    return any(phrase in text for phrase in CONFIRMATION_PHRASES)
