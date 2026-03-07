# CLAUDE.md — AI Assistant Guide for Grok3API

This document describes the codebase structure, development conventions, and workflows for AI assistants working on the **Grok3API** project.

---

## Project Overview

**Grok3API** is an unofficial Python library (v0.1.0rc2, MIT) that provides:
- A Python client (`GrokClient`) to interact with the Grok 3 AI model via browser automation
- An OpenAI-compatible REST API server (`python -m grok3api.server`)
- Advanced anti-detection browser fingerprinting to avoid bot detection

The library works by launching an undetected Chrome browser, automatically extracting session cookies, then making direct HTTP requests to Grok's REST API using those cookies.

**Upstream repo**: https://github.com/boykopovar/Grok3API
**PyPI**: `pip install grok3api`
**Python**: ≥3.8
**Author**: boykopovar

---

## Repository Structure

```
proyecto-grok-2026/
├── grok3api/                   # Main package
│   ├── __init__.py
│   ├── client.py               # GrokClient — primary entry point (709 lines)
│   ├── driver.py               # WebDriverSingleton — Chrome automation (728 lines)
│   ├── driver_pool.py          # DriverPool — thread-safe Chrome pool (128 lines)
│   ├── fingerprint.py          # FingerprintGenerator — anti-detection (485 lines)
│   ├── history.py              # History — chat history management (199 lines)
│   ├── logger.py               # Logging configuration
│   ├── server.py               # FastAPI OpenAI-compatible server (200 lines)
│   └── types/
│       ├── GrokResponse.py     # ModelResponse, GrokResponse data classes
│       └── GeneratedImage.py   # Image download and saving
├── tests/                      # Test suite (direct Python execution)
│   ├── example.py              # Async usage example
│   ├── test_funcional.py
│   ├── test_profesional.py
│   ├── test_stress_10.py
│   ├── openai_test.py
│   ├── ManyPictures.py
│   └── SimpleTgBot/            # Telegram bot integration example
├── docs/
│   ├── En/                     # English documentation
│   └── Ru/                     # Russian documentation (mirrors of En/)
├── scripts/
│   └── interactive_chat.py     # Terminal interactive chat demo
├── analysis/                   # Development notes (not shipped)
├── assets/                     # Sample generated images
├── pyproject.toml              # Package metadata and deps
├── .env.example                # All supported environment variables
├── Dockerfile                  # Python 3.11 + Chrome container
└── README.md
```

---

## Key Source Files

| File | Responsibility |
|------|---------------|
| `grok3api/client.py` | `GrokClient` class — handles `ask()` / `async_ask()`, cookie injection, history, HTTP request lifecycle |
| `grok3api/driver.py` | `WebDriverSingleton` — launches undetected Chrome, navigates to grok.com, extracts cookies and statsig ID |
| `grok3api/fingerprint.py` | `FingerprintGenerator` — generates JS scripts that spoof canvas, WebGL, AudioContext, WebRTC, navigator properties |
| `grok3api/driver_pool.py` | `DriverPool` — thread-safe queue of `WebDriverSingleton` instances for parallel requests |
| `grok3api/history.py` | `History` — in-memory + optional JSON-file chat history with `SenderType` enum |
| `grok3api/server.py` | FastAPI app with `/v1/chat/completions` (OpenAI format) and `/v1/string` endpoints |
| `grok3api/types/GrokResponse.py` | `GrokResponse` / `ModelResponse` dataclasses; transforms artifact blocks to markdown |
| `grok3api/types/GeneratedImage.py` | Downloads and saves Grok-generated images using session cookies |

---

## Architecture

### Request Flow

```
GrokClient.ask() / async_ask()
  └─► WebDriverSingleton.init_driver()   # launch Chrome if not already running
  └─► WebDriverSingleton.get_cookies()   # extract grok.com cookies
  └─► HTTP POST to grok.com REST API     # with cookies + JSON payload
  └─► Parse streaming response           # parse NDJSON lines
  └─► History.add_message()              # if history enabled
  └─► Return GrokResponse                # with message, images, responseId, etc.
```

### Key Patterns

- **Singleton**: `driver.web_driver` is a module-level `WebDriverSingleton` instance; `GrokClient.__init__` calls `init_driver()` which is idempotent.
- **Pool**: `DriverPool` maintains a `Queue` of `WebDriverSingleton` instances for concurrent use.
- **Dataclasses**: `GrokResponse`, `ModelResponse`, `GeneratedImage` are plain Python dataclasses.
- **Async**: `GrokClient.async_ask()` uses `asyncio.get_event_loop().run_in_executor()` to wrap the sync call.

### API Endpoints (server.py)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/chat/completions` | OpenAI-compatible chat completions |
| `GET`  | `/v1/string?q=...` | Plain-text query/response |
| `POST` | `/v1/string` | Plain-text query in body, response in body |

