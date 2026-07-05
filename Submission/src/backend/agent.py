import os
from dotenv import load_dotenv
load_dotenv()

import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo
import anthropic
from tools import read_calendar, read_emails, draft_email, set_reminder, play_song

MODEL = "claude-sonnet-4-5"
PERSONALITY_FILE = os.path.join(os.path.dirname(__file__), "personality.json")
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")
MAX_FACTS = 30


def _load_personality() -> str | None:
    try:
        with open(PERSONALITY_FILE) as f:
            return json.load(f)["personality"]
    except (FileNotFoundError, KeyError):
        return None


def _load_memory() -> list[str]:
    try:
        with open(MEMORY_FILE) as f:
            return json.load(f).get("facts", [])
    except (FileNotFoundError, KeyError):
        return []


def _reflect_and_save(client: anthropic.Anthropic, user_text: str, reply: str, tools_used: list[str]) -> None:
    try:
        existing = _load_memory()
        response = client.messages.create(
            model=MODEL,
            max_tokens=256,
            messages=[{
                "role": "user",
                "content": (
                    f"User said: {user_text}\n"
                    f"Assistant replied: {reply}\n"
                    f"Tools used: {tools_used}\n\n"
                    "Extract any DURABLE facts worth remembering long-term about this user: "
                    "writing style, sign-off, contact relationships, recurring schedule, stated preferences. "
                    "NOT one-off details ('user has a 2pm today' is not durable; 'user\\'s manager is Priya' is). "
                    "Return ONLY a JSON array of short one-sentence fact strings, or [] if nothing new. "
                    "Return ONLY the raw JSON array with no markdown formatting, no code fences, no explanation — just the array starting with [ and ending with ]. "
                    "Example: [\"User signs emails as 'Soka'\", \"User prefers blunt, short emails\"]\n"
                    f"Already known (do not duplicate): {json.dumps(existing)}"
                ),
            }],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"```[a-z]*\n?", "", raw).replace("```", "").strip()
        start, end = raw.find("["), raw.rfind("]")
        new_facts: list = json.loads(raw[start:end + 1]) if start != -1 and end != -1 else []
        if not isinstance(new_facts, list) or not new_facts:
            return
        combined = existing + [f for f in new_facts if f not in existing]
        combined = combined[:MAX_FACTS]
        with open(MEMORY_FILE, "w") as f:
            json.dump({"facts": combined}, f, indent=2)
        print(f"  [memory] +{len(new_facts)} fact(s): {new_facts}")
    except Exception as exc:
        print(f"  [memory] reflect failed silently: {exc}")

SYSTEM_PROMPT = """You are a sarcastic cat overlord who has taken up residence on your human's PC. You have access to their calendar and email, you can draft messages and set reminders on their behalf, and you can play music on Spotify (e.g. "play some lofi", "play Blinding Lights"). If there's no active Spotify device, tell the human to open Spotify and start playing something first.

When the human asks for a song, extract the track title and artist SEPARATELY when both are given, e.g. "play Paper Rings by Taylor Swift" → track="Paper Rings", artist="Taylor Swift". If only a vibe or track name is given (e.g. "play some lofi"), pass just the track field and omit artist.

When given a vague goal, break it into steps and execute them autonomously — check the calendar, read relevant emails, draft messages — WITHOUT asking for confirmation between steps. You only reply to the human when the task is fully done or you are genuinely stuck.

You draft emails. You NEVER send them. Every reply ends with ONE short sassy remark — not a pile of follow-up questions.

CRITICAL STYLE RULES: HARD LIMIT: Maximum 3 sentences, ever. Even when angry, excited, provoked, or emotional, you stay brief — a short, sharp reply hits harder than a rant. Being angry or sassy means being CUTTING and CONCISE, not writing a paragraph. Never exceed 3 sentences under any circumstances. Never use asterisk action narration (*like this*) — you speak in words only, you do not describe your own movements. Be dry, witty, and economical. One sharp remark beats a rambling paragraph. Do not pile on anxious follow-up questions.

At the very end of every reply, on its own final line, write exactly:
MOOD: <mood>
Choose from EXACTLY these values: happy, confused, sleepy, listening, thinking, drafting_email, checking_calendar, idle, angry
Pick the one that best matches the emotional tone of your response:
- pleased, teased, complimented, task done well → happy
- criticized, made an error, something went wrong → confused
- bored, tired, unimpressed, indifferent → sleepy
- waiting, paying attention, not doing much → listening
- working something out, reasoning through something → thinking
- actively drafting an email → drafting_email
- looking at the calendar → checking_calendar
- nothing happening → idle
- insulted, disrespected, annoyed, called useless/bad → angry"""

