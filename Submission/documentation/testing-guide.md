# Testing Guide

Manual testing procedures for the submission copy. No automated test suite is configured (`npm test` exits with error by design).

## Prerequisites

- Backend running on `:8000` with valid `ANTHROPIC_API_KEY`
- Desktop running via `npm start` in `src/desktop/`

## Core flows

### Cat upload

| Step | Action | Expected |
|------|--------|----------|
| 1 | Upload non-cat image | Error message; no cutout saved; upload overlay stays |
| 2 | Upload real cat | Cutout appears; overlay hides; cat is interactive |
| 3 | Quit and reopen app | Same cat restored without upload prompt |

### Cat delete

| Step | Action | Expected |
|------|--------|----------|
| 1 | Click **Delete cat** → confirm | Upload overlay returns |
| 2 | Quit and reopen | Upload overlay shown again |

### Commands

| Step | Action | Expected |
|------|--------|----------|
| 1 | Click cat (no drag) | Command panel opens |
| 2 | Submit text | Thinking animation → reply in speech bubble |
| 3 | Backend down | Error bubble: "Can't reach my brain right now, human. 🐾" |

### Memory panel

| Step | Action | Expected |
|------|--------|----------|
| 1 | Click 🧠 | Panel lists facts from `GET /memory` |
| 2 | Delete one fact | List updates via `DELETE /memory/{index}` |
| 3 | Forget everything | All facts cleared |

### Launch greeting

| Step | Action | Expected |
|------|--------|----------|
| 1 | Ensure memory has facts (e.g. name) | — |
| 2 | Restart app with saved cat | Placeholder greeting immediately |
| 3 | Wait ~2s | Personalized greeting replaces placeholder |

### System tray

| Step | Action | Expected |
|------|--------|----------|
| 1 | Left-click tray icon | Cat centers on screen |
| 2 | Hide cat | Window hidden; app still running |
| 3 | Show cat | Window visible again |
| 4 | Quit | App fully exits |

### Mood overlays

Trigger via commands that return moods or use tools:

- `happy` — floating hearts
- `checking_calendar` — calendar icon
- `drafting_email` — envelope icon
- `play_song` in `tools_used` — music notes (independent of mood)

## Backend manual scripts

From `src/backend/` with venv activated:

```powershell
python test_tools.py
python test_apis.py
```

These exercise Google tools directly (require OAuth). They are smoke tests, not CI tests.

## Agent smoke test

```powershell
cd src/backend
python agent.py
```

Runs sample prompts against `run_agent()` when executed as `__main__`.