---

## Development Setup

### Prerequisites

- Python ≥ 3.8
- Google Chrome or Chromium installed
- On Linux: Xvfb for headless display (`USE_XVFB=True`)

### Install for Development

```bash
pip install -e .
# Optional: install server extras
pip install fastapi uvicorn pydantic aiofiles questionary rich
```

### Configuration

Copy `.env.example` to `.env` and adjust values:

```bash
cp .env.example .env
```

Key environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `TIMEOUT` | `360` | Browser operation timeout (seconds) |
| `DEF_PROXY` | _(empty)_ | SOCKS/HTTP proxy URL |
| `USE_XVFB` | `True` | Use Xvfb virtual display on Linux |
| `ANTI_DETECTION_LEVEL` | `full` | `basic` / `standard` / `full` |
| `FINGERPRINT_SEED` | _(random)_ | Seed for consistent fingerprints across sessions |
| `DRIVER_POOL_SIZE` | _(unset)_ | Number of parallel Chrome instances |
| `GROK_COOKIES` | _(empty)_ | Pre-set cookies (server only) |
| `GROK_TIMEOUT` | `120` | Server request timeout |
| `GROK_PROXY` | _(empty)_ | Server proxy |
| `GROK_SERVER_HOST` | `0.0.0.0` | Server bind host |
| `GROK_SERVER_PORT` | `8000` | Server bind port |

---

## Running the Server

```bash
python -m grok3api.server
# or with explicit args:
python -m grok3api.server --host 127.0.0.1 --port 9000
```

The server launches a `GrokClient` on startup and blocks until Chrome is ready.

---

## Running Tests

Tests are plain Python scripts — run them directly:

```bash
python tests/test_funcional.py
python tests/test_profesional.py
python tests/test_stress_10.py
python tests/openai_test.py
python tests/example.py     # async usage demo
```

There is no pytest configuration or test runner setup. Tests require a real network connection and Chrome.

---

## Code Conventions

### Style

- **No linter/formatter configured** (no black, flake8, mypy, pre-commit hooks). Follow the existing style in modified files.
- Type hints are used extensively in function signatures.
- Docstrings use `:param name:` Sphinx style in `client.py`; other files use minimal or no docstrings.
- Comments are mixed English/Spanish — match the language in the file being edited.

### Naming

- Classes: `PascalCase` (`GrokClient`, `WebDriverSingleton`, `DriverPool`)
- Methods/functions: `snake_case`
- Constants: `UPPER_SNAKE_CASE` (`NEW_CHAT_URL`, `TIMEOUT`, `MAX_TRIES`)
- Private attributes: single underscore prefix (`_statsig_id`, `_history`)

### Error Handling

- Errors are logged via `grok3api.logger.logger` (a standard Python `logging.Logger`)
- `GrokClient.ask()` retries up to `max_tries = 5` times on recoverable failures
- `GrokResponse.error` holds error strings instead of raising exceptions in normal flow
- Initialization errors (`__init__`) are re-raised after logging

### Async

- `async_ask()` is implemented via `run_in_executor` wrapping the sync `ask()` — not a native coroutine chain
- The FastAPI server uses `async def` handlers but delegates to `grok_client.async_ask()`
- Do not introduce new blocking calls in `async def` functions without wrapping them

---

## Important Constraints

1. **Chrome is required** — all requests go through browser automation; there is no direct API key-based access.
2. **Cookies expire** — the driver re-fetches cookies when they become stale; avoid caching cookies externally.
3. **`conversation_id` and `response_id` must be paired** — passing one without the other raises `ValueError`.
4. **Streaming not supported** in the server (`/v1/chat/completions` returns 400 if `stream=True`).
5. **`always_new_conversation=True` (default)** — each `ask()` call starts a fresh Grok conversation. Set to `False` to continue an existing thread.
6. **History is disabled by default** (`history_msg_count=0`) — pass a positive integer to enable.

---

## Docker

Build and run:

```bash
docker build -t grok3api .
docker run -e USE_XVFB=True -p 8000:8000 grok3api
```

The Dockerfile uses Python 3.11 and pre-installs Chrome.

---

## File Patterns to Avoid Modifying

- `grok3api/fingerprint.py` — highly sensitive anti-detection JS; changes can break Cloudflare bypass
- `grok3api/driver.py` — Chrome initialization sequence is carefully tuned; test thoroughly after changes
- `.gitignore` entries: `cookies.txt`, `*.log`, `.env`, generated images are intentionally excluded

---

## Git Conventions

Commit style observed in history uses conventional commits:

```
feat(scope): short description
fix(scope): short description
```

Scopes used: `api`, `answer`, `docker`, `server`. Mixed English/Spanish commit bodies are acceptable.

Branch naming: `claude/<description>-<id>` for AI-assisted work.
