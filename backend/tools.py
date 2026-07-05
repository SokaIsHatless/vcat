import base64
import os
import re
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from urllib.parse import quote

import feedparser
import requests
import spotipy
from spotipy.exceptions import SpotifyException
from googleapiclient.discovery import build
from google_auth import get_credentials
from spotify_auth import get_spotify_token
from app_finder import open_application


def read_calendar(date: str = None) -> list[dict]:
    # Day boundaries are UTC midnight, so events near IST midnight may appear
    # on the wrong day. Will fix with proper IST offset when needed.
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    time_min = f"{date}T00:00:00Z"
    time_max = f"{date}T23:59:59Z"

    creds = get_credentials()
    cal = build("calendar", "v3", credentials=creds)
    items = cal.events().list(
        calendarId="primary",
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime",
    ).execute().get("items", [])

    return [
        {
            "summary": e.get("summary", "(no title)"),
            "start": e["start"].get("dateTime", e["start"].get("date")),
            "end": e["end"].get("dateTime", e["end"].get("date")),
            "attendees": [a["email"] for a in e.get("attendees", [])],
        }
        for e in items
    ]


def _extract_body(payload: dict) -> str:
    def find(part: dict, mime_target: str) -> str | None:
        if part.get("mimeType") == mime_target and part.get("body", {}).get("data"):
            return part["body"]["data"]
        for sub in part.get("parts", []) or []:
            found = find(sub, mime_target)
            if found:
                return found
        return None

    data = find(payload, "text/plain")
    is_html = False
    if not data:
        data = find(payload, "text/html")
        is_html = data is not None
    if not data:
        return ""

    text = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    if is_html:
        text = re.sub(r"<[^>]+>", " ", text)
    text = text.strip()

    limit = 3000
    if len(text) > limit:
        text = text[:limit] + "... [truncated]"
    return text


def read_emails(query: str = "is:unread", max_results: int = 5, include_body: bool = False) -> list[dict]:
    creds = get_credentials()
    gmail = build("gmail", "v1", credentials=creds)

    result = gmail.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()
    messages = result.get("messages", [])

    emails = []
    for msg in messages:
        if include_body:
            detail = gmail.users().messages().get(
                userId="me", id=msg["id"], format="full",
            ).execute()
        else:
            detail = gmail.users().messages().get(
                userId="me",
                id=msg["id"],
                format="metadata",
                metadataHeaders=["From", "Subject"],
            ).execute()
        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        email = {
            "from": headers.get("From", ""),
            "subject": headers.get("Subject", ""),
            "snippet": detail.get("snippet", ""),
            "id": msg["id"],
        }
        if include_body:
            email["body"] = _extract_body(detail["payload"])
        emails.append(email)

    return emails


def draft_email(to: str, subject: str, body: str) -> dict:
    creds = get_credentials()
    gmail = build("gmail", "v1", credentials=creds)

    msg = MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    draft = gmail.users().drafts().create(
        userId="me", body={"message": {"raw": raw}}
    ).execute()
    return {"draft_id": draft["id"]}


def set_reminder(title: str, datetime_iso: str) -> dict:
    # If Calendar returns 400, try dropping "timeZone" or stripping the UTC
    # offset from datetime_iso — the two fields can conflict.
    creds = get_credentials()
    cal = build("calendar", "v3", credentials=creds)

    end_iso = (
        datetime.fromisoformat(datetime_iso) + timedelta(hours=1)
    ).isoformat()

    event = cal.events().insert(
        calendarId="primary",
        body={
            "summary": title,
            "start": {"dateTime": datetime_iso, "timeZone": "UTC"},
            "end": {"dateTime": end_iso, "timeZone": "UTC"},
            "reminders": {"useDefault": True},
        },
    ).execute()
    return {"event_id": event["id"]}


