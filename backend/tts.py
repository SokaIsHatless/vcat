import asyncio
import json
import os
import random
import re

import edge_tts

RUNTIME_AUDIO_DIR = os.path.join(os.path.dirname(__file__), "runtime", "audio")
LATEST_AUDIO_PATH = os.path.join(RUNTIME_AUDIO_DIR, "latest.mp3")
VOICE_FILE = os.path.join(os.path.dirname(__file__), "voice.json")

DEFAULT_VOICE = "en-US-AriaNeural"
DEFAULT_MOOD = "idle"

# Frontend sends abstract categories only; Edge TTS mapping stays server-side.
VOICE_CATALOG = [
    {"voice": "male", "label": "🐈 Male", "edge_voice": "en-US-GuyNeural"},
    {"voice": "female", "label": "🐈 Female", "edge_voice": "en-US-AriaNeural"},
    {"voice": "neutral", "label": "🐈 Gender Neutral", "edge_voice": "en-US-AvaNeural"},
]

VOICE_CATEGORY_MAP = {entry["voice"]: entry["edge_voice"] for entry in VOICE_CATALOG}

# Prosody targets for edge-tts (wrapped into SSML server-side by the library).
# spoken_style selects optional spoken-only text shaping for pauses / delivery.
MOOD_SPEECH = {
    "happy": {
        "rate": "+8%",
        "pitch": "+3Hz",
        "volume": "+2%",
        "spoken_style": "none",
    },
    "sleepy": {
        "rate": "-10%",
        "pitch": "-3Hz",
        "volume": "-2%",
        "spoken_style": "none",
    },
    "angry": {
        "rate": "+6%",
        "pitch": "-2Hz",
        "volume": "+8%",
        "spoken_style": "none",
    },
    "confused": {
        "rate": "+0%",
        "pitch": "+1Hz",
        "volume": "+0%",
        "spoken_style": "inquisitive",
    },
    "thinking": {
        "rate": "+0%",
        "pitch": "+0Hz",
        "volume": "+0%",
        "spoken_style": "pauses",
    },
    "checking_calendar": {
        "rate": "-3%",
        "pitch": "+0Hz",
        "volume": "+0%",
        "spoken_style": "calm",
    },
    "drafting_email": {
        "rate": "-2%",
        "pitch": "+0Hz",
        "volume": "+2%",
        "spoken_style": "professional",
    },
    "listening": {
        "rate": "+0%",
        "pitch": "+0Hz",
        "volume": "+0%",
        "spoken_style": "conversational",
    },
    "idle": {
        "rate": "+0%",
        "pitch": "+0Hz",
        "volume": "+0%",
        "spoken_style": "conversational",
    },
}

CAT_SOUNDS = ("Mrrp.", "Meow.", "Mrow.", "Prrt.", "*soft purr*")
CAT_SOUND_SPOKEN = {
    "Mrrp.": "Mrrp.",
    "Meow.": "Meow.",
    "Mrow.": "Mrow.",
    "Prrt.": "Prrt.",
    "*soft purr*": "Mmm, purr.",
}
CAT_SOUND_PROBABILITY = 0.175

SERIOUS_MARKERS = (
    "sorry",
    "apolog",
    "unfortunately",
    "my bad",
    "i'm afraid",
    "something broke",
    "even cats have limits",
    "sincerely",
    "serious",
    "urgent",
    "important:",
    "i owe you an apology",
)


def get_voice_options() -> list[dict]:
    return [{"voice": entry["voice"], "label": entry["label"]} for entry in VOICE_CATALOG]


def get_valid_voice_categories() -> list[str]:
    return list(VOICE_CATEGORY_MAP.keys())


def set_voice_category(category: str) -> None:
    if category not in VOICE_CATEGORY_MAP:
        raise ValueError(f"Unknown voice category: {category}")
    with open(VOICE_FILE, "w") as f:
        json.dump({"voice": category}, f)


def get_voice_category() -> str | None:
    try:
        with open(VOICE_FILE) as f:
            data = json.load(f)
        category = data.get("voice")
        return category if category in VOICE_CATEGORY_MAP else None
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None


def has_voice_category() -> bool:
    return get_voice_category() is not None


def clear_voice_category() -> None:
    if os.path.exists(VOICE_FILE):
        os.remove(VOICE_FILE)


def resolve_edge_voice() -> str:
    category = get_voice_category()
    if category:
        return VOICE_CATEGORY_MAP[category]
    return os.environ.get("TTS_VOICE", DEFAULT_VOICE)


