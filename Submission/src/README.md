# vcat source (submission copy)

Runnable copy of the vcat application. See [../README.md](../README.md) for the full submission package overview.

## Run the backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Create backend/.env with ANTHROPIC_API_KEY=your_key
uvicorn main:app --reload --port 8000
```

## Run the desktop

```powershell
cd desktop
npm install
npm start
```

## Layout

- `backend/` — FastAPI API, Anthropic agent, Google/Spotify integrations
- `desktop/` — Electron transparent floating cat UI

Both parts communicate over HTTP at `http://localhost:8000`.
