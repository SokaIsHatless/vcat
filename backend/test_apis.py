from googleapiclient.discovery import build
from google_auth import get_credentials
from datetime import datetime, timedelta, timezone

creds = get_credentials()

# Calendar — list today's events
cal = build("calendar", "v3", credentials=creds)
now = datetime.now(timezone.utc)
end = now + timedelta(days=1)
events = cal.events().list(
    calendarId="primary",
    timeMin=now.isoformat(),
    timeMax=end.isoformat(),
    singleEvents=True,
    orderBy="startTime",
).execute().get("items", [])

print(f"\n=== Calendar: {len(events)} event(s) today ===")
for e in events:
    start = e["start"].get("dateTime", e["start"].get("date"))
    print(f"  {start} — {e.get('summary', '(no title)')}")

# Gmail — create a draft
gmail = build("gmail", "v1", credentials=creds)
import base64
from email.mime.text import MIMEText
msg = MIMEText("This is a test draft from Cat Overlord 😼")
msg["to"] = "mrityunjaykrithick@gmail.com"   # use your own email
msg["subject"] = "Test draft from the cat"
raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
draft = gmail.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
print(f"\n=== Gmail: created draft id={draft['id']} ===")
print("Check your Gmail → Drafts folder.")