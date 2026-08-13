# AI BankSim

AI BankSim is an AI-assisted, scenario-based bank teller training platform.

It is intentionally a foundation, not a finished product. The current version provides:

- React + TypeScript + Vite frontend scaffold
- FastAPI backend scaffold
- SQLAlchemy models designed for SQLite now and PostgreSQL later
- Business rule engine skeleton
- Scoring service skeleton
- AI provider abstraction with local mock and server-side DeepSeek provider
- Five AI agent module skeletons
- Health, scenario, training, and AI evaluation endpoints
- End-to-end training completion with deterministic final score and ExaminerAgent explanation
- Completed-session locking and AI-provider fallback reporting
- Six teller scenarios with versioned deterministic rule policies and dynamic business inputs
- Authenticated history, stored final reports, and deterministic ability analysis
- Scenario-specific AI customers with persisted, bounded conversation memory
- Persisted personalized training plans with deterministic scenario ordering and PlannerAgent explanation
- Teacher workspace for student review, scenario editing, and immutable scenario-version history
- Docker Compose, GitHub Actions CI, and GitHub Pages frontend release workflow
- Handoff documentation for future agents

## Quick Start

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.db.seed_demo
pytest
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
pnpm install
pnpm dev
```

If your terminal cannot find `node`, install Node.js locally or add your Node binary to `PATH` before running `pnpm`.

Create `backend/.env` when using DeepSeek:

```bash
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_server_side_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

Do not put the DeepSeek key in frontend files.

## Docker

Copy the example environment values, then run:

```bash
docker compose up --build
```

Open `http://localhost:5173`. The backend API and Swagger UI are available at
`http://localhost:8000` and `http://localhost:8000/docs`.

## GitHub deployment

The repository contains two workflows:

- `CI` runs the backend test suite and production frontend build on pushes and pull requests.
- `Deploy frontend to GitHub Pages` publishes the static React application from `main`.

GitHub Pages cannot run FastAPI. For an online training system, deploy `backend/Dockerfile`
to a container host, store `DEEPSEEK_API_KEY` in that host's encrypted environment variables,
then create the GitHub repository variable `VITE_API_BASE_URL` with the public HTTPS API origin.
Never create a GitHub Actions variable whose name or value exposes the DeepSeek key.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the release checklist and limitations.

### Competition demo mode

The public GitHub Pages build sets `VITE_DEMO_MODE=true`. It opens directly in a
no-login competition experience and runs six scenarios, deterministic browser-side
rule checks, reproducible customer/coach/examiner responses, reports, history, and
planning without a hosted API. This is deliberately labelled as a demonstration;
real DeepSeek calls, persistence, authentication, and authoritative production rule
execution remain in the FastAPI backend and never expose server secrets to the browser.

Database schema changes are managed by Alembic. For a disposable development
database created by an older version, delete the ignored `backend/ai_banksim.sqlite3`
file and run `alembic upgrade head`. If an existing database contains data that
must be retained, back it up and verify it matches the initial schema before using
`alembic stamp 20260813_0001`; do not stamp an unknown production schema.

Demo login credentials after running `python -m app.db.seed_demo`:

- Student: `demo_student` / `Student123!`
- Teacher: `demo_teacher` / `Teacher123!`
- Admin: `demo_admin` / `Admin123!`

The optional `/api/dev/seed` endpoint is disabled by default. It is available only
when `ENABLE_DEV_SEED=true` and must remain disabled in production.

## Handoff

Read [docs/AGENT_HANDOFF.md](docs/AGENT_HANDOFF.md) before continuing development.
