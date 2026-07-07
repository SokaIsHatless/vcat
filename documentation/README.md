# Cat Overlord 🐾

*An AI desktop pet with the personality of your cat, that helps developers manage the boring parts of their day.*

Cat Overlord is a floating, always-on-top Electron desktop pet powered by Anthropic's Claude Sonnet 4.5. Upload a photo of your cat, and its personality (extracted from the photo by Claude Vision) shapes every reply. Then talk to it in natural language — it can read your calendar, draft emails, summarize your inbox, play Spotify, open apps, run a Pomodoro timer, look up the weather and news, define words, analyze what's on your screen, and remember things about you across sessions.

Built for the **#hackthekitty 2026** hackathon under the **For Developers** theme by team **error404**.

---

## Table of Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running the app](#running-the-app)
- [How to use it](#how-to-use-it)
- [Project structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [Known limitations](#known-limitations)
- [Team](#team)
- [Acknowledgments](#acknowledgments)

---

## Features

### The cat itself
- Floating, transparent, always-on-top desktop cat you can drag around
- Personality generated from your uploaded cat photo (Claude Vision)
- Persistent memory that learns durable facts about you and applies them to future tasks
- Mood-driven animations and overlays (happy, angry, confused, sleepy, music, fire, and more)
- Text-to-speech with mood-aware voice modulation and cat sound effects
- Personalized launch greeting

### Google integrations
- **Calendar** — reads events across all your subscribed calendars, creates reminders
- **Gmail** — reads emails, summarizes them to `.txt` files, drafts messages (never sends)

### Developer tools
- **Screen analysis** — silently captures a screenshot and describes what you're looking at, including code
- **App launcher** — opens installed Windows apps by name, with denylist protection for system shells and admin tools
- **Focus timer** — Pomodoro with countdown UI and TTS break announcements
- **CPU/RAM monitoring** — a fire overlay animates when your system gets hot

### Everything else
- Spotify song playback on your Premium account
- Weather via IP geolocation + Open-Meteo
- News headlines from BBC RSS
- Dictionary word lookups
- Session chat history panel, memory panel (view/delete what the cat knows), saved-summaries panel

For a full list of features and how they fit together, see [`documentation/project_report.md`](documentation/project_report.md).

---

## Screenshots

*(Add these before submission — leaving placeholders here so you don't forget)*

- Upload screen
- Cat with speech bubble mid-conversation
- Memory panel showing learned facts
- Summaries panel
- Mood animations (happy, angry)

---

## Prerequisites

Cat Overlord is currently **Windows-only** (relies on `Get-StartApps`, `%LOCALAPPDATA%`, `os.startfile`).

You'll need:

### Software
- **Windows 10 or 11**
- **Python 3.11 or newer** — [python.org](https://www.python.org/downloads/)
- **Node.js 18 or newer** (bundled with npm) — [nodejs.org](https://nodejs.org/)
- **Git** — [git-scm.com](https://git-scm.com/)

### API credentials (all free tiers except Spotify)
- **Anthropic API key** — [console.anthropic.com](https://console.anthropic.com/). You need Claude API access.
- **Google Cloud OAuth credentials** — for Gmail and Calendar. Setup instructions below.
- **Spotify Developer credentials** — [developer.spotify.com](https://developer.spotify.com/). Music playback requires a **Spotify Premium** account.

### No signup needed
- Open-Meteo (weather) — no key
- ip-api.com (location) — no key
- BBC News RSS (news) — no key
- Free Dictionary API — no key

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/SokaIsHatless/vcat.git
cd vcat
```

### 2. Set up Google Cloud credentials

Cat Overlord uses OAuth to read your Gmail and Calendar. You'll create your own OAuth app so the credentials stay yours.

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create a new project.
2. Enable the **Gmail API** and **Google Calendar API** for that project.
3. Go to **APIs & Services → OAuth consent screen**, choose **External**, fill in the required fields, and add yourself as a test user.
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
5. Choose **Desktop app**, name it anything, and download the resulting JSON.
6. Save that JSON as `backend/credentials.json`.

The requested scopes should be:
- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/gmail.compose`
- `https://www.googleapis.com/auth/calendar`

⚠️ In **Testing** mode, Google expires refresh tokens after 7 days. You'll need to re-authorize weekly (see [Troubleshooting](#troubleshooting)).

### 3. Set up Spotify credentials

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and create an app.
2. Set the **Redirect URI** to exactly `http://127.0.0.1:8888/callback` (not `localhost` — Spotify no longer accepts `http://localhost` for security reasons).
3. Copy the **Client ID** and **Client Secret**.

### 4. Configure environment variables

Create `backend/.env` with:

```env
ANTHROPIC_API_KEY=your-anthropic-key-here
SPOTIFY_CLIENT_ID=your-spotify-client-id
SPOTIFY_CLIENT_SECRET=your-spotify-client-secret
```

⚠️ **No spaces around `=`**. That format matters.

### 5. Install backend dependencies

```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1   # PowerShell
pip install -r requirements.txt
```

### 6. Install frontend dependencies

```bash
cd ..\desktop
npm install
```

### 7. Do first-time OAuth for Google

From `backend/` (with venv activated):

```bash
python google_auth.py
```

A browser window will open. Log in with the Google account you added as a test user, approve access. A `token.json` will be saved. You're done.

Spotify OAuth happens automatically the first time you ask the cat to play a song.

---

## Running the app

You'll run two processes: the backend server and the Electron desktop app.

### Terminal 1 — Backend

```bash
cd backend
.\venv\Scripts\Activate.ps1
uvicorn main:app --port 8000
```

You should see `Uvicorn running on http://127.0.0.1:8000`.

### Terminal 2 — Frontend

```bash
cd desktop
npm start
```

Your cat will appear centered on your desktop.

---

## How to use it

1. **First launch** — you'll see an upload screen. Drop in a photo of your cat (real cats work best — the vision model rejects clearly non-cat images).
2. **Wait for cutout** — background removal and personality generation take a few seconds.
3. **Pick a voice** — male, female, or neutral. This drives the TTS.
4. **Click the cat** to open the command input.
5. **Type a command.** Some things to try:
   - *"what's on my calendar today?"*
   - *"draft an email to [name] about [topic]"*
   - *"summarize my last 5 emails"*
   - *"play some lofi"*
   - *"what's the weather?"*
   - *"what's in the news?"*
   - *"define serendipity"*
   - *"open notepad"*
   - *"start a 25 minute timer"*
   - *"what's on my screen?"* (asks the cat to look at your current screen)
6. **Try to be nice.** Insulting the cat produces different animations than complimenting it.
7. **Look at what it learned about you** — click the memory panel button (bottom left). Delete facts you don't like.
8. **Recall the cat** if it drifts off-screen — click the tray icon or right-click for the menu.
9. **When you're done** — right-click the tray → Quit. The cat persists; it'll be there next launch.

---

## Project structure

```
vcat/
├── backend/                    # Python + FastAPI backend
│   ├── main.py                 # FastAPI app, all HTTP endpoints
│   ├── agent.py                # Claude tool-use loop, personality + memory injection
│   ├── tools.py                # All tool implementations (calendar, email, spotify, etc.)
│   ├── app_finder.py           # Windows app allowlist/denylist launcher
│   ├── summaries.py            # Summary history tracking
│   ├── tts.py                  # Edge TTS with mood-aware modulation
│   ├── google_auth.py          # Google OAuth setup
│   ├── spotify_auth.py         # Spotify OAuth setup
│   ├── requirements.txt        # Python dependencies
│   ├── .env                    # API keys (gitignored)
│   ├── credentials.json        # Google OAuth credentials (gitignored)
│   ├── token.json              # Google OAuth token (gitignored, auto-generated)
│   └── ...
├── desktop/                    # Electron frontend
│   ├── main.js                 # Electron main process (window, tray)
│   ├── preload.js              # Preload script
│   ├── index.html              # UI (cat, bubble, panels)
│   ├── package.json            # Node dependencies + scripts
│   └── ...
├── documentation/
│   └── project_report.md       # Full technical report
└── README.md                   # This file
```

Persistent state gets created as you use the app:
- `backend/personality.json` — cat's generated personality
- `backend/memory.json` — durable facts learned about you
- `backend/summaries.json` — index of saved summaries
- `backend/voice.json` — chosen TTS voice
- `%LOCALAPPDATA%\vcat\summaries\*.txt` — saved summary files

---

## Troubleshooting

**Cat says "couldn't grab the news" or weather fails.**
Usually an SSL certificate issue. Update your certificate bundle: `pip install --upgrade certifi`.

**Google APIs stop working after about a week.**
Google's OAuth Testing-mode refresh tokens expire in 7 days. Re-authorize:
```bash
cd backend
.\venv\Scripts\Activate.ps1
python google_auth.py
```

**Spotify says "no active device."**
Open Spotify on your desktop and play + pause any track. That activates the device so the API can control it.

**Cat spawns off-screen or is stuck invisible.**
Click the tray icon (system tray, bottom right of your taskbar) → **Center cat**. This is a hard reset.

**Command returns "I don't see 'X' installed" for an app you have.**
The launcher only uses Windows' Start Menu app list (`Get-StartApps`). Apps installed to unusual locations or portable apps might not appear. You can verify by running `Get-StartApps` in PowerShell.

**Cat's calendar reply is missing events.**
Make sure all the calendars you care about are checked ("My calendars" AND "Other calendars") in Google Calendar's sidebar. The cat queries every calendar you have access to.

**Backend won't start with `ModuleNotFoundError`.**
Make sure the venv is activated (`.\venv\Scripts\Activate.ps1`) and dependencies are installed (`pip install -r requirements.txt`).

**"Something else is using port 8000."**
Kill it or start the backend on a different port. If you change the port, you'll need to update the frontend to match.

---

## Security

Cat Overlord was designed with the principle that an assistant with access to your data should never surprise you.

- **Draft-only email.** Emails are composed as Gmail drafts. Sending requires you to click Send yourself.
- **App launcher guardrails.** Only Windows Start Menu apps can be opened; a hardcoded denylist blocks system shells (`cmd`, `powershell`, `regedit`, etc.).
- **Summary file deletion is scoped.** The delete helper verifies the file is inside `%LOCALAPPDATA%\vcat\summaries` before removing it. Files outside are never touched.
- **Secrets are gitignored.** `.env`, `credentials.json`, and all token caches never enter version control.
- **Backend is localhost-only.** FastAPI binds to `127.0.0.1:8000`. No external exposure.
- **Screen analysis is opt-in.** Screenshots are only captured when you explicitly ask, and not persisted after analysis.
- **User owns memory.** Everything the cat has learned about you is inspectable and deletable through the memory panel.
- **Least-privilege OAuth scopes.** Google scopes are limited to Gmail read/compose (not send) and Calendar. Spotify scopes are limited to playback control.

For the full security design writeup, see [`documentation/project_report.md`](documentation/project_report.md).

---

## Known limitations

- **Windows-only.** No macOS or Linux support yet.
- **Google OAuth expires weekly** (Testing-mode refresh tokens).
- **Spotify requires Premium** for playback control (Spotify's restriction, not ours).
- **Single-monitor assumptions** in spawn/recall and screenshot capture.
- **Requires internet** for almost everything except the memory panel, timer, and system resource monitor.

---

## Acknowledgments

- **Anthropic** for Claude Sonnet 4.5 and Claude Vision
- **Google** for Gmail and Calendar APIs
- **Spotify** for the Web API
- **Open-Meteo**, **ip-api.com**, **BBC News**, and **Free Dictionary API** for free public data
- The organizers of **#hackthekitty 2026** for a theme that made building this genuinely fun

---

## Notes for evaluators

The full technical writeup, architecture diagram, testing matrix, security discussion, and reflections live in [`documentation/project_report.md`](documentation/project_report.md). This README is meant to get you running the project; the report is meant to explain what's under the hood.