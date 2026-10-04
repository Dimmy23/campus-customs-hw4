# HW4 — Campus Customs Shop & Chatbot

Campus Customs is a React/Vite/TypeScript storefront backed by FastAPI, SQLite catalogue tools, authentication, customer memory, and a PydanticAI shopping assistant.

## Repository and local data pack

The public repository contains code, prompts, documentation, and an `.env.example`. It intentionally does not contain secrets, the SQLite database, or product images. After cloning, place the private local data pack here:

```text
HW4/data/campus_customs.db
HW4/data/products/*.jpg
```

The database must include the `catalogue`, `inventory`, `users`, and `chat_messages` tables described in [`output/harness.md`](output/harness.md). Copy `.env.example` to `.env` and add a local `PORTKEY_API_KEY` if live model calls are desired.

Do not commit `.env`, `data/campus_customs.db`, or `data/products/`; `.gitignore` excludes them.

## Run the backend

From `HW4/backend`:

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r ../requirements.txt
uvicorn main:app --reload --port 8000
```

## Run the frontend

In a second terminal, from `HW4/frontend`:

```bash
npm install
npm run dev
```

Open the Vite URL shown in the terminal, usually `http://localhost:5173`.

The frontend expects the backend at `http://127.0.0.1:8000`. The API serves catalogue images from the local data pack and exposes `/api/products`, `/api/chat`, and the authentication routes.

## Problem 1 — Vibe Coder Prompts

Prompt history and reusable AI instructions for building the Campus Customs shop and chatbot are stored in [`AI_prompts.md`](AI_prompts.md).

## Problem 2 — Analyze the Database

The database analysis is in [`output/harness.md`](output/harness.md).

Work for this problem will be added here as a single numbered section when the requirements are provided.

## Problem 3 — Build the Campus Customs Website

The React + Vite + TypeScript frontend is in [`frontend/`](frontend/), with the catalogue API in [`backend/main.py`](backend/main.py). See [`problem_3_build_campus_customs_website.md`](problem_3_build_campus_customs_website.md) for run commands and implementation notes.

Problem 9 usability decisions and verification notes are in [`output/usability.md`](output/usability.md).

## Provided data

- `data/campus_customs.db` — catalogue, inventory, users, and chat-message tables.
- `data/products/` — product images used by the shop.