def play_song(track: str, artist: str = None) -> dict:
    sp = spotipy.Spotify(auth=get_spotify_token())

    query = f'track:"{track}" artist:"{artist}"' if artist else f'track:"{track}"'
    print(f"  [play_song] search query: {query}")

    results = sp.search(q=query, type="track", limit=1)
    tracks = results.get("tracks", {}).get("items", [])
    if not tracks:
        return {"error": "couldn't find that song"}

    top = tracks[0]
    track_uri = top["uri"]
    track_name = top["name"]
    artist_name = top["artists"][0]["name"] if top["artists"] else "unknown artist"
    print(f"  [play_song] matched: {track_name} by {artist_name}")

    try:
        sp.start_playback(uris=[track_uri])
    except SpotifyException as exc:
        if exc.http_status == 404 or "No active device" in str(exc):
            return {"error": "no active Spotify device — open Spotify and play something first, then try again"}
        if exc.http_status == 403:
            return {"error": "Spotify Premium required for playback"}
        return {"error": f"couldn't start playback: {exc}"}

    return {"playing": f"{track_name} by {artist_name}"}


def _summaries_dir() -> str:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return os.path.join(local_appdata, "vcat", "summaries")
    return os.path.join(os.path.expanduser("~"), ".vcat", "summaries")


def ensure_summaries_dir() -> str:
    d = _summaries_dir()
    os.makedirs(d, exist_ok=True)
    return d


def save_summary(content: str, title: str) -> dict:
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", title).strip()
    sanitized = re.sub(r"\s+", "_", sanitized) or "summary"
    filename = f"{sanitized}_{datetime.now().strftime('%Y-%m-%d_%H%M')}.txt"

    target_dir = _summaries_dir()
    os.makedirs(target_dir, exist_ok=True)
    full_path = os.path.join(target_dir, filename)

    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as exc:
        return {"error": str(exc)}

    from summaries import register_summary

    register_summary(filename, full_path, title.strip() or "Summary")
    return {"saved_to": full_path, "filename": filename}


def delete_summary_file(path: str) -> dict:
    base_dir = os.path.abspath(_summaries_dir())
    target = os.path.abspath(path)

    try:
        inside = os.path.commonpath([base_dir, target]) == base_dir
    except ValueError:
        inside = False

    if not inside:
        return {"error": "path outside summaries folder — refusing to delete"}

    try:
        os.remove(target)
    except FileNotFoundError:
        return {"deleted": True}
    except OSError as exc:
        return {"error": str(exc)}

    return {"deleted": True}


def delete_all_summary_files() -> dict:
    target_dir = _summaries_dir()
    if not os.path.isdir(target_dir):
        return {"deleted": 0}

    count = 0
    for name in os.listdir(target_dir):
        full_path = os.path.join(target_dir, name)
        if name.lower().endswith(".txt") and os.path.isfile(full_path):
            try:
                os.remove(full_path)
                count += 1
            except OSError:
                pass

    return {"deleted": count}


def start_timer(minutes: int = 25) -> dict:
    """Start a local focus/Pomodoro timer (no external APIs). Frontend runs the countdown."""
    try:
        minutes = int(minutes)
    except (TypeError, ValueError):
        minutes = 25
    minutes = max(1, min(minutes, 240))
    return {
        "started": True,
        "minutes": minutes,
        "message": f"Timer started for {minutes} minute(s). Hourglass shows until break time.",
    }


RAM_ALERT_PERCENT = 85
CPU_ALERT_PERCENT = 90


def check_system_resources() -> dict:
    """Read local CPU and RAM usage via psutil. No external APIs."""
    import psutil

    cpu_percent = psutil.cpu_percent(interval=0.4)
    mem = psutil.virtual_memory()
    ram_percent = mem.percent
    ram_used_gb = round(mem.used / (1024 ** 3), 1)
    ram_total_gb = round(mem.total / (1024 ** 3), 1)

    high_ram = ram_percent >= RAM_ALERT_PERCENT
    high_cpu = cpu_percent >= CPU_ALERT_PERCENT

    alert = None
    if high_ram:
        alert = {
            "type": "ram",
            "overlay": "fire",
            "ram_percent": round(ram_percent, 1),
            "cpu_percent": round(cpu_percent, 1),
        }
    elif high_cpu:
        alert = {
            "type": "cpu",
            "overlay": "fire",
            "ram_percent": round(ram_percent, 1),
            "cpu_percent": round(cpu_percent, 1),
        }

    return {
        "cpu_percent": round(cpu_percent, 1),
        "ram_percent": round(ram_percent, 1),
        "ram_used_gb": ram_used_gb,
        "ram_total_gb": ram_total_gb,
        "high_ram": high_ram,
        "high_cpu": high_cpu,
        "alert": alert,
    }


DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/"
_LOOKUP_STOP_WORDS = frozenset({
    "a", "an", "the", "of", "is", "it", "for", "please",
    "define", "definition", "meaning", "mean", "means", "word", "what", "does",
})


def _extract_lookup_word(raw: str) -> str:
    """Pull the target English word from a bare word or short phrase."""
    tokens = re.findall(r"[a-zA-Z][\w'-]*", raw.strip())
    if not tokens:
        return ""
    filtered = [t for t in tokens if t.lower() not in _LOOKUP_STOP_WORDS]
    target = filtered[-1] if filtered else tokens[-1]
    return re.sub(r"[^\w'-]", "", target.lower())


def define_word(word: str) -> dict:
    """Look up any English word via the Free Dictionary API."""
    cleaned = _extract_lookup_word(word)
    if not cleaned:
        return {"found": False, "error": "No word provided"}

    url = f"{DICTIONARY_API_URL}{quote(cleaned)}"
    try:
        response = requests.get(url, timeout=10)
    except requests.RequestException as exc:
        return {"found": False, "word": cleaned, "error": f"Dictionary lookup failed: {exc}"}

    if response.status_code == 404:
        return {"found": False, "word": cleaned, "error": "Word not found"}
    if not response.ok:
        return {"found": False, "word": cleaned, "error": f"HTTP {response.status_code}"}

    try:
        data = response.json()
    except ValueError:
        return {"found": False, "word": cleaned, "error": "Invalid dictionary response"}

    if not isinstance(data, list) or not data:
        return {"found": False, "word": cleaned, "error": "Word not found"}

    entry = data[0]
    meanings = []
    for meaning in entry.get("meanings", [])[:3]:
        definitions = [
            item.get("definition", "")
            for item in meaning.get("definitions", [])[:2]
            if item.get("definition")
        ]
        if definitions:
            meanings.append({
                "part_of_speech": meaning.get("partOfSpeech"),
                "definitions": definitions,
            })

    return {
        "found": True,
        "word": entry.get("word", cleaned),
        "phonetic": entry.get("phonetic"),
        "meanings": meanings,
    }


IP_GEOLOCATION_API_URL = "http://ip-api.com/json/"
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"

_WEATHER_CODE_DESCRIPTIONS = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "foggy",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    61: "light rain",
    63: "moderate rain",
    65: "heavy rain",
    71: "light snow",
    73: "moderate snow",
    75: "heavy snow",
    80: "rain showers",
    81: "rain showers",
    82: "violent rain showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "thunderstorm with hail",
}


def _describe_weather_code(code: int) -> str:
    """Map an Open-Meteo WMO weather code to a human-friendly description."""
    return _WEATHER_CODE_DESCRIPTIONS.get(code, "unusual weather")


