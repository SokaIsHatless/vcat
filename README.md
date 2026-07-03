# vcat

## 1. Project Name

**vcat** — repository name from `https://github.com/SokaIsHatless/vcat.git`. The desktop UI title is **Cat Overlord** (`desktop/index.html`).

---

## 2. Introduction

vcat is a two-part application:

1. **Desktop client** (`desktop/`) — an Electron window that displays a floating, draggable cat on the desktop. The user uploads a cat photo, the client removes the background in-browser, and the cat responds to text commands via a speech bubble.
2. **Backend API** (`backend/`) — a FastAPI server that stores cat personality and memory, accepts commands, and runs an AI agent with Google Calendar and Gmail tools.

The desktop client communicates with the backend over HTTP at `http://localhost:8000`. The backend uses the Anthropic API (`claude-sonnet-4-5`) for personality analysis and command handling.

---

## 3. Problem Statement

> Not specified in the current codebase.

---

## 4. Project Goals

> Not specified in the current codebase.

---

## 5. Key Features

### Desktop (`desktop/`)

- Transparent, frameless, always-on-top Electron window (`desktop/main.js`)
- Cat photo upload via drag-and-drop or file picker (`desktop/index.html`, `desktop/cat-photo.mjs`)
- In-browser background removal using `@imgly/background-removal` and `onnxruntime-web` (`desktop/cat-photo.mjs`)
- Cutout image persisted to Electron `userData` as `cat-cutout.png` (`desktop/main.js`)
- On launch, restore saved cat only when both local cutout and backend `GET /has_cat` confirm a cat exists (`desktop/index.html`)
- Click cat to open command input; Enter or Send submits a command (`desktop/index.html`)
- Speech bubble shows user text, thinking state, and backend reply (`desktop/index.html`)
- Mood-based CSS animations on the cat image (idle bob, thinking, happy, listening, working, confused, sleepy, angry) (`desktop/index.html`)
- Memory panel (🧠 button) to view, delete individual facts, or forget all memory (`desktop/index.html`)
- **Change cat** — re-open upload overlay (`desktop/index.html`)
- **Delete cat** — confirm, call `DELETE /cat`, delete local cutout, return to upload screen (`desktop/index.html`)
- Programmatic window drag and dynamic height resize via IPC (`desktop/main.js`, `desktop/preload.js`)
- Backend unreachable error message: `"Can't reach my brain right now, human. 🐾"` (`desktop/index.html`)

### Backend (`backend/`)

- Health check endpoint `GET /` (`backend/main.py`)
- Cat personality upload from image via `POST /upload_cat` using Anthropic vision (`backend/main.py`)
- Personality stored in `backend/personality.json` (`backend/main.py`, `backend/agent.py`)
- `GET /has_cat` — reports whether personality exists (`backend/main.py`)
- `DELETE /cat` — removes personality file and clears memory (`backend/main.py`)
- `POST /command` — runs AI agent and returns `{ reply, mood, tools_used }` (`backend/main.py`, `backend/agent.py`)
- Memory stored in `backend/memory.json` with CRUD via `/memory` endpoints (`backend/main.py`, `backend/agent.py`)
- Agent tools: `read_calendar`, `read_emails`, `draft_email`, `set_reminder` (`backend/agent.py`, `backend/tools.py`)
- Post-command memory reflection: extracts durable user facts (max 30) via Anthropic (`backend/agent.py`, `MAX_FACTS = 30`)
- Google OAuth for Gmail and Calendar access (`backend/google_auth.py`)

---

## 6. System Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Electron Desktop (desktop/)                                │
│  ┌─────────────┐   IPC    ┌──────────────┐                  │
│  │ index.html  │◄────────►│ main.js      │                  │
│  │ cat-photo   │          │ userData/    │                  │
│  │ .mjs        │          │ cat-cutout   │                  │
│  └──────┬──────┘          └──────────────┘                  │
│         │ fetch http://localhost:8000                       │
└─────────┼───────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│  FastAPI Backend (backend/)                                 │
│  main.py ──► agent.py ──► Anthropic API (claude-sonnet-4-5) │
│                │                                            │
│                ├── tools.py ──► Google Gmail / Calendar   │
│                ├── personality.json                         │
│                └── memory.json                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Architecture

