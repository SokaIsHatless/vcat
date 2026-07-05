# vcat — Submission Package

This folder is a self-contained submission bundle for **vcat** (Cat Overlord). It does not replace or modify the main project at the repository root.

## Contents

```
Submission/
├── README.md                 ← You are here
├── documentation/            ← Reports, architecture, API, testing guides
└── src/                      ← Complete runnable copy of the application
    ├── backend/              ← FastAPI server + AI agent
    ├── desktop/              ← Electron desktop client
    └── .gitignore
```

## Quick start (run from `src/`)

### Prerequisites

- **Node.js** and **npm** (for the desktop client)
- **Python 3** with `pip` (for the backend)
- **Anthropic API key** in `src/backend/.env` as `ANTHROPIC_API_KEY=...`
- Optional: Google OAuth files (`credentials.json`, `token.json`) in `src/backend/` for calendar/email tools
- Optional: Spotify credentials for the `play_song` tool (see `src/backend/spotify_auth.py`)

### 1. Backend

```powershell
cd src/backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Desktop

```powershell
cd src/desktop
npm install
npm start
```

The desktop client connects to `http://localhost:8000`. Dependencies are already installable via the included `package-lock.json`.

## Documentation

| Document | Description |
|----------|-------------|
| [project-documentation.md](documentation/project-documentation.md) | Full project reference (features, stack, APIs, configuration) |
| [architecture-overview.md](documentation/architecture-overview.md) | System components and data flow |
| [api-reference.md](documentation/api-reference.md) | HTTP API endpoints |
| [setup-and-run-guide.md](documentation/setup-and-run-guide.md) | Detailed setup and runtime instructions |
| [testing-guide.md](documentation/testing-guide.md) | Manual testing procedures and scripts |

## Notes for reviewers

- Runtime secrets (` .env`, OAuth tokens, personality/memory JSON) are gitignored and are **not** included in this package.
- Cat cutout images are stored at runtime in Electron `userData`, not in the repository.
- The original project layout at the repository root is unchanged; this package is a copy for submission only.
