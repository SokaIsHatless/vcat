# vcat — Cat Overlord

A floating desktop cat (Electron) powered by a FastAPI backend and Claude. Upload your cat, pick a voice, and command your sarcastic overlord. It can read email and calendar, draft messages, play Spotify, summarize to files, run Pomodoro timers, check your PC, analyze your screen, and more.

The desktop UI title is **Cat Overlord**. The backend runs at `http://localhost:8000`.

---

## Features

1) Floating transparent Electron desktop cat (always-on-top, draggable)

2) Cat photo upload with drag-and-drop or file picker

3) In-browser background removal for the cat photo (`@imgly/background-removal`)

4) Local cutout image saved and restored on launch

5) Cat personality generated from photo via Claude vision

6) Voice picker after upload (male / female / neutral → Edge TTS voices)

7) Edge TTS speech for cat replies (mood-aware rate, pitch, volume)

8) Random cat sounds prepended to spoken replies (~17.5%, with filters for serious/apologetic lines)

9) Mute/unmute voice toggle (persisted in browser localStorage)

10) Click cat to open command input panel

11) Text commands sent to backend AI agent (`POST /command`)

12) Speech bubble for user text, thinking state, and replies

13) Speech bubble synced with TTS playback (stays visible while the cat is speaking)

14) Hover speech bubble to keep it visible while reading (2.5s hide after mouse leaves)

15) Mood-based cat animations (happy, listening, thinking, confused, sleepy, angry, idle, etc.)

16) Mood overlays — music 🎵, calendar 📅, email ✉️, timer ⏳, fire 🔥 (high RAM/CPU), eyes 👀 (screenshot)

17) Launch greeting when the cat returns (`GET /greeting`)

18) Google Calendar read (`read_calendar`)

19) Gmail read/search (`read_emails`, optional full body, configurable count)

20) Gmail draft creation — never sends (`draft_email`)

21) Google Calendar reminders (`set_reminder`)

22) Spotify song search and playback (`play_song`)

23) Long summaries saved to Desktop `.txt` files (`save_summary`)

24) Summaries panel — list saved summaries, open in default editor, remove from registry

25) Pomodoro/focus timer with live countdown UI (`start_timer`)

26) Timer break announcement with TTS when complete (`POST /speak`)

27) CPU/RAM monitoring with fire overlay when usage is critical (`check_system_resources`)

28) Screenshot capture and AI screen analysis (`capture_screenshot`)

29) English word definitions via Free Dictionary API (`define_word`)

30) Open Windows apps by fuzzy name search (`open_application`)

31) Weather lookup by IP geolocation + Open-Meteo (`get_weather`)

32) BBC World News headlines via RSS (`get_news`)

33) Persistent user memory facts (`memory.json`) with post-command reflection (max 30 facts)

34) Memory panel — view facts, delete one, forget all

35) Session chat history panel (last 10 exchanges this session, frontend only)

36) Delete cat with confirmation dialog + optional “Also delete saved summaries”

37) System tray — show/hide cat, center cat, quit

38) Dynamic window resizing as panels and speech bubble grow

39) Multi-step autonomous agent tasks (e.g. check calendar → read email → draft)

40) Anthropic Claude Sonnet 4.5 as the agent brain

---

## Prerequisites

- **Node.js** (for the Electron desktop)
- **Python 3.10+** (for the backend)
- **Windows** recommended (screenshot capture, app launcher, Desktop summary paths are Windows-oriented)
- An **Anthropic API key** (required)

Optional, for specific tools:

- **Google Cloud OAuth** credentials (Gmail + Calendar tools)
- **Spotify Developer** app credentials (music playback; requires Spotify Premium + an active device)

---

## API keys & credentials

Create a file `backend/.env` (never commit it — it is gitignored):

```env
ANTHROPIC_API_KEY=sk-ant-...
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
```

### Required: Anthropic API key

Used for personality analysis, the command agent, memory reflection, launch greetings, and screenshot vision.