### Frontend

- **Electron** desktop app in `desktop/`
- Plain HTML, CSS, and JavaScript (no React or bundler)
- `desktop/main.js` — main process: window creation, IPC handlers for cutout file I/O and window movement
- `desktop/preload.js` — exposes `window.catWindow` and `window.catStorage` via `contextBridge`
- `desktop/index.html` — UI, styles, and application logic
- `desktop/cat-photo.mjs` — ES module for upload, background removal, and `window.catPhoto` API

### Backend

- **FastAPI** application in `backend/main.py`
- **Agent** in `backend/agent.py` — Anthropic tool-use loop with system prompt and mood parsing
- **Tools** in `backend/tools.py` — Google API wrappers
- **Google auth** in `backend/google_auth.py` — OAuth installed-app flow

### Services

- FastAPI HTTP server (`backend/main.py`)
- Anthropic Messages API (`backend/main.py`, `backend/agent.py`)
- Google Calendar API v3 (`backend/tools.py`)
- Gmail API v1 (`backend/tools.py`)

### Database

> Not specified in the current codebase. Persistence uses JSON files and the local filesystem (see Storage).

### Storage

| Location | Purpose |
|----------|---------|
| `backend/personality.json` | Cat personality text (gitignored) |
| `backend/memory.json` | List of remembered user facts (gitignored) |
| `backend/credentials.json` | Google OAuth client secrets (gitignored) |
| `backend/token.json` | Google OAuth tokens (gitignored) |
| Electron `app.getPath('userData')/cat-cutout.png` | Saved cat cutout image (`desktop/main.js`) |

### APIs

