from datetime import datetime, timedelta, timezone
from tools import read_calendar, read_emails, draft_email, set_reminder

print("=== 1. read_calendar (today) ===")
events = read_calendar()
print(events)

print("\n=== 2. read_emails (unread, max 3) ===")
emails = read_emails(max_results=3)
print(emails)

print("\n=== 3. draft_email ===")
draft = draft_email(
    to="24f2005971@ds.study.iitm.ac.in",
    subject="Test draft from vcat tools",
    body="This is a test draft created by tools.py. Safe to delete.",
)
print(draft)

print("\n=== 4. set_reminder ===")
dt_iso = (datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=1)).isoformat()
reminder = set_reminder("vcat test reminder", dt_iso)
print(reminder)
