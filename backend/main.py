import os
import base64
import json
from dotenv import load_dotenv
load_dotenv()

import anthropic
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent import run_agent

PERSONALITY_FILE = os.path.join(os.path.dirname(__file__), "personality.json")
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CommandRequest(BaseModel):
    text: str


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


@app.delete("/cat")
def delete_cat():
    if os.path.exists(PERSONALITY_FILE):
        os.remove(PERSONALITY_FILE)
    _save_facts([])
    print("★ CAT DELETED — personality and memory cleared")
    return {"ok": True}


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
                            "Analyze this cat's appearance and vibe. "
                            "Write 2-3 sentences describing a personality for an AI assistant modeled after this specific cat — "
                            "its attitude, tone, and how it speaks. Be specific to what you observe "
                            "(e.g. a grumpy tabby → blunt and sarcastic; a fluffy white cat → dreamy but chaotic). "
                            "Write it as a direct description of personality and speaking style, suitable for injecting into an AI system prompt."
                        ),
                    },
                ],
            }
        ],
    )

    personality = response.content[0].text.strip()
    with open(PERSONALITY_FILE, "w") as f:
        json.dump({"personality": personality}, f)

    print(f"★ PERSONALITY STORED: {personality[:80]}...")
    return {"personality": personality}


def _load_facts() -> list[str]:
    try:
        with open(MEMORY_FILE) as f:
            return json.load(f).get("facts", [])
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return []


def _save_facts(facts: list[str]) -> None:
    with open(MEMORY_FILE, "w") as f:
        json.dump({"facts": facts}, f, indent=2)


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


@app.post("/command")
def command(body: CommandRequest):
    print(f"→ COMMAND: {body.text}")
    try:
        result = run_agent(body.text)
        print(f"← REPLY (mood={result['mood']}, tools={result['tools_used']})")
        return result
    except Exception:
        return {
            "reply": "Something broke, human. Even cats have limits. 🐾",
            "mood": "confused",
            "tools_used": [],
        }