def get_weather() -> dict:
    """Get current weather for the human's approximate location, based on IP geolocation."""
    try:
        geo_response = requests.get(IP_GEOLOCATION_API_URL, timeout=5)
    except requests.RequestException:
        return {"error": "couldn't figure out where you are, human"}

    if not geo_response.ok:
        return {"error": "couldn't figure out where you are, human"}

    try:
        geo_data = geo_response.json()
    except ValueError:
        return {"error": "couldn't figure out where you are, human"}

    lat = geo_data.get("lat")
    lon = geo_data.get("lon")
    city = geo_data.get("city")
    country = geo_data.get("country")
    if lat is None or lon is None:
        return {"error": "couldn't figure out where you are, human"}

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "temperature_unit": "celsius",
    }
    try:
        weather_response = requests.get(WEATHER_API_URL, params=params, timeout=5)
    except requests.RequestException as exc:
        return {"error": f"weather lookup failed: {exc}"}

    if not weather_response.ok:
        return {"error": f"weather lookup failed: HTTP {weather_response.status_code}"}

    try:
        weather_data = weather_response.json()
    except ValueError:
        return {"error": "invalid weather response"}

    current = weather_data.get("current")
    if not isinstance(current, dict):
        return {"error": "invalid weather response"}

    try:
        temperature_c = float(current["temperature_2m"])
        humidity = int(current["relative_humidity_2m"])
        wind_kmh = float(current["wind_speed_10m"])
        weather_code = int(current["weather_code"])
    except (KeyError, TypeError, ValueError):
        return {"error": "invalid weather response"}

    return {
        "city": city,
        "country": country,
        "temperature_c": temperature_c,
        "humidity": humidity,
        "wind_kmh": wind_kmh,
        "description": _describe_weather_code(weather_code),
    }


NEWS_RSS_URL = "http://feeds.bbci.co.uk/news/world/rss.xml"


def _clean_summary(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", "", text or "").strip()
    return cleaned[:200]


def get_news(count: int = 5) -> dict:
    """Get the latest BBC World News headlines via RSS."""
    count = max(1, min(count, 10))

    try:
        response = requests.get(NEWS_RSS_URL, timeout=5)
    except requests.RequestException:
        return {"error": "couldn't grab the news, human — the internet's being uncooperative"}

    if not response.ok:
        return {"error": "couldn't grab the news, human — the internet's being uncooperative"}

    try:
        feed = feedparser.parse(response.content)
    except Exception:
        return {"error": "couldn't grab the news, human — the internet's being uncooperative"}

    if not feed.entries:
        return {"error": "couldn't grab the news, human — the internet's being uncooperative"}

    headlines = [
        {
            "title": entry.get("title", ""),
            "summary": _clean_summary(entry.get("summary", entry.get("description", ""))),
        }
        for entry in feed.entries[:count]
    ]

    return {
        "source": "BBC World News",
        "headlines": headlines,
    }


SCREENSHOT_MAX_EDGE = 1568
VISION_MODEL = "claude-sonnet-4-5"

SCREENSHOT_FOCUS_PROMPTS = {
    "general": (
        "This is a screenshot of the user's Windows desktop. Describe what is on screen: "
        "open apps, visible text, and anything notable. Be specific and concise."
    ),
    "error": (
        "This is a screenshot of the user's screen. Look for error messages, compiler output, "
        "IDE red squiggles, dialog boxes, or stack traces. Explain what is wrong in plain "
        "language and the most likely fix if you can see it."
    ),
}


def _resize_screenshot(img):
    from PIL import Image

    width, height = img.size
    longest = max(width, height)
    if longest <= SCREENSHOT_MAX_EDGE:
        return img
    scale = SCREENSHOT_MAX_EDGE / longest
    return img.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)


def capture_screenshot(focus: str = "general") -> dict:
    """Capture the desktop with pyautogui and analyze via Claude vision."""
    import io
    import os

    import anthropic
    import pyautogui

    focus_key = focus if focus in SCREENSHOT_FOCUS_PROMPTS else "general"

    try:
        img = pyautogui.screenshot()
    except Exception as exc:
        return {"captured": False, "error": f"Screenshot failed: {exc}"}

    img = _resize_screenshot(img)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    image_b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"captured": False, "error": "ANTHROPIC_API_KEY not set"}

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=VISION_MODEL,
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_b64,
                    },
                },
                {
                    "type": "text",
                    "text": SCREENSHOT_FOCUS_PROMPTS[focus_key],
                },
            ],
        }],
    )
    analysis = "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()

    if not analysis:
        return {"captured": False, "error": "Vision analysis returned no text"}

    return {
        "captured": True,
        "focus": focus_key,
        "analysis": analysis,
    }