1. Go to [https://console.anthropic.com/](https://console.anthropic.com/)
2. Sign up or log in
3. Open **API Keys** and create a key
4. Add it to `backend/.env` as `ANTHROPIC_API_KEY`

Without this key the backend will fail on upload and commands.

### Optional: Google (Gmail + Calendar)

Used when the cat reads email, drafts email, reads calendar, or sets reminders.

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or pick an existing one)
3. Enable **Gmail API** and **Google Calendar API**
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**
5. Choose **Desktop app**
6. Download the JSON and save it as `backend/credentials.json`
7. The first time a Google tool runs, a browser window opens on `http://127.0.0.1:8080` for consent
8. Tokens are saved to `backend/token.json` (gitignored)

Run manually to authorize early:

```bash
cd backend
python google_auth.py
```

### Optional: Spotify

Used only for `play_song`. Requires **Spotify Premium** and an **active Spotify device** (open Spotify and start playing something first).

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create an app
3. Copy **Client ID** and **Client Secret** into `backend/.env`
4. In the app settings, add redirect URI: `http://127.0.0.1:8888/callback`
5. The first time music is requested, the backend prints/opens an auth URL; paste the redirect URL when prompted
6. Token cache is saved to `backend/spotify_token.json` (gitignored)

Run manually to authorize early:

```bash
cd backend
python spotify_auth.py
```

### No API key needed

| Service | Used for |
|---------|----------|
| **Edge TTS** (`edge-tts`) | Cat voice — Microsoft Edge speech, no key |
| **Free Dictionary API** | `define_word` |
| **ip-api.com + Open-Meteo** | `get_weather` |
| **BBC World RSS** | `get_news` |

### Optional env override

| Variable | Purpose |
|----------|---------|
| `TTS_VOICE` | Override default Edge TTS voice ID (e.g. `en-US-AriaNeural`) if no voice category is saved |

---

## Installation

### 1. Clone the repo

```bash
git clone https://github.com/SokaIsHatless/vcat.git
cd vcat
```

### 2. Backend

```bash
cd backend
python -m venv venv
```

**Windows (PowerShell):**

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS / Linux:**

```bash
source venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env` with at least `ANTHROPIC_API_KEY` (see above).

### 3. Desktop

```bash
cd desktop
npm install
```

The first cat upload may download the background-removal ONNX model (one-time).

---

## Running

You need **two terminals** — backend first, then desktop.

### Terminal 1 — Backend

```bash
cd backend
# activate venv if not already active
uvicorn main:app --reload --port 8000
```

