# Setup and Run Guide

This guide applies to the submission copy under `Submission/src/`.

## Environment variables

Create `src/backend/.env`:

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

Required for personality analysis, commands, greetings, and memory reflection.

## Google integration (optional)

For calendar and email tools:

1. Place `credentials.json` (OAuth client secrets) in `src/backend/`
2. Run any tool script once to complete OAuth; `token.json` is created automatically

Scopes used (`google_auth.py`):

- Gmail compose and read
- Google Calendar

## Spotify integration (optional)

For the `play_song` agent tool, configure credentials per `src/backend/spotify_auth.py`. Token file `spotify_token.json` is gitignored.

## Backend setup

```powershell
cd Submission/src/backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Verify: open `http://localhost:8000/` — expect `{ "status": "ok" }`.

## Desktop setup

```powershell
cd Submission/src/desktop
npm install
npm start
```

**Note:** Restart `npm start` after changes to `main.js` or `preload.js`. Use **Ctrl+R** in the cat window for `index.html` changes only.

## First-run flow

1. Start backend, then desktop
2. Upload a cat photo on the upload overlay
3. Backend validates the image; on success, background is removed and cutout is saved
4. Click the cat to send commands; use 🧠 for memory panel; tray icon for center/hide/quit

## Troubleshooting

| Issue | Check |
|-------|--------|
| "Can't reach my brain" | Backend running on port 8000 |
| Upload rejected | Image must contain a cat (`is_cat: false`) |
| No calendar/email tools | Google OAuth files and token |
| Cat not restored on launch | Both local cutout and `GET /has_cat` must be true |
| Tray Quit leaves process | Use tray **Quit**; app stays alive when cat is hidden |
