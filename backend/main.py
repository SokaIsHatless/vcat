import os
import base64
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
load_dotenv()

import anthropic
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from agent import run_agent
from summaries import clear_summaries, delete_summary, list_summaries
from tts import (
    clear_voice_category,
    generate_tts,
    get_valid_voice_categories,
    get_voice_category,
    get_voice_options,
    has_voice_category,
    resolve_edge_voice,
    set_voice_category,
)

PERSONALITY_FILE = os.path.join(os.path.dirname(__file__), "personality.json")
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")
AUDIO_LATEST_URL = "http://localhost:8000/audio/latest"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CommandRequest(BaseModel):
    text: str


class VoiceRequest(BaseModel):
    voice: str


class SpeakRequest(BaseModel):
    reply: str
    mood: str | None = None


@app.get("/")
def health():
    return {"status": "ok"}


@app.get("/has_cat")
def has_cat():
    try:
        with open(PERSONALITY_FILE) as f:
            data = json.load(f)
        return {"has_cat": bool(data.get("personality"))}
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return {"has_cat": False}


@app.get("/greeting")
def get_greeting():
    fallback = "Well, look who's back. 🐾"
    try:
        personality = None
        try:
            with open(PERSONALITY_FILE) as f:
                personality = json.load(f).get("personality")
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass

        if not personality:
            return {"greeting": fallback}

        facts = _load_facts()
        facts_block = (
            " ".join(f"- {f}" for f in facts)
            if facts
            else "Nothing specific yet — greet them warmly anyway."
        )

        now = datetime.now(ZoneInfo("Asia/Kolkata"))

        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=128,
            temperature=1.0,
            messages=[{
                "role": "user",
                "content": (
                    f"You are a cat AI assistant with this personality: {personality}\n\n"
                    f"What you know about this human: {facts_block}\n\n"
                    f"The current date and time is {now.strftime('%A, %B %d, %Y at %I:%M %p')} (IST).\n\n"
                    "Write a brief launch greeting (1-2 sentences max) welcoming them back to their desktop.\n\n"
                    "STYLE RULES: Never use asterisk action narration (*purrs*, *tail swish*, *stretches*, "
                    "etc.) — you speak in words only, you do not describe your own movements. Be dry, witty, "
                    "and economical. One sharp line beats a rambling greeting.\n\n"
                    "VARY YOUR GREETINGS — don't always start with the user's name or 'welcome back'. Be "
                    "unpredictable and different each time. Rotate between different moods: tease the human "
                    "about something you know about them, comment dryly on the time of day, reference a "
                    "specific fact from memory, act reluctantly affectionate, or just be flatly sassy with no "
                    "specific hook at all. If you know their name or a preference, you may weave it in "
                    "naturally — but not every time.\n\n"
                    "Return ONLY the greeting text, nothing else."
                ),
            }],
        )
        text = response.content[0].text.strip()
        if text:
            print(f"★ GREETING: {text[:80]}...")
            return {"greeting": text}
    except Exception as exc:
        print(f"★ GREETING failed: {exc}")

    return {"greeting": fallback}


@app.post("/upload_cat")
async def upload_cat(file: UploadFile = File(...)):
    image_bytes = await file.read()
    if image_bytes[:3] == b'\xff\xd8\xff':
        media_type = "image/jpeg"
    elif image_bytes[:4] == b'\x89PNG':
        media_type = "image/png"
    elif image_bytes[8:12] == b'WEBP':
        media_type = "image/webp"
    elif image_bytes[:4] == b'GIF8':
        media_type = "image/gif"
    else:
        media_type = "image/jpeg"
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Look at this image and determine two things:\n"
                            "1. Whether it clearly contains a cat (real or cartoon/illustrated) — be lenient: "
                            "accept kittens, any breed, cartoonish or stylized cats, and cats in odd poses or "
                            "partial views. Only say it is NOT a cat if the image clearly shows something else "
                            "(a person, a dog, a car, a landscape, an object, etc.) with no cat present. "
                            "If genuinely ambiguous, lean toward saying it IS a cat.\n"
                            "2. If it is a cat, analyze its appearance and vibe. Write 2-3 sentences describing "
                            "a personality for an AI assistant modeled after this specific cat — its attitude, "
                            "tone, and how it speaks. Be specific to what you observe (e.g. a grumpy tabby → "
                            "blunt and sarcastic; a fluffy white cat → dreamy but chaotic). Write it as a direct "
                            "description of personality and speaking style, suitable for injecting into an AI "
                            "system prompt.\n\n"
                            "Respond with ONLY raw JSON, no markdown code fences, no explanation, in exactly "
                            "this shape:\n"
                            '{"is_cat": true, "personality": "<personality text>"}\n'
                            "or if it is not a cat:\n"
                            '{"is_cat": false, "personality": null}'
                        ),
                    },
                ],
            }
        ],
    )

    raw = response.content[0].text.strip()
    cleaned = re.sub(r"```[a-z]*\n?", "", raw).replace("```", "").strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    try:
        data = json.loads(cleaned[start:end + 1]) if start != -1 and end != -1 else {}
    except json.JSONDecodeError:
        data = {}

    is_cat = data.get("is_cat", True)
    personality = data.get("personality") or cleaned

    if not is_cat:
        print("★ UPLOAD REJECTED — not a cat")
        return JSONResponse(status_code=400, content={
            "is_cat": False,
            "error": "That doesn't look like a cat, human. I only serve feline overlords.",
        })

    with open(PERSONALITY_FILE, "w") as f:
        json.dump({"personality": personality}, f)

    print(f"★ PERSONALITY STORED: {personality[:80]}...")
    return {"is_cat": True, "personality": personality}


