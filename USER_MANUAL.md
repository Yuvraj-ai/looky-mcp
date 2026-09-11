# Vision MCP — User Manual

Vision MCP is a self-hosted **Model Context Protocol (MCP) server for image understanding**. You configure vision model profiles (any OpenAI-compatible endpoint), write system prompts, and then connect coding agents like **OpenCode** to it. When the agent needs to "see" an image — a screenshot, a diagram, an error dialog — it calls one of the MCP tools here, which forwards the image to your configured vision model with your chosen system prompt.

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Logging In](#2-logging-in)
3. [System Prompts](#3-system-prompts)
4. [Vision Profiles](#4-vision-profiles)
5. [Universal Extra Instructions](#5-universal-extra-instructions)
6. [MCP Access (API Key)](#6-mcp-access-api-key)
7. [Connecting an Agent (OpenCode)](#7-connecting-an-agent-opencode)
8. [MCP Tools Reference](#8-mcp-tools-reference)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Node.js + npm (for the frontend)

### Start the backend

From the repository root:

```bash
uv run python run_backend.py --migrate
```

This runs `backend/scripts/dev.py`, which:

- starts a bundled PostgreSQL instance (no system Postgres needed; data lives in `backend/.pgdata/`)
- applies database migrations (with `--migrate`; needed on first run and after schema changes)
- launches the API + MCP server at **http://localhost:8000**

> First run ever? The migration step is required before the app will work.

### Start the frontend

```bash
cd frontend
npm install     # first time only
npm run dev
```

The web app is at **http://localhost:5173**.

### Create your first user account

There is **no public signup** — accounts are provisioned by an admin from the backend folder:

```bash
cd backend
uv run python scripts/create_user.py --email you@example.com --password 'your-password'
```

Then log in at http://localhost:5173 with that email and password.

---

## 2. Logging In

Open **http://localhost:5173**. If you aren't logged in, you're redirected to the login page.

- **Email + password** — use the credentials created via `create_user.py` (see above).
- **Sign in with Google** — shown if the server has Google OAuth credentials configured. The first Google sign-in only works if your account was pre-provisioned (with `--google-sub`) or already exists with the same verified email.

Sessions are cookie-based (30 days). Use **Logout** in the top bar to end the session on this browser.

---

## 3. System Prompts

**Nav: System Prompts**

A *system prompt* is the instruction persona your vision model uses when analyzing images (e.g. "You are a UI reviewer; describe layout issues concisely"). System prompts are reusable — you'll attach one to each vision profile.

- **Create** — click *New Prompt*, fill in a **Title** and the prompt **Content**, save.
- **Edit / Delete** — each prompt row has edit and delete buttons.
- **Deletion is blocked** if a prompt is referenced by a vision profile. Detach (or delete) the profile first.

> Tip: create your system prompts *before* creating vision profiles — profile creation requires selecting one.

### Universal Extra Instructions

On this page you'll also find the **Universal Extra Instructions** card: a single text block appended to *every* `describe_image` call regardless of profile. Use it for global preferences (e.g. "Always answer in English. Be terse."). It applies even when the active profile changes. (`ocr_image` calls don't use it — OCR answers stay literal.)

---

## 4. Vision Profiles

**Nav: Vision Profiles**

A *vision profile* binds a vision model to a system prompt. Fields:

| Field | Meaning |
|---|---|
| **Name** | Label for the profile (e.g. "GPT-4o fast") |
| **Endpoint / Base URL** | OpenAI-compatible base URL, e.g. `https://api.openai.com/v1` |
| **Model** | Vision model name, e.g. `gpt-4o` |
| **API Key** | Provider key. Encrypted at rest. On **edit**, leave blank to keep the current key |
| **System Prompt** | Which system prompt to use for calls made with this profile |

- **Create** — *New Profile* → fill fields → save. The API key is stored encrypted; it is never shown again after saving.
- **Activate** — exactly **one profile is active** at a time. Click *Activate* on a profile to make it the one all MCP tool calls use.
- **Edit / Delete** — as with prompts. You can delete the active profile, but tools won't work until you activate another one.

The profiles list shows whether a stored key exists (`has key`) and which profile is active.

---

## 5. Universal Extra Instructions

(Described in [Section 3](#universal-extra-instructions) — the card lives on the System Prompts page.)

---

## 6. MCP Access (API Key)

**Nav: MCP Access**

MCP tool calls are authenticated with a personal **API key** (format `vmcp-...`).

- **Generate key** — creates a key and shows it **exactly once**. Copy it immediately; only a hash is stored server-side, so it cannot be recovered later.
- **Revoke** — immediately invalidates the current key. Any agent still using it gets `401`. Generate a new key afterwards to restore access.
- Generating a new key while one exists **replaces** it (one active key per user).

The page also shows a ready-to-copy **OpenCode config snippet** (see next section).

---

## 7. Connecting an Agent (OpenCode)

On the **MCP Access** page:

1. Click **Generate** and copy the key.
2. Export it in your shell environment:

   ```bash
   export VISION_MCP_KEY="vmcp-...your-key..."
   ```

3. Copy the **OpenCode snippet** from the page and paste it into your `opencode.json` config file. It looks like:

   ```json
   {
     "mcp": {
       "vision": {
         "type": "http",
         "url": "http://localhost:8000/mcp",
         "headers": { "Authorization": "Bearer {env:VISION_MCP_KEY}" }
       }
     }
   }
   ```

   The key is referenced via `{env:VISION_MCP_KEY}` so it never gets pasted into a config file.

4. Restart OpenCode. The `vision` MCP server's tools (`describe_image`, `ocr_image`) are now available.

For other MCP-capable clients: the server endpoint is `http://<host>:8000/mcp` (Streamable HTTP), with header `Authorization: Bearer vmcp-...`.

---

## 8. MCP Tools Reference

Both tools use your **active vision profile** (endpoint, model, API key, system prompt). `describe_image` additionally appends the Universal Extra Instructions; `ocr_image` does not.

| Tool | What it does | When the agent should use it |
|---|---|---|
| `describe_image` | Analyze/describe the contents of an image | General visual understanding, screenshots, diagrams, UI review |
| `ocr_image` | Extract literal text from an image via OCR | Error messages, code screenshots, document text |

Images up to **5 MB** are accepted. The tool returns the model's answer as text.

---

## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| Login fails with no account existing | Accounts are admin-provisioned only: `uv run python scripts/create_user.py --email ... --password ...` |
| Tool call returns `401` from agent | Key revoked or replaced — generate a new key on MCP Access and re-export `VISION_MCP_KEY` |
| Tool call errors with "no active profile" | Activate a profile on the Vision Profiles page |
| Vision call fails (provider error) | Check the profile's endpoint URL and API key; edit the profile and re-enter the key |
| Backend won't start | Ensure you ran `--migrate` on first start; delete `backend/.pgdata` only if you accept losing all data |
| Frontend can't reach API | Backend must run on port 8000 (CORS allows only `http://localhost:5173` by default) |
| Lost API key | Cannot be recovered — revoke and generate a new one |

### Useful commands

```bash
# from repo root
uv run python run_backend.py --migrate   # start backend (with migrations)

# from backend/
uv run python scripts/create_user.py --email a@b.c --password 'secret'
uv run pytest                            # run test suite
curl http://localhost:8000/api/health    # backend health check
```
