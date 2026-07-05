# API Reference

Base URL: `http://localhost:8000`

CORS is enabled for all origins. No authentication on HTTP routes.

## Health

### `GET /`

**Response:** `{ "status": "ok" }`

---

## Cat personality

### `GET /has_cat`

Returns whether a cat personality is stored.

**Response:** `{ "has_cat": true | false }`

### `POST /upload_cat`

Upload a cat image for validation and personality analysis.

**Request:** `multipart/form-data` with field `file`

**Success (200):** `{ "is_cat": true, "personality": "<string>" }`

**Rejection (400):** `{ "is_cat": false, "error": "<message>" }`

### `DELETE /cat`

Deletes personality and clears all memory facts.

**Response:** `{ "ok": true }`

### `GET /greeting`

Generates a launch greeting using personality and memory.

**Response:** `{ "greeting": "<string>" }`

---

## Memory

### `GET /memory`

**Response:** `{ "facts": ["...", ...] }`

### `DELETE /memory`

Clears all facts.

**Response:** `{ "facts": [] }`

### `DELETE /memory/{index}`

Deletes one fact by zero-based index.

**Response:** `{ "facts": [...] }`

---

## Commands

### `POST /command`

Run the AI agent on user text.

**Request body:**

```json
{ "text": "your command here" }
```

**Success response:**

```json
{
  "reply": "<string>",
  "mood": "<mood>",
  "tools_used": ["read_calendar", "..."]
}
```

**Moods:** `happy`, `confused`, `sleepy`, `listening`, `thinking`, `drafting_email`, `checking_calendar`, `idle`, `angry`

**Agent tools:** `read_calendar`, `read_emails`, `draft_email`, `set_reminder`, `play_song`

**Error fallback:**

```json
{
  "reply": "Something broke, human. Even cats have limits. 🐾",
  "mood": "confused",
  "tools_used": []
}
```
