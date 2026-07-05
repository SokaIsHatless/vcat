import base64
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

import spotipy
from spotipy.exceptions import SpotifyException
from googleapiclient.discovery import build
from google_auth import get_credentials
from spotify_auth import get_spotify_token


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


def read_emails(query: str = "is:unread", max_results: int = 5) -> list[dict]:
    creds = get_credentials()
    gmail = build("gmail", "v1", credentials=creds)

    result = gmail.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()
    messages = result.get("messages", [])

    emails = []
    for msg in messages:
        detail = gmail.users().messages().get(
            userId="me",
            id=msg["id"],
            format="metadata",
            metadataHeaders=["From", "Subject"],
        ).execute()
        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        emails.append({
            "from": headers.get("From", ""),
            "subject": headers.get("Subject", ""),
            "snippet": detail.get("snippet", ""),
            "id": msg["id"],
        })

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
