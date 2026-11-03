# Usability Experiment

Usability experimnt is a local proof-of-concept for observing how people and AI browser agents use the same controlled bookstore. It compares Version A's selected usability friction with Version B's improvements and records browser behavior for T1 product discovery and T5 cart editing.

## What this mini-experiment tests

- T1: Find “Signal in the Dust” and add it to the cart. The task only succeeds after the final cart is verified.
- T5: Change the starting cart item's quantity from one to two and verify the updated subtotal.
- Version A and B share the same ordered product catalogue and actions. A real parity validator checks IDs, names, prices, authors, descriptions, ratings, stock, ordering, and actions; failed parity blocks session creation.
- Human demonstration sessions require an on-screen consent confirmation. AI sessions have separate actor metadata and are never registered as human participants.
- Five visible A-side seeded issues are currently implemented: S1, S3, S7, S8, and S10. Other items in the research draft are not claimed as implemented.

## Architecture

- `frontend/`: React/TypeScript bookstore, T1/T5 task flow, consent-gated manual run setup, event queue, results table and exports.
- `backend/`: FastAPI sessions, participant/consent records, shared catalogue and parity validation, idempotent event ingestion, task metrics and results API.
- `agent/`: Python Playwright/OpenAI Responses API runner, structured persona profiles, browser tool restrictions, verification, screenshots and reports.
- `docs/mini-experiment-protocol.md`: conditions, measures and interpretation guidance.

## Prerequisites

- Windows 11 with PowerShell.
- Python 3.12 or newer, Node.js 20.19+ or 22.12+, and npm.
- Docker Desktop only if using PostgreSQL. SQLite is the local default.
- An OpenAI API key only for AI-agent runs. Keep it in `agent/.env`; never place it in frontend variables.

## Install

Run these commands from the repository root in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m pip install -r agent\requirements.txt
python -m pip install pytest
python -m playwright install chromium
Set-Location frontend
npm install
Set-Location ..
```

The browser and frontend production checks are:

```powershell
Set-Location frontend
npm run lint
npm run build
Set-Location ..
```

## Start the application

SQLite is used unless `DATABASE_URL` is set. The default is the clean `backend/behaviourlens_demo.db`; any older `backend/behaviourlens.db` is left untouched. To use the included PostgreSQL service, start Docker Desktop and run:

```bash
docker compose up -d postgres
```

In PowerShell, point the backend to PostgreSQL before starting it:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/behaviourlens"
Set-Location backend
python -m uvicorn app.main:app --reload --port 8000
```

In a second terminal, start the bookstore:

```powershell
Set-Location frontend
npm run dev -- --host 127.0.0.1
```

Open `http://localhost:5173`. Select Version A or B and T1 or T5 before starting a manual run. Starting a recorded run requires the on-screen consent checkbox. Use fictional demonstration delivery details only. Successful task verification closes the session and refreshes the results table.

## Configure and run the AI agent

Copy the example file and edit `agent/.env` locally. The `.env` file is ignored by Git:

```powershell
Copy-Item agent\.env.example agent\.env
```

Set `OPENAI_API_KEY` and optionally `OPENAI_MODEL`, `APP_BASE_URL`, and `API_BASE_URL` in that file. Both URLs must resolve to localhost or 127.0.0.1. The agent blocks non-local browser requests, uses a fresh Chromium context per repetition, and verifies the final cart from rendered DOM state.

From the repository root:

```powershell
python -m agent.runner --version A --persona neutral_baseline --task T1 --repeat 1
python -m agent.runner --version B --persona low_patience --task T1 --repeat 2 --model gpt-4.1-mini
python -m agent.runner --version A --persona low_risk_tolerance --task T5 --repeat 1 --max-actions 25 --max-model-calls 10
```

Available personas: `neutral_baseline`, `low_digital_experience`, `low_patience`, `low_risk_tolerance`, and `high_experience`. Their structured parameters and strategy descriptions are in `agent/personas.py`. The task objective is unchanged across personas; the agent does not receive the seeded issue register or a prescribed click sequence.

## Results and reports

The frontend results section compares stored human and AI sessions and exports CSV/JSON. Detailed local AI run exports and screenshots are kept in the ignored `reports/` files and `reports/evidence/`. Aggregate-only, GitHub-visible snapshots are written to `reports/public/mini_experiment_summary.md`, `reports/public/mini_experiment_results.csv`, and `reports/public/mini_experiment_results.json`; they contain condition-level counts and averages, not session IDs, event payloads, timestamps, screenshots, or model transcripts. Reports label results preliminary and make no statistical-significance claim. No synthetic human observations are created.

The backend event API accepts batches of up to 500 events at `POST /api/sessions/{session_id}/events`; retries are idempotent per event ID and session. The browser queue persists pending events in local storage and retries when the connection returns. Payloads contain behavioral data only, not form values or direct identifiers.

## Tests

From the repository root in PowerShell:

```powershell
$env:PYTHONPATH = "$PWD\backend"
python -m pytest backend\tests agent\tests -q
```

The Playwright storefront smoke test uses running local services when available; otherwise pytest skips it. It does not create research sessions. Start backend and frontend as described above to execute it.

## Limitations

- This is a local demonstration, not a production participant platform or ethics-approved study deployment.
- T2–T4 are not completed mini-experiment tasks. Questionnaires, advanced analysis, and human validation of usability findings are not implemented.
- Deterministic seeded-issue outcomes are preliminary observable-evidence indicators and may abstain; they are not proof of frustration or a substitute for human coding.
- The local demonstration uses a small catalogue and no payment or real purchasing flow.
- AI execution requires a user-provided OpenAI key and network access to the OpenAI API. No key is required for manual sessions, unit tests, or the storefront.
```
