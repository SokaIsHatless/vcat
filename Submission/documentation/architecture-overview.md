# Architecture Overview

## System summary

**vcat** is a desktop AI cat companion with two main parts:

1. **Electron desktop client** (`src/desktop/`) — floating, draggable, always-on-top window
2. **FastAPI backend** (`src/backend/`) — personality, memory, command handling, external tool integrations

Communication is HTTP-only at `http://localhost:8000`.

## Component diagram

```
┌─────────────────────────────────────────────────────────────┐
│  Electron Desktop (desktop/)                                │
│  ┌─────────────┐   IPC    ┌──────────────┐                  │
│  │ index.html  │◄────────►│ main.js      │                  │
│  │ cat-photo   │          │ preload.js   │                  │
│  │ .mjs        │          │ Tray / Menu  │                  │
│  └──────┬──────┘          └──────────────┘                  │
│         │ fetch http://localhost:8000                       │
└─────────┼───────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│  FastAPI Backend (backend/)                                 │
│  main.py ──► agent.py ──► Anthropic API (claude-sonnet-4-5) │
│                │                                            │
│                ├── tools.py ──► Google Gmail / Calendar     │
│                ├── tools.py ──► Spotify (play_song)         │
│                ├── personality.json (runtime)               │
│                └── memory.json (runtime)                    │
└─────────────────────────────────────────────────────────────┘
```

## Desktop architecture

| File | Role |
|------|------|
| `main.js` | Electron main process: window, IPC, cutout file I/O, system tray |
| `preload.js` | Exposes `window.catWindow` and `window.catStorage` to renderer |
| `index.html` | UI, CSS, speech bubble, memory panel, mood overlays, app logic |
| `cat-photo.mjs` | Upload flow, background removal, cat state module |

**Persistence:** Accepted cat cutouts are saved to Electron `userData/cat-cutout.png`. Launch restore requires both the local cutout and backend `GET /has_cat`.

**Tray:** System tray icon (`logo.png`) provides Center cat, Show/Hide, and Quit.

## Backend architecture

| File | Role |
|------|------|
| `main.py` | REST routes, personality upload, memory CRUD, greeting |
| `agent.py` | Anthropic tool-use loop, system prompt, mood parsing, memory reflection |
| `tools.py` | Google Calendar, Gmail, Spotify tool implementations |
| `google_auth.py` | Google OAuth installed-app flow |
| `spotify_auth.py` | Spotify OAuth for music playback tool |

**Persistence:** JSON files in `backend/` — `personality.json`, `memory.json` (created at runtime, gitignored).

## Data flow: command

1. User clicks cat → command panel opens
2. Desktop `POST /command` with `{ "text": "..." }`
3. Agent loads personality + memory into system prompt
4. Anthropic runs tool loop until final text reply
5. Response `{ reply, mood, tools_used }` drives speech bubble and animations
6. Agent may append new facts to memory (max 30)

## Data flow: cat upload

1. User selects image on upload overlay
2. Desktop `POST /upload_cat` — backend validates `is_cat` and stores personality
3. On acceptance only: in-browser background removal → save cutout to `userData`
4. On rejection: no cutout saved; upload overlay remains

## Data flow: launch greeting

1. Saved cat restored on launch (local cutout + `has_cat`)
2. Instant placeholder greeting in speech bubble
3. Background `GET /greeting` returns personalized greeting from memory
4. Bubble text updates when response arrives