Verify: open [http://localhost:8000/](http://localhost:8000/) → `{"status":"ok"}`

### Terminal 2 — Desktop

```bash
cd desktop
npm start
```

### First-time flow

1. Upload a cat photo (drag-drop or click)
2. Wait for background removal and personality analysis
3. Pick a voice (male / female / neutral)
4. Click the cat to type a command

### After code changes

| Changed | Reload |
|---------|--------|
| `desktop/index.html` | **Ctrl+R** in the Electron window |
| `desktop/main.js` or `desktop/preload.js` | Restart `npm start` |
| `backend/*.py` | Auto-reloads if using `--reload`; otherwise restart uvicorn |

---

## Project structure

```
vcat/
├── backend/
│   ├── main.py           # FastAPI routes
│   ├── agent.py          # Claude agent, tools loop, memory reflection
│   ├── tools.py          # Gmail, Calendar, Spotify, weather, news, etc.
│   ├── tts.py            # Edge TTS generation
│   ├── summaries.py      # Summary registry for Summaries panel
│   ├── google_auth.py    # Google OAuth
│   ├── spotify_auth.py   # Spotify OAuth
│   ├── app_finder.py     # Windows app launcher
│   └── requirements.txt
└── desktop/
    ├── main.js           # Electron main process, tray, IPC
    ├── preload.js        # IPC bridge (window, storage, shell)
    ├── index.html        # UI, styles, client logic
    ├── cat-photo.mjs     # Upload + background removal
    └── package.json
```

### Runtime files (gitignored)

| File | Purpose |
|------|---------|
| `backend/personality.json` | Cat personality from photo upload |
| `backend/memory.json` | Remembered user facts |
| `backend/voice.json` | Selected TTS voice category |
| `backend/summaries.json` | Summary panel registry |
| `backend/runtime/audio/latest.mp3` | Latest TTS audio |
| `backend/credentials.json` | Google OAuth client secrets |
| `backend/token.json` | Google OAuth tokens |
| `backend/spotify_token.json` | Spotify token cache |
| `backend/.env` | API keys |
| Electron `userData/cat-cutout.png` | Saved cat cutout image |

---

## API reference

Base URL: `http://localhost:8000` (hardcoded in `desktop/index.html`).

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/` | Health check |
| `GET` | `/has_cat` | Whether personality exists |
| `POST` | `/upload_cat` | Upload cat image → personality |
| `DELETE` | `/cat` | Delete cat; `?wipe_summaries=true` also clears summaries |
| `POST` | `/command` | Run agent — body: `{ "text": "..." }` |
| `GET` | `/greeting` | Launch greeting text |
| `GET` | `/memory` | List memory facts |
| `DELETE` | `/memory` | Clear all facts |
| `DELETE` | `/memory/{index}` | Delete one fact |
| `GET` | `/summaries` | List saved summaries |
| `DELETE` | `/summaries/{index}` | Remove summary from registry |
| `GET` | `/voice` | Voice options + current selection |
| `POST` | `/voice` | Save voice — body: `{ "voice": "male" \| "female" \| "neutral" }` |
| `GET` | `/audio/latest` | Latest TTS MP3 |
| `POST` | `/speak` | TTS for fixed text — body: `{ "reply": "...", "mood": "happy" }` |

### Example command response

```json
{
  "reply": "Your calendar is clear, human.",
  "mood": "happy",
  "tools_used": ["read_calendar"],
  "audio_url": "http://localhost:8000/audio/latest",
  "timer": { "minutes": 25 },
  "system_alert": { "overlay": "fire" },
  "screenshot": { "analyzed": true, "focus": "general" }
}
```

Optional fields (`timer`, `system_alert`, `screenshot`, `audio_url`) appear only when relevant.

---

## Agent tools

| Tool | Description |
|------|-------------|
| `read_calendar` | Google Calendar events for a date |
| `read_emails` | Gmail search; optional full body |
| `draft_email` | Create Gmail draft (never sends) |
| `set_reminder` | Create Google Calendar event |
| `play_song` | Spotify search + play |
| `save_summary` | Write `.txt` summary to Desktop + register in panel |
| `start_timer` | Pomodoro timer (frontend runs countdown) |
| `check_system_resources` | CPU/RAM via psutil |
| `capture_screenshot` | Screen capture + Claude vision |
| `define_word` | Dictionary lookup |
| `open_application` | Fuzzy Windows app launcher |
| `get_weather` | Weather via IP location + Open-Meteo |
| `get_news` | BBC World headlines via RSS |

---

## Desktop controls

| Control | Action |
|---------|--------|
| Click cat | Open command panel |
| Drag cat | Move window |
| 💬 | Session chat history (this session only) |
| 📄 | Saved summaries panel |
| 🧠 | Memory panel |
| 🔊 / 🔇 | Toggle TTS |
| Delete cat | Reset personality, memory, voice; optional summary wipe |
| System tray | Show/hide, center, quit |
| **Escape** | Close open panel or speech bubble |

---

## Troubleshooting

**“Can't reach my brain right now, human. 🐾”**  
Backend is not running or not on port 8000. Start `uvicorn main:app --reload --port 8000`.

**Upload works but commands fail**  
Check `ANTHROPIC_API_KEY` in `backend/.env`.

**Google tools fail**  
Ensure `credentials.json` exists and run `python google_auth.py` once.

**Spotify fails**  
Premium required, active device required, and `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` in `.env`. Run `python spotify_auth.py` once.

**Memory panel empty but cat seems to remember**  
Memory is saved via a post-command reflection step into `memory.json` — it only persists durable facts and can return nothing for casual chat. The cat may also appear to “remember” from email/calendar data or your current message, not from saved memory.

**TTS silent**  
Check mute button. Restart Electron after `main.js` / `preload.js` changes.

**No voice on first launch**  
Complete the voice picker step after cat upload.

---

## License

ISC (`desktop/package.json`).
