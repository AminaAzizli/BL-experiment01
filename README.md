# BehaviourLens

BehaviourLens is a research platform for comparing real human behaviour with AI browser-agent behaviour on a controlled bookstore. The project is being implemented in stages to match the specification.

## Stage plan

1. Foundation: repository configuration, backend, frontend shell, Docker, environment setup.
2. Bookstore: version A/B parity, product sets, task states, cart and delivery flow.
3. Human participant system: consent, sessions, task flow, questionnaires.
4. Event collection and validation.
5. AI browser-agent execution and logging.
6. Judge, baselines, and ground-truth validation.
7. Pilot, freeze, confirmatory analysis, and deployment hardening.

## Current status

The foundation, controlled bookstore shell, human participant API, and event collection API are implemented. The participant-facing consent/task UI and AI research pipeline remain future stages.

## Event collection

Events are submitted in batches to `POST /api/sessions/{session_id}/events`. Each event needs a stable client-generated `event_id`; retries with the same ID in a session are safely counted as duplicates. Batches are limited to 500 events. `GET /api/sessions/{session_id}/metrics` derives event counts, task duration, and completion status from stored events.

The frontend event queue helper at `frontend/src/lib/eventQueue.ts` persists pending events in browser storage and retries a session's batches when the caller can reach the API. Event payloads should contain study behavior only; do not include names, contact details, or other direct identifiers.

## Tech stack

- Python 3.12 + FastAPI
- React + TypeScript
- PostgreSQL via Docker Compose
- SQLAlchemy
- Vite for frontend dev server

## Local development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

### Docker

```bash
docker compose up -d postgres
```