def resolve_mood_speech(mood: str | None) -> dict:
    key = (mood or DEFAULT_MOOD).strip().lower()
    if key not in MOOD_SPEECH:
        key = DEFAULT_MOOD
    return dict(MOOD_SPEECH[key])


def sanitize_for_tts(text: str) -> str:
    if not text:
        return ""

    cleaned = text
    cleaned = re.sub(r"```[\s\S]*?```", " ", cleaned)
    cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"\[/?tool[^\]]*\]", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[*_~#>|]+", "", cleaned)
    cleaned = re.sub(
        "["
        "\U0001F300-\U0001FAFF"
        "\U00002600-\U000027BF"
        "\U0001F600-\U0001F64F"
        "\U0001F680-\U0001F6FF"
        "]+",
        "",
        cleaned,
        flags=re.UNICODE,
    )
    cleaned = re.sub(r"[\U0001F000-\U0001FFFF]", "", cleaned)
    cleaned = re.sub(r"([!?.]){2,}", r"\1", cleaned)
    cleaned = re.sub(r"[,;]{2,}", ",", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _starts_with_cat_sound(text: str) -> bool:
    lower = text.lower().lstrip()
    for sound in CAT_SOUNDS:
        spoken = CAT_SOUND_SPOKEN[sound].lower()
        if lower.startswith(sound.lower()) or lower.startswith(spoken):
            return True
    return False


def _is_error_reply(text: str) -> bool:
    lower = text.lower()
    return "something broke" in lower and "even cats have limits" in lower


def _is_serious_or_apologetic(text: str) -> bool:
    lower = text.lower()
    return any(marker in lower for marker in SERIOUS_MARKERS)


def _word_count(text: str) -> int:
    return len([word for word in text.split() if word])


def _maybe_prepend_cat_sound(text: str) -> str:
    if random.random() >= CAT_SOUND_PROBABILITY:
        return text
    if _starts_with_cat_sound(text):
        return text
    if _is_error_reply(text):
        return text
    if _word_count(text) <= 2:
        return text
    if _is_serious_or_apologetic(text):
        return text

    sound = random.choice(CAT_SOUNDS)
    spoken_sound = CAT_SOUND_SPOKEN[sound]
    return f"{spoken_sound} {text}"


def _apply_spoken_style(text: str, spoken_style: str) -> str:
    if spoken_style == "inquisitive":
        if "," in text:
            return text.replace(",", ", ...", 1)
        words = text.split()
        if len(words) > 5:
            pivot = min(4, len(words) - 2)
            return " ".join(words[:pivot] + ["..."] + words[pivot:])
        return text

    if spoken_style == "pauses":
        for phrase in ("Well,", "Hmm,", "Let me", "So,", "Okay,"):
            if text.startswith(phrase):
                return text.replace(phrase, f"{phrase} ...", 1)
        if ". " in text:
            return text.replace(". ", "... ", 1)
        words = text.split()
        if len(words) > 7:
            pivot = len(words) // 2
            return " ".join(words[:pivot] + ["..."] + words[pivot:])
        return text

    if spoken_style == "calm":
        return text.replace(" - ", ", ")

    if spoken_style == "professional":
        return text

    return text


def prepare_spoken_text(text: str, mood: str | None = None) -> tuple[str, dict]:
    sanitized = sanitize_for_tts(text)
    if not sanitized:
        raise ValueError("No speakable text after sanitization")

    settings = resolve_mood_speech(mood)
    spoken = _apply_spoken_style(sanitized, settings.get("spoken_style", "none"))
    spoken = _maybe_prepend_cat_sound(spoken)
    return spoken, settings


async def _generate_tts_async(
    text: str,
    voice: str,
    output_path: str,
    *,
    rate: str,
    pitch: str,
    volume: str,
) -> None:
    communicate = edge_tts.Communicate(
        text,
        voice,
        rate=rate,
        pitch=pitch,
        volume=volume,
    )
    await communicate.save(output_path)


def generate_tts(text: str, voice: str, mood: str | None = None) -> None:
    spoken, settings = prepare_spoken_text(text, mood=mood)

    os.makedirs(RUNTIME_AUDIO_DIR, exist_ok=True)
    asyncio.run(
        _generate_tts_async(
            spoken,
            voice,
            LATEST_AUDIO_PATH,
            rate=settings.get("rate", "+0%"),
            pitch=settings.get("pitch", "+0Hz"),
            volume=settings.get("volume", "+0%"),
        )
    )