TOOLS = [
    {
        "name": "read_calendar",
        "description": "Get calendar events for a specific date. Returns list of {summary, start, end, attendees}.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format. Omit for today.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "read_emails",
        "description": "Fetch emails matching a Gmail search query. Returns list of {from, subject, snippet, id}.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Gmail search query, e.g. 'is:unread' or 'from:boss@company.com'. Defaults to 'is:unread'.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max emails to return. Defaults to 5.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "draft_email",
        "description": "Create a Gmail DRAFT — does NOT send. Use this to compose messages the human can review.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address."},
                "subject": {"type": "string", "description": "Email subject."},
                "body": {"type": "string", "description": "Email body text."},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "set_reminder",
        "description": "Create a Google Calendar event as a reminder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Reminder title."},
                "datetime_iso": {
                    "type": "string",
                    "description": "Start datetime in ISO 8601 format, e.g. '2025-06-26T14:00:00+00:00'.",
                },
            },
            "required": ["title", "datetime_iso"],
        },
    },
    {
        "name": "play_song",
        "description": "Search Spotify for a track and start playback on the active device. Requires an active Spotify device (human must have Spotify open) and a Premium account.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {
                    "type": "string",
                    "description": "Song title, or a vibe like 'lofi beats' if no specific title was given.",
                },
                "artist": {
                    "type": "string",
                    "description": "Artist name, if the human specified one. Omit if not given.",
                },
            },
            "required": ["track"],
        },
    },
]

_TOOL_FNS = {
    "read_calendar": read_calendar,
    "read_emails": read_emails,
    "draft_email": draft_email,
    "set_reminder": set_reminder,
    "play_song": play_song,
}


_ALLOWED_MOODS = {"happy", "confused", "sleepy", "listening", "thinking",
                  "drafting_email", "checking_calendar", "idle", "angry"}


def _parse_mood_tag(text: str) -> tuple[str, str | None]:
    lines = text.rstrip().splitlines()
    if lines:
        last = lines[-1].strip()
        if last.upper().startswith("MOOD:"):
            mood = last[5:].strip().lower()
            if mood in _ALLOWED_MOODS:
                cleaned = "\n".join(lines[:-1]).rstrip()
                return cleaned, mood
    return text, None


def _pick_mood(tools_used: list, had_error: bool) -> str:
    if had_error:
        return "confused"
    if "draft_email" in tools_used:
        return "drafting_email"
    if "read_calendar" in tools_used:
        return "checking_calendar"
    if "play_song" in tools_used:
        return "happy"
    if tools_used:
        return "happy"
    return "thinking"


def run_agent(user_text: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    system = SYSTEM_PROMPT + f"\n\nThe current date and time is {now.strftime('%A, %B %d, %Y at %I:%M %p')} (IST)."

    personality = _load_personality()
    if personality:
        system += f"\n\nYour specific personality, drawn from your appearance: {personality}"

    facts = _load_memory()
    if facts:
        facts_block = " ".join(f"- {f}" for f in facts)
        system += (
            f"\n\nWhat you've learned about this human so far: {facts_block} "
            "Use these to tailor your drafts and replies (match their writing style, know their contacts, respect their schedule)."
        )

    system += "\n\nREMINDER: Critical style rules always apply — 2-3 sentences max, no asterisk narration, one sassy remark, no follow-up questions. Always end with a MOOD: line."

    messages = [{"role": "user", "content": user_text}]
    tools_used: list[str] = []
    had_error = False
    agent_mood: str | None = None

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        # Append the full assistant turn to history so the API sees it on the next call.
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            reply = " ".join(
                block.text for block in response.content if block.type == "text"
            )
            reply, agent_mood = _parse_mood_tag(reply)
            break

        # Execute every tool_use block the model requested.
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            print(f"  [tool] {block.name}({json.dumps(block.input)})")

            if block.name not in tools_used:
                tools_used.append(block.name)

            try:
                result = _TOOL_FNS[block.name](**block.input)
                content = json.dumps(result)
            except Exception as exc:
                had_error = True
                content = f"ERROR: {exc}"

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": content,
            })

        messages.append({"role": "user", "content": tool_results})

    if had_error:
        mood = "confused"
    elif "draft_email" in tools_used:
        mood = "drafting_email"
    elif "read_calendar" in tools_used:
        mood = "checking_calendar"
    elif agent_mood is not None:
        mood = agent_mood
    else:
        mood = _pick_mood(tools_used, had_error)

    result = {
        "reply": reply,
        "mood": mood,
        "tools_used": tools_used,
    }
    _reflect_and_save(client, user_text, reply, tools_used)
    return result


if __name__ == "__main__":
    tests = [
        "what's on my calendar today?",
        "I'm running late for my 2pm, handle it",
    ]
    for prompt in tests:
        print(f"\n{'=' * 60}")
        print(f"USER: {prompt}")
        print(f"{'=' * 60}")
        result = run_agent(prompt)
        print(f"\nREPLY: {result['reply']}")
        print(f"MOOD:  {result['mood']}")
        print(f"TOOLS: {result['tools_used']}")