- REST API defined in `backend/main.py` (see [APIs](#16-apis))
- Desktop calls `http://localhost:8000` (hardcoded in `desktop/index.html`, `desktop/cat-photo.mjs`)

### Background Workers

> Not specified in the current codebase.

### AI Components

- Model: `claude-sonnet-4-5` (`backend/agent.py`, `backend/main.py`)
- Agent loop with tool execution until `stop_reason != "tool_use"` (`backend/agent.py`)
- Personality prompt for image analysis on upload (`backend/main.py`)
- System prompt for sarcastic cat overlord behavior (`backend/agent.py`, `SYSTEM_PROMPT`)
- Memory reflection prompt after each command (`backend/agent.py`, `_reflect_and_save`)

### External Services

- Anthropic API
- Google Gmail API
- Google Calendar API

---

## 8. Technology Stack

### Frontend

- Electron `^42.5.0` (`desktop/package.json`)
- HTML / CSS / JavaScript
- `@imgly/background-removal` `^1.7.0`
- `onnxruntime-web` `^1.21.0`

### Backend

- Python
- FastAPI `0.138.1` (`backend/requirements.txt`)
- Uvicorn `0.49.0` (`backend/requirements.txt`)
- Pydantic `2.13.4`
- `python-dotenv` `1.2.2`
- `python-multipart` `0.0.32`

### AI

- `anthropic` `0.112.0`
- Model: `claude-sonnet-4-5`

### Google Integration

- `google-api-python-client` `2.198.0`
- `google-auth` `2.55.1`
- `google-auth-oauthlib` `1.4.0`

### DevOps / Cloud / Infrastructure

> Not specified in the current codebase.

---

## 9. Directory Structure

```
vcat/
├── .gitignore
├── HANDOFF.md                 # Empty file
├── backend/
│   ├── agent.py               # AI agent, tools loop, memory reflection
│   ├── CLAUDE.md              # Empty file
│   ├── google_auth.py         # Google OAuth credential loading
│   ├── main.py                # FastAPI routes and file I/O
│   ├── personality.json       # Generated at runtime (gitignored)
│   ├── requirements.txt       # Python dependencies
│   ├── test_apis.py           # Manual Google API smoke test
│   ├── test_tools.py          # Manual tools smoke test
│   └── tools.py               # Gmail and Calendar tool implementations
└── desktop/
    ├── cat-photo.mjs          # Photo upload and background removal
    ├── index.html             # UI, styles, and client logic
    ├── main.js                # Electron main process
    ├── package.json           # npm metadata and scripts
    ├── package-lock.json      # npm lockfile
    └── preload.js             # IPC bridge for renderer
```

---

## 10. Application Workflow

### Launch

1. Electron creates a transparent 320×300 window (`desktop/main.js`).
2. `initUploadUI()` calls `tryRestoreSavedCat()` (`desktop/index.html`).
3. `tryRestoreSavedCat()` checks:
   - Local cutout via `window.catStorage.hasSavedCutout()`
   - Backend via `GET http://localhost:8000/has_cat`
4. If local cutout exists but backend reports `has_cat: false`, the local cutout is deleted.
5. If backend is unreachable, local cutout is missing, or `has_cat` is false → upload overlay is shown.
6. If both exist → cutout is loaded, upload overlay is hidden, cat is marked ready.

### Cat upload

1. User drops or selects an image file.
2. `cat-photo.mjs` runs `removeBackground()` on the image.
3. Cutout PNG is saved to `userData/cat-cutout.png` via IPC.
4. Original image is posted to `POST /upload_cat`; backend analyzes it with Anthropic and writes `personality.json`.
5. If upload fails, local cutout is deleted and state is reset (`desktop/cat-photo.mjs`).
6. Upload overlay is hidden; cat becomes interactive.

### Command

1. User clicks the cat (without dragging past 5px threshold) → command panel opens, mood set to `listening`.
2. User submits text → `POST /command` with `{ "text": "..." }`.
3. While waiting: thinking animation and `"Thinking..."` dots in speech bubble.
4. On success: reply shown in bubble; mood applied from `data.mood` (`thinking` remapped to `happy` on reply).
5. On fetch failure: error bubble and `confused` mood.
6. Bubble auto-hides after `BUBBLE_HIDE_MS` (6000ms), scaled by reply length (max 15000ms).

### Memory

1. User opens memory panel → `GET /memory`.
2. Facts rendered with per-fact delete (`DELETE /memory/{index}`).
3. **Forget everything** confirms, then `DELETE /memory`.

### Delete cat

1. User confirms deletion.
2. `DELETE /cat` clears backend personality and memory.
3. Local cutout deleted; `catPhoto.reset()`; image reset to `cat.png`.
4. Upload overlay shown.

### Agent (backend)

1. `run_agent(user_text)` builds system prompt with personality, memory facts, and current IST datetime.
2. Anthropic API called with `TOOLS` definitions in a loop until no tool use.
3. Tool results appended to message history; tools executed via `_TOOL_FNS`.
4. Reply text parsed for optional `MOOD:` line; mood assigned from agent tag, tools used, or errors.
5. `_reflect_and_save()` may append new facts to `memory.json` (capped at 30).

---

## 11. Installation

### Desktop

From `desktop/package.json` and `desktop/package-lock.json`:

```bash
cd desktop
npm install
```

### Backend

From `backend/requirements.txt`:

```bash
cd backend
pip install -r requirements.txt
```

### Google OAuth (backend tools)

`backend/google_auth.py` expects:

- `credentials.json` — OAuth client secrets file in the backend working directory
- `token.json` — created on first successful OAuth flow

Both files are listed in `.gitignore`.

### Environment file

`.gitignore` references `.env` files. `backend/main.py` and `backend/agent.py` call `load_dotenv()` from `python-dotenv`.

---

## 12. Configuration

| File | Purpose |
|------|---------|
| `desktop/package.json` | npm package name `desktop`, `start` script, dependencies |
| `desktop/main.js` | Window dimensions (`WINDOW_WIDTH=320`, `WINDOW_MIN_HEIGHT=300`, `WINDOW_MAX_HEIGHT=720`), cutout filename `cat-cutout.png` |
| `backend/requirements.txt` | Pinned Python dependencies |
| `.gitignore` | Ignores secrets, `node_modules`, `venv`, `personality.json`, `memory.json` |
| `backend/personality.json` | Runtime personality storage (not committed) |
| `backend/memory.json` | Runtime memory storage (not committed) |
| `backend/credentials.json` | Google OAuth client config (not committed) |
| `backend/token.json` | Google OAuth tokens (not committed) |

No YAML, TOML, Docker, or CI configuration files are present in the repository.

---

## 13. Running the Project

### Desktop

From `desktop/package.json`:

```bash
cd desktop
npm start
```

This runs `electron .` (entry point `main.js`).

### Backend

> Not specified in the current codebase.

`backend/requirements.txt` includes `uvicorn`. `backend/main.py` defines `app = FastAPI()`. No Makefile, Docker file, or npm script starts the backend server.

### Manual test scripts

These are standalone Python scripts, not part of an automated test runner:

```bash
cd backend
python test_tools.py
python test_apis.py
```

`backend/agent.py` also includes a `if __name__ == "__main__"` block with sample `run_agent()` calls.

---

## 14. Environment Variables

| Name | Purpose | Required |
|------|---------|----------|
| `ANTHROPIC_API_KEY` | API key for `anthropic.Anthropic(api_key=...)` in `backend/main.py` and `backend/agent.py` | Required — accessed via `os.environ["ANTHROPIC_API_KEY"]` (raises `KeyError` if unset) |

No other environment variables are referenced in application source code. Google credentials are loaded from `credentials.json` and `token.json` files, not environment variables.

---

## 15. Database

> Not specified in the current codebase.

The backend uses JSON files:

- `backend/personality.json` — `{ "personality": "<string>" }`
- `backend/memory.json` — `{ "facts": ["...", ...] }`

No ORM, migrations, or seed data are present.

---

## 16. APIs

Base URL used by the desktop client: `http://localhost:8000`.

CORS is enabled for all origins (`allow_origins=["*"]` in `backend/main.py`).

No authentication is implemented on API routes.

### `GET /`

| | |
|---|---|
| **Purpose** | Health check |
| **Response** | `{ "status": "ok" }` |

### `GET /has_cat`

| | |
|---|---|
| **Purpose** | Check whether cat personality exists |
| **Response** | `{ "has_cat": true \| false }` — `true` if `personality.json` exists and contains a non-empty `personality` field |

### `POST /upload_cat`

| | |
|---|---|
| **Purpose** | Upload cat image; analyze personality with Anthropic vision |
| **Request** | `multipart/form-data` with file field `file` (`UploadFile`) |
| **Response** | `{ "personality": "<string>" }` |
| **Side effect** | Writes `backend/personality.json` |

### `DELETE /cat`

| | |
|---|---|
| **Purpose** | Delete cat personality and clear memory |
| **Response** | `{ "ok": true }` |
| **Side effect** | Removes `personality.json` if present; sets memory facts to `[]` |

### `GET /memory`

| | |
|---|---|
| **Purpose** | List remembered facts |
| **Response** | `{ "facts": ["...", ...] }` |

### `DELETE /memory`

| | |
|---|---|
| **Purpose** | Clear all memory facts |
| **Response** | `{ "facts": [] }` |

### `DELETE /memory/{index}`

| | |
|---|---|
| **Purpose** | Delete one fact by zero-based index |
| **Path parameter** | `index` (integer) |
| **Response** | `{ "facts": [...] }` — updated list (no-op if index out of range) |

### `POST /command`

| | |
|---|---|
| **Purpose** | Run the AI agent on user text |
| **Request body** | `{ "text": "<string>" }` (`CommandRequest`) |
| **Response** | `{ "reply": "<string>", "mood": "<string>", "tools_used": ["<tool_name>", ...] }` |
| **Error response** | On exception: `{ "reply": "Something broke, human. Even cats have limits. 🐾", "mood": "confused", "tools_used": [] }` |

---

## 17. AI Components

### Models

- `claude-sonnet-4-5` — personality analysis (`backend/main.py`, `max_tokens=256`) and agent (`backend/agent.py`, `max_tokens=4096`)

### Agent

- `run_agent(user_text)` in `backend/agent.py`
- Tool-use loop: calls Anthropic with `tools=TOOLS` until `stop_reason != "tool_use"`
- System prompt defines cat overlord persona, style rules, and `MOOD:` output format

### Tools

| Tool | Function | Description |
|------|----------|-------------|
| `read_calendar` | `read_calendar(date?)` | List calendar events for a date (`YYYY-MM-DD`, default today) |
| `read_emails` | `read_emails(query?, max_results?)` | Gmail search (default `is:unread`, max 5) |
| `draft_email` | `draft_email(to, subject, body)` | Create Gmail draft (does not send) |
| `set_reminder` | `set_reminder(title, datetime_iso)` | Create Google Calendar event |

### Prompt templates

- Image personality analysis prompt in `POST /upload_cat` handler (`backend/main.py`)
- `SYSTEM_PROMPT` in `backend/agent.py`
- Memory reflection prompt in `_reflect_and_save()` (`backend/agent.py`)

### Memory

- Facts loaded from `memory.json` and injected into system prompt
- After each command, `_reflect_and_save()` asks the model for new durable facts as a JSON array
- Maximum 30 facts (`MAX_FACTS = 30` in `backend/agent.py`)
- Not RAG, embeddings, or vector database — plain string list in JSON

### Mood

Agent and frontend support moods: `happy`, `confused`, `sleepy`, `listening`, `thinking`, `drafting_email`, `checking_calendar`, `idle`, `angry`.

Agent may emit `MOOD: <mood>` as the final line of a reply; mood is also inferred from tools used and errors (`backend/agent.py`).

---

## 18. Integrations

| Service | Usage |
|---------|-------|
| **Anthropic** | Personality analysis and command agent (`anthropic` Python SDK) |
| **Google Gmail** | Read emails, create drafts (`backend/tools.py`) |
| **Google Calendar** | Read events, create reminder events (`backend/tools.py`) |

OAuth scopes in `backend/google_auth.py`:

- `https://www.googleapis.com/auth/gmail.compose`
- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/calendar`

---

## 19. Authentication & Authorization

### Backend HTTP API

> No authentication or authorization is implemented on FastAPI routes.

### Google APIs

- OAuth 2.0 installed-app flow via `google_auth_oauthlib.flow.InstalledAppFlow`
- Local server on `127.0.0.1:8080` with browser open (`backend/google_auth.py`)
- Tokens stored in `token.json`; refreshed when expired

### Electron

- `nodeIntegration: false`, `contextIsolation: true` (`desktop/main.js`)

---

## 20. Error Handling

### Backend

- `POST /command`: broad `except Exception` returns a fallback reply with `mood: "confused"` (`backend/main.py`)
- Agent tool execution: exceptions caught per tool; result string `"ERROR: {exc}"`; sets `had_error` (`backend/agent.py`)
- `_reflect_and_save()`: failures logged and swallowed (`backend/agent.py`)
- `GET /has_cat`: file/JSON errors return `{ "has_cat": false }` (`backend/main.py`)

### Desktop

- Command fetch failure: error bubble and `confused` mood (`desktop/index.html`)
- Cat photo processing failure: status message shown, upload overlay remains (`desktop/index.html`)
- Personality upload failure after cutout save: local cutout deleted (`desktop/cat-photo.mjs`)
- Delete cat: alert if backend delete fails (`desktop/index.html`)
- Memory operations: error text in memory panel (`desktop/index.html`)

---

## 21. Logging & Monitoring

### Backend

- `print()` statements for commands, replies, tool calls, personality storage, cat deletion, and memory updates (`backend/main.py`, `backend/agent.py`, `backend/tools.py` via agent)

### Desktop

- `console.log` / `console.warn` / `console.error` for mood changes, backend responses, and errors (`desktop/index.html`, `desktop/cat-photo.mjs`)

### Health check

- `GET /` returns `{ "status": "ok" }` (`backend/main.py`)

> No metrics, tracing, or external monitoring integrations are present.

---

## 22. Testing

### Frameworks

> No testing framework is configured.

`desktop/package.json` test script:

```json
"test": "echo \"Error: no test specified\" && exit 1"
```

### Manual scripts

- `backend/test_tools.py` — exercises `read_calendar`, `read_emails`, `draft_email`, `set_reminder`
- `backend/test_apis.py` — manual Calendar list and Gmail draft creation
- `backend/agent.py` `__main__` — sample `run_agent()` invocations

> No unit tests, integration tests, or end-to-end tests are present in the repository.

---

## 23. Deployment

> Not specified in the current codebase.

No Dockerfile, docker-compose, Kubernetes manifests, CI/CD pipelines, or cloud deployment configuration files are present.

---

## 24. Security

| Mechanism | Implementation |
|-----------|----------------|
| **CORS** | `allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]` (`backend/main.py`) |
| **Secret management** | `.gitignore` excludes `.env`, `credentials.json`, `token.json` |
| **Electron isolation** | `contextIsolation: true`, `nodeIntegration: false` (`desktop/main.js`) |
| **API authentication** | Not implemented on backend routes |
| **Email sending** | Agent system prompt and `draft_email` tool create drafts only; no send implementation |

> CSRF protection, rate limiting, and encryption beyond HTTPS/TLS defaults are not implemented in application code.

---

## 25. Performance

- Background removal model may download on first run (`desktop/cat-photo.mjs`: `"first run may download a model"`)
- Memory capped at 30 facts (`MAX_FACTS = 30` in `backend/agent.py`)
- Speech bubble hide duration scales with reply length, bounded 6000–15000ms (`desktop/index.html`)
- Window height resize uses `requestAnimationFrame` double-buffering (`desktop/index.html`)

> No caching layer, job queues, or database query optimization is present.

---

## 26. Future Improvements

From `backend/tools.py`:

```python
# Day boundaries are UTC midnight, so events near IST midnight may appear
# on the wrong day. Will fix with proper IST offset when needed.
```

```python
# If Calendar returns 400, try dropping "timeZone" or stripping the UTC
# offset from datetime_iso — the two fields can conflict.
```

> No other TODOs, FIXMEs, or roadmap items were found in the repository.

---

## 27. Known Limitations

- Calendar `read_calendar` uses UTC day boundaries; comment in `backend/tools.py` notes events near IST midnight may appear on the wrong day.
- Cat restore on launch requires both local cutout and reachable backend with `has_cat: true`; if the backend is unreachable, the upload screen is shown (`desktop/index.html`).
- `DELETE /cat` from the desktop requires a successful backend response before local cutout is removed (`desktop/index.html`).
- Agent creates Gmail drafts only; system prompt states emails are never sent (`backend/agent.py`).
- Memory limited to 30 facts (`backend/agent.py`).
- Backend API has no authentication; CORS allows all origins (`backend/main.py`).
- Desktop backend URL is hardcoded to `http://localhost:8000`.

---

## 28. Troubleshooting

> No troubleshooting information is available.

---

## 29. Contributing

> No contribution guidelines are included in the repository.

---

## 30. License

`desktop/package.json` specifies `"license": "ISC"`.

> No license file was found at the repository root.

---

## 31. Contact

> No contact information is provided.

---

## Electron IPC Reference

Exposed via `desktop/preload.js`:

### `window.catWindow`

| Method | IPC channel | Purpose |
|--------|-------------|---------|
| `moveBy(dx, dy)` | `window-move-by` | Move window by pixel offset |
| `setHeight(height)` | `window-set-height` | Resize window height (clamped 300–720), anchor bottom |

### `window.catStorage`

| Method | IPC channel | Purpose |
|--------|-------------|---------|
| `hasSavedCutout()` | `cat-has-saved-cutout` | Check if `cat-cutout.png` exists in userData |
| `saveCutout(arrayBuffer)` | `cat-save-cutout` | Write PNG to userData; returns `file://` URL |
| `getCutoutUrl()` | `cat-get-cutout-url` | Return `file://` URL or `null` |
| `deleteCutout()` | `cat-delete-cutout` | Delete saved cutout file |