def _load_facts() -> list[str]:
    try:
        with open(MEMORY_FILE) as f:
            return json.load(f).get("facts", [])
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return []


def _save_facts(facts: list[str]) -> None:
    with open(MEMORY_FILE, "w") as f:
        json.dump({"facts": facts}, f, indent=2)


@app.delete("/cat")
def delete_cat():
    if os.path.exists(PERSONALITY_FILE):
        os.remove(PERSONALITY_FILE)
    _save_facts([])
    clear_voice_category()
    clear_summaries()
    print("★ CAT DELETED — personality, memory, voice, and summaries cleared")
    return {"ok": True}


@app.get("/memory")
def get_memory():
    return {"facts": _load_facts()}


@app.delete("/memory")
def clear_memory():
    _save_facts([])
    return {"facts": []}


@app.delete("/memory/{index}")
def delete_fact(index: int):
    facts = _load_facts()
    if 0 <= index < len(facts):
        facts.pop(index)
        _save_facts(facts)
    return {"facts": facts}


@app.get("/summaries")
def get_summaries():
    return {"summaries": list_summaries()}


@app.delete("/summaries/{index}")
def remove_summary(index: int):
    return {"summaries": delete_summary(index)}


@app.get("/audio/latest")
def get_latest_audio():
    from tts import LATEST_AUDIO_PATH

    if not os.path.exists(LATEST_AUDIO_PATH):
        return JSONResponse(status_code=404, content={"error": "No audio generated yet"})
    return FileResponse(
        LATEST_AUDIO_PATH,
        media_type="audio/mpeg",
        filename="latest.mp3",
    )


@app.get("/voice")
def get_voice():
    category = get_voice_category()
    return {
        "voice": category,
        "has_voice": category is not None,
        "options": get_voice_options(),
    }


@app.post("/voice")
def save_voice(body: VoiceRequest):
    if body.voice not in get_valid_voice_categories():
        return JSONResponse(
            status_code=400,
            content={"error": f"voice must be one of: {', '.join(get_valid_voice_categories())}"},
        )
    set_voice_category(body.voice)
    print(f"★ VOICE SET: {body.voice}")
    return {"voice": body.voice}


def _try_generate_tts(reply: str, mood: str | None = None) -> bool:
    try:
        generate_tts(reply, resolve_edge_voice(), mood=mood)
        print(f"★ TTS saved latest.mp3 (mood={mood or 'idle'})")
        return True
    except Exception as exc:
        print(f"★ TTS failed (non-fatal): {exc}")
        return False


def _with_audio_url(result: dict) -> dict:
    if _try_generate_tts(result.get("reply", ""), mood=result.get("mood")):
        result["audio_url"] = AUDIO_LATEST_URL
    return result


@app.post("/speak")
def speak(body: SpeakRequest):
    """Generate TTS for a fixed reply (e.g. timer completion) using the same pipeline as /command."""
    result = {"reply": body.reply, "mood": body.mood or "idle"}
    return _with_audio_url(result)


@app.post("/command")
def command(body: CommandRequest):
    print(f"→ COMMAND: {body.text}")
    try:
        result = run_agent(body.text)
        print(f"← REPLY (mood={result['mood']}, tools={result['tools_used']})")
        return _with_audio_url(result)
    except Exception:
        result = {
            "reply": "Something broke, human. Even cats have limits. 🐾",
            "mood": "confused",
            "tools_used": [],
        }
        return _with_audio_url(result)
