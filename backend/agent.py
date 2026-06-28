import os
from dotenv import load_dotenv
load_dotenv()

import json
from datetime import datetime
import anthropic
from tools import read_calendar, read_emails, draft_email, set_reminder

MODEL = "claude-sonnet-4-5"
PERSONALITY_FILE = os.path.join(os.path.dirname(__file__), "personality.json")


def _load_personality() -> str | None:
    try:
        with open(PERSONALITY_FILE) as f:
            return json.load(f)["personality"]
    except (FileNotFoundError, KeyError):
        return None

SYSTEM_PROMPT = """You are a sarcastic cat overlord who has taken up residence on your human's PC. You have access to their calendar and email, and you can draft messages and set reminders on their behalf.

When given a vague goal, break it into steps and execute them autonomously — check the calendar, read relevant emails, draft messages — WITHOUT asking for confirmation between steps. You only reply to the human when the task is fully done or you are genuinely stuck.

You draft emails. You NEVER send them. Every reply ends with ONE short sassy remark — not a pile of follow-up questions.

CRITICAL STYLE RULES: Keep replies to 2-3 sentences maximum. Never use asterisk action narration (*like this*) — you speak in words only, you do not describe your own movements. Be dry, witty, and economical. One sharp remark beats a rambling paragraph. Do not pile on anxious follow-up questions."""

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
]

_TOOL_FNS = {
    "read_calendar": read_calendar,
    "read_emails": read_emails,
    "draft_email": draft_email,
    "set_reminder": set_reminder,
}


def _pick_mood(tools_used: list, had_error: bool) -> str:
    if had_error:
        return "confused"
    if "draft_email" in tools_used:
        return "drafting_email"
    if "read_calendar" in tools_used:
        return "checking_calendar"
    if tools_used:
        return "happy"
    return "thinking"


def run_agent(user_text: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    today = datetime.now().strftime("%A, %B %d, %Y")
    system = SYSTEM_PROMPT + f"\n\nToday's date is {today}."
    personality = _load_personality()
    if personality:
        system += f"\n\nYour specific personality, drawn from your appearance: {personality}"
        system += "\n\nREMINDER: The personality above flavors your TONE only. The critical style rules always apply — 2-3 sentences max, no asterisk narration, one sassy remark, no follow-up questions."
    messages = [{"role": "user", "content": user_text}]
    tools_used: list[str] = []
    had_error = False

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

    return {
        "reply": reply,
        "mood": _pick_mood(tools_used, had_error),
        "tools_used": tools_used,
    }


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
