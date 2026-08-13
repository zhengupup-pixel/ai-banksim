# AI BankSim Agent Handoff

## 1. Product Goal

AI BankSim is an AI-driven, adaptive, scenario-based bank teller training platform for university practical training, coursework, and innovation/software competitions.

The core direction must remain:

- Bank teller training
- Multi-agent AI
- Deterministic business rule engine
- Intelligent scoring
- Personalized training loop

Do not turn it into a generic chatbot, CRM, ERP, or question-bank website.

## 2. Current Implementation

This repository now contains a runnable first training-loop vertical slice.

Implemented now:

- FastAPI backend with health check and core training APIs
- SQLAlchemy database entities for the main domain
- SQLite development database with an executable Alembic initial migration
- BusinessRuleEngine for deterministic rule validation
- ScoringEngine that combines rule score and future AI score
- AIProvider abstraction
- MockProvider for local development
- DeepSeekProvider using server-side OpenAI-compatible chat completions
- Five agent skeletons: Customer, Coach, Examiner, Scenario, Planner
- AgentOrchestrator to route calls
- React + TypeScript + Vite frontend skeleton
- Simple first-screen training console
- Basic backend tests
- TrainingService for session lifecycle and persistence boundaries
- Final training submission with deterministic final score and session locking
- ExaminerAgent final report that cannot override rule-engine facts
- Frontend final-submit action and final report panel
- Six seeded bank scenarios with versioned deterministic rule policies
- Dynamic frontend scenario selection, business inputs, and ordered authorization actions
- Student history, ability analysis, customer role-play, and personalized plan loop
- Teacher workspace with student selection, scenario editing, and version audit history
- Docker Compose, GitHub Actions CI, and GitHub Pages frontend workflow

This is not feature-complete. It is intentionally structured so another agent can safely continue.

## 3. Architecture

```text
Browser
  -> React Frontend
  -> FastAPI Backend
      -> API Routes
      -> Training Service / Rule Engine / Scoring Engine
      -> AI Agent Orchestrator
          -> Customer Agent
          -> Coach Agent
          -> Examiner Agent
          -> Scenario Agent
          -> Planner Agent
      -> SQLAlchemy Models
      -> SQLite database in development
```

Important separation:

- BusinessRuleEngine decides business facts: legal flow, required steps, amount checks, risk flags, base score.
- AI agents explain, simulate customers, coach learners, generate drafts, and plan learning.
- DeepSeek must never be the sole source of truth for whether a business operation is valid.

## 4. Directory Map

```text
backend/
  app/
    api/routes.py              FastAPI route definitions
    agents/                    Five agent skeletons and orchestrator
    ai/providers.py            AIProvider, MockProvider, DeepSeekProvider
    core/config.py             Environment settings
    db/session.py              SQLAlchemy engine/session
    db/init_db.py              Explicit opt-in development table creation
    models/entities.py         Domain database models
    schemas/training.py        Pydantic request/response models
    services/training.py       Training session lifecycle and persistence
    services/rule_engine.py    Deterministic business validation
    services/scoring.py        Score calculation
    main.py                    FastAPI application
  tests/test_api.py            Basic API tests
  requirements.txt             Python dependencies
  alembic.ini                  Alembic configuration
  alembic/env.py               Migration runtime and metadata wiring
  alembic/versions/            Ordered database revisions

frontend/
  src/
    api/client.ts              Browser API wrapper
    components/Metric.tsx      Small UI component
    pages/App.tsx              Training console screen
    pages/TeacherDashboard.tsx Teacher review and scenario-management workspace
    types/training.ts          Frontend domain types
    main.tsx                   React entrypoint
    styles.css                 Tailwind base styles
  package.json                 Frontend scripts and dependencies
```

## 5. Database Entities

Current SQLAlchemy entities:

- User
- Customer
- CustomerMemory
- Scenario
- TrainingSession
- TrainingAction
- Conversation
- Score
- AIEvaluation
- TrainingPlan
- Recommendation
- ScenarioVersion

Design notes:

- JSON columns are used for flexible scenario policy, session context, score details, and generated AI results.
- This is acceptable for early SQLite development.
- When moving to PostgreSQL, keep JSON payloads but add stricter relational tables for high-value analytics fields.
- Initial revision `20260813_0001` creates all current domain tables and indexes.
- Revision `20260813_0002` adds the versioned `Scenario.rule_policy` JSON column.
- Revision `20260813_0004` adds scenario-specific customer profiles; internal notes remain server-only.
- Revision `20260813_0005` links each Recommendation to the TrainingPlan version that produced it.
- Revision `20260813_0006` adds immutable snapshots of teacher/admin scenario changes.
- Application startup no longer calls `create_all` by default; run `alembic upgrade head` before starting the backend.
- `AUTO_CREATE_TABLES=true` is available only as an explicit temporary local-development escape hatch.

## 6. API Surface

Base prefix: `/api`

Endpoints:

- `GET /health`
  - Returns service health.

- `POST /dev/seed`
  - Creates three demo role accounts and six demo scenarios.
  - Disabled by default; available only with `ENABLE_DEV_SEED=true` for local/test workflows.

- `POST /auth/login`
  - Accepts username/password and returns a short-lived opaque bearer token.

- `GET /auth/me`
  - Returns the authenticated user and server-authoritative role.

- `POST /auth/logout`
  - Revokes the current bearer token and returns HTTP `204`.

- `GET /scenarios`
  - Lists six available training scenarios and their validated rule policies/input definitions.

- `PUT /scenarios/{scenario_id}`
  - Teacher/admin only. Validates and updates a scenario and its rule policy.

- `GET /scenarios/{scenario_id}/versions`
  - Teacher/admin only. Returns newest-first snapshots of prior scenario states.

- `GET /students`
  - Teacher/admin only. Lists active student identities for review selection.

- `GET /admin/users`
  - Admin only. Lists user identities and roles without password or token hashes.

- `GET /training-sessions`
  - Student: returns own active/completed history.
  - Teacher/admin: requires `user_id` and returns that student's history.

- `GET /training-sessions/{session_id}/report`
  - Reconstructs a completed report from persisted final score and Examiner evaluation.
  - Students may read only their own report; teacher/admin may review student reports.

- `GET /ability-analysis`
  - Deterministically aggregates average score, pass rate, per-business ability, repeated weaknesses, and recommended retraining types.

- `GET /training-sessions/{session_id}/conversations`
  - Returns persisted learner/customer conversation history to the owner or teacher/admin reviewer.

- `POST /training-sessions/{session_id}/customer-messages`
  - Student/owner only and active sessions only.
  - Persists the learner message, calls CustomerAgent with bounded recent history, and persists the customer response.
  - AI-provider failure returns the scenario opening line as a safe fallback without affecting training state or score.

- `POST /training-plans/generate`
  - Student only. Freezes deterministic top-three scenario order/targets, persists a new plan version and linked recommendations, then asks PlannerAgent only for explanation.

- `GET /training-plans/current`
  - Returns the student's latest plan. Teacher/admin review requires `user_id`.

- `GET /training-plans`
  - Returns versioned plan history. Teacher/admin review requires `user_id`.

- `POST /training-sessions`
  - Body: `{ "user_id": 1, "scenario_id": 1 }`
  - Creates a training session.

- `POST /training-sessions/{session_id}/actions`
  - Body: `{ "action_type": "verify_identity", "payload": {} }`
  - Records an action, runs deterministic rule check, saves a score.
  - Returns `409` after the session has been completed.

- `POST /training-sessions/{session_id}/complete`
  - Runs the final deterministic rule check and saves the final score.
  - Marks the session `completed` and prevents further actions or duplicate submission.
  - Invokes ExaminerAgent only to explain the frozen rule result.
  - If the configured AI provider is unavailable, returns a deterministic fallback explanation; AI failure does not undo or block the business result.

- `POST /ai/evaluate`
  - Body: `{ "session_id": 1, "agent_name": "coach", "learner_message": "..." }`
  - Routes to the requested AI agent.

## 7. AI Agent Design

Current agents:

- CustomerAgent: simulates a bank customer.
- CoachAgent: gives training hints.
- ExaminerAgent: explains performance and score reasons.
- ScenarioAgent: drafts new scenarios.
- PlannerAgent: creates personalized study plans.

Provider selection:

- `AI_PROVIDER=mock` uses local MockProvider.
- `AI_PROVIDER=deepseek` uses DeepSeekProvider.

Required DeepSeek variables:

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`
- `DEEPSEEK_MODEL`

The DeepSeek API key must stay only in backend `.env` or deployment secrets. It must never be put into React code, checked into Git, logged, or returned from an API endpoint.

## 8. Running Locally

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
pytest
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
pnpm install
pnpm dev
```

If the local environment cannot find `node`, install Node.js or add the active Node binary to `PATH` before running `pnpm`.

Open:

- Frontend: `http://localhost:5173`
- Backend docs: `http://localhost:8000/docs`

## 9. Testing

Current backend tests cover:

- Health check
- Demo seed
- Scenario list
- Training session creation
- Rule check after first action
- Mock AI coach response
- Successful and incomplete final training submissions
- Completed-session action and duplicate-submit rejection
- Missing-user session creation rejection
- Rule-only and explicitly weighted AI scoring behavior
- Examiner-provider failure fallback during final submission
- Initial migration upgrade, metadata drift check, downgrade, and re-upgrade
- Valid workflows for all six demo scenarios
- Operation order, numeric bounds, identity/account matching, available balance, unknown operations, and authorization timing

Recommended next test additions:

- Frontend component and end-to-end tests for both role workspaces
- Authentication rate-limit and password-lifecycle tests
- Scenario update concurrency and version-restore tests
- Production PostgreSQL migration verification

## 10. Key Decisions

- Start with a small vertical slice instead of many unfinished screens.
- Keep rule checks deterministic.
- Use MockProvider by default so local development does not require an API key.
- Keep DeepSeek integration behind a provider abstraction.
- Use SQLite for early development and SQLAlchemy so PostgreSQL migration is realistic.
- Use a simple UI that exposes the product direction immediately: scenario, teller actions, rule check, AI coach.

## 11. Known Gaps

- Authentication/RBAC foundation is implemented; self-service registration, password reset, rate limiting, and production HttpOnly-cookie sessions remain open.
- Existing pre-migration SQLite databases require deliberate adoption: recreate disposable development data, or back up and verify the schema before stamping revision `20260813_0001`.
- Customer role-play uses bounded recent conversation context but has no semantic long-term memory retrieval yet.
- Teachers can edit current scenarios and audit versions, but cannot create, duplicate, restore, publish, or schedule policy versions yet.
- Student and per-student teacher analytics exist; class/cohort analytics and score-trend charts do not.
- Deployment files exist, but a public FastAPI/PostgreSQL host is still required for a functional GitHub Pages release.
- No frontend automated tests yet.
- DeepSeek works server-side, but prompt-injection evaluation, structured-output validation, rate limiting, and cost controls need hardening.

## 12. Recommended Next Development Order

1. Deploy the backend with PostgreSQL and encrypted environment secrets; connect GitHub Pages through `VITE_API_BASE_URL`.
2. Add frontend component/end-to-end coverage for student and teacher workflows.
3. Add score-trend charts and class/cohort analytics.
4. Add scenario create/duplicate/restore/publish operations with optimistic concurrency.
5. Harden authentication with rate limiting, password lifecycle, audit records, and production HttpOnly-cookie sessions.
6. Expand rule-policy v1 with transaction fees, daily limits, card/account status, and explicit policy effective dates.
7. Add prompt-injection tests, structured AI outputs, timeout/retry policy, and usage budgets.

## 13. Prohibited Changes

Future agents must not:

- Expose DeepSeek API keys in frontend code.
- Let AI override deterministic business rule results.
- Replace the product with a simple chatbot.
- Add broad unrelated admin modules before the training loop is useful.
- Commit local `.env`, SQLite database files, virtual environments, or `node_modules`.
- Rewrite the whole codebase just to change style.

## 14. Work Rules for Future Agents

- Read this handoff before editing.
- Inspect current files before modifying.
- Preserve existing behavior unless the task explicitly changes it.
- Keep changes small and verifiable.
- Add tests when touching rule logic, scoring, sessions, or provider routing.
- Prefer existing module boundaries.
- After each meaningful stage, run at least the relevant backend tests or frontend build.
- Document new endpoints, environment variables, and business rules in this file or nearby docs.

## 15. Suggested Product North Star

The system should eventually feel like this:

1. A student enters a realistic teller scenario.
2. A customer agent behaves like a real customer with needs, confusion, and constraints.
3. The student performs teller actions in the UI.
4. The rule engine checks hard business correctness.
5. The coach agent gives contextual hints during practice.
6. The examiner agent produces a final performance report.
7. The planner agent recommends the next training sequence.
8. Teachers can inspect progress, weaknesses, and class-level analytics.

## 16. Latest Development Stage (2026-08-13)

Completed the first end-to-end training completion stage:

- Moved create-session and submit-action business logic from API routes into `TrainingService`.
- Added `TrainingService.complete_session` and `POST /api/training-sessions/{id}/complete`.
- The final endpoint freezes the deterministic rule result, persists the final score, marks the session completed, and then asks ExaminerAgent for explanation.
- Completed sessions reject further actions and duplicate completion with HTTP `409`.
- Missing users are now rejected when creating a session instead of relying on a later foreign-key failure.
- Fixed scoring semantics so an absent AI rubric score does not silently turn a perfect rule score of 100 into a total of 80. Explicit AI scores still use scenario weights.
- Added matching frontend TypeScript types, API client method, submit button, error state, completion state, and report panel.

Verification performed:

```bash
cd backend
source .venv/bin/activate
pytest -q
# 10 passed

cd ../frontend
pnpm build
# TypeScript and Vite production build succeeded
```

## 22. Personalized Training Plan Loop (2026-08-13)

- Added migration `20260813_0005` so Recommendations are linked to the exact TrainingPlan version that created them.
- Deterministic plan selection prioritizes trained business types below 85 by ascending average score, then fills remaining slots with untrained scenarios ordered basic before intermediate. If everything is mastered, the lowest-scoring mastered areas receive reinforcement.
- Each plan freezes at most three scenarios, priority order, selection reason, current average, and target score. PlannerAgent can explain only and cannot alter this structure.
- Every generated plan stores an ability-analysis snapshot, AI/fallback explanation marker, goals, ordered items, and linked recommendation rows. Older plan versions remain queryable.
- Added student generation/current/history endpoints and teacher/admin review boundaries. Only students may generate plans for themselves.
- Restricted the generic `/ai/evaluate` route so students can call only CoachAgent; they cannot bypass dedicated workflows to invoke Planner, Examiner, Scenario, or Customer agents.
- AI-provider failure still persists the deterministic plan with a safe fallback explanation.
- Added a frontend next-training panel with explicit generation, ordered targets, PlannerAgent explanation, and one-click scenario selection.

Verification:

```bash
cd backend
source .venv/bin/activate
pytest -q
# 37 passed

cd ../frontend
pnpm build
# TypeScript and Vite production build succeeded
```

## 21. Scenario Customer and Conversation Memory (2026-08-13)

- Added migration `20260813_0004` and a customer profile for each of the six demo scenarios.
- Customer profiles include public name/persona/opening line/facts plus server-only internal role-play notes. Internal notes are excluded from scenario API responses and teacher update payloads.
- Added a dedicated CustomerAgent conversation service with a maximum 12-message prompt window and full persisted learner/customer history.
- CustomerAgent is constrained to stay in role, avoid inventing critical bank data, avoid performing teller actions, and never judge compliance or scores.
- AI-provider failure falls back to the scenario opening line and records `ai_generated=false`; the conversation remains usable and deterministic training continues.
- Coach and Examiner receive recent conversation context only for natural-language explanation. `BusinessRuleEngine.evaluate` remains unchanged and receives no conversation content.
- Completed sessions reject new customer messages; students cannot read another student's conversation, while teacher/admin review uses the existing view authorization boundary.
- Added an AI customer panel to the frontend with scenario persona, opening line, teller input, persisted turn display, and explicit rule-engine separation notice.

Verification:

```bash
cd backend
source .venv/bin/activate
pytest -q
# 32 passed

cd ../frontend
pnpm build
# TypeScript and Vite production build succeeded
```

## 19. Authentication and Role Foundation (2026-08-13)

- Added migration `20260813_0003` with PBKDF2 password hashes, user activation state, and revocable/expiring authentication tokens.
- Raw bearer tokens are returned once and only SHA-256 digests are stored. Passwords use independent random salts and PBKDF2-HMAC-SHA256 with 310,000 iterations.
- Added login, current-user, and logout endpoints. Logout revokes the server-side token.
- Added backend role enforcement for `student`, `teacher`, and `admin`; frontend role labels are informational and are not trusted for authorization.
- Students can create training sessions only for themselves and cannot modify another student's session. Teachers/admins can inspect authenticated scenario data; teachers/admins can update validated scenarios; only admins can list users.
- Added an in-memory-token frontend login screen. Browser refresh intentionally requires login again; production persistence should move to secure HttpOnly cookies rather than localStorage.
- Development seed is disabled by default. Run `python -m app.db.seed_demo` explicitly after migration. The HTTP seed endpoint exists only when `ENABLE_DEV_SEED=true` for tests or local-only workflows.

Demo setup:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
python -m app.db.seed_demo
```

Demo accounts:

- `demo_student` / `Student123!`
- `demo_teacher` / `Teacher123!`
- `demo_admin` / `Admin123!`

## 20. Training History and Ability Analysis (2026-08-13)

- Added authenticated training history for students and teacher/admin review with explicit student selection.
- Added stored final-report retrieval using the latest persisted final score and Examiner evaluation. Active sessions return HTTP `409` because no final report exists yet.
- Added deterministic ability analysis by business type: completed count, average score, pass rate, proficiency level, repeated missing steps/violations, and weak business types for retraining.
- Analytics never asks AI to decide pass/fail or recalculate scores. Examiner content is display-only context.
- Added student frontend panels for recent history, historical report review, overall metrics, per-business progress, and main weaknesses. Queries refresh after session creation/completion.
- Replaced deprecated `datetime.utcnow` ORM defaults with a centralized UTC helper while retaining the current naive-UTC SQLite column contract.

Verification:

```bash
cd backend
source .venv/bin/activate
pytest -q
# 29 passed

cd ../frontend
pnpm build
# TypeScript and Vite production build succeeded
```

The test run reports a dependency deprecation warning from Starlette TestClient; it does not fail the suite. A later maintenance stage should follow the Starlette/httpx migration guidance.

## 23. Teacher Workspace, DeepSeek, UI, and Release Stage (2026-08-13)

- Added a role-aware teacher workspace for selecting students, reviewing deterministic history/ability/plan data, editing validated scenario fields, and inspecting scenario change history.
- Added `ScenarioVersion` and migration `20260813_0006`. Every teacher/admin update stores the complete prior scenario state before changing the current record.
- Added teacher/admin-only student listing and scenario-version endpoints, with matching frontend TypeScript contracts and authorization tests.
- Connected and smoke-tested the real DeepSeek provider from the backend only. The local key remains in ignored `backend/.env`; tests explicitly select MockProvider.
- Reworked the UI into a consistent training product system with responsive panels, metric cards, progress indicators, accessible fields, clearer role workspaces, and stronger completion/review hierarchy.
- Added backend/frontend Dockerfiles, Nginx SPA routing, Docker Compose persistent demo storage, configurable CORS and frontend API origins, CI, and GitHub Pages deployment workflow.
- Added `docs/DEPLOYMENT.md` with the static-frontend/server-backend boundary and production release checklist.

Verification:

```bash
cd backend
source .venv/bin/activate
pytest -q
# 37 passed

# From a new temporary SQLite database:
alembic upgrade head
alembic check
# All six revisions applied; no new upgrade operations detected

cd ../frontend
pnpm build
VITE_BASE_PATH=/ai-banksim/ VITE_API_BASE_URL=https://api.example.invalid pnpm build
# Both production builds succeeded
```

Docker was not available in the development workstation, so image construction must still be verified in CI or on a Docker-enabled machine. A GitHub Pages artifact is not a complete hosted system until `VITE_API_BASE_URL` points to an HTTPS FastAPI deployment whose CORS list includes the Pages origin.

Git release state: the public source repository is `https://github.com/zhengupup-pixel/ai-banksim`. GitHub cloud CI passed for both backend and frontend, Pages deployment succeeded, and the login UI was verified at `https://zhengupup-pixel.github.io/ai-banksim/`. The Pages subpath required `createBrowserRouter(..., { basename: import.meta.env.BASE_URL })`; this fix is included locally and remotely. Pages remains frontend-only until its repository variable `VITE_API_BASE_URL` points to a public FastAPI deployment.

## 24. No-login Competition Demo (2026-08-13)

- The public Pages artifact now builds with `VITE_DEMO_MODE=true` and opens directly in the student training console; judges do not need credentials.
- Added six browser-local competition scenarios with prefilled example business data and deterministic validation for required steps, order, identity/account matches, balance checks, and conditional large-transaction authorization.
- Added reproducible Customer, Coach, Examiner, and Planner demonstration responses plus session-local history and ability analysis, so the entire product loop remains interactive without a hosted API.
- The UI explicitly labels this behavior as a competition demonstration. It does not claim browser responses are live DeepSeek output, and the real DeepSeek key/provider remain server-only.
- Normal local/server builds keep `VITE_DEMO_MODE=false` and continue using FastAPI authentication, database persistence, and backend-authoritative rules.

## 17. Alembic Initial Migration Stage (2026-08-13)

- Added a complete Alembic environment and initial revision `20260813_0001` for all 11 domain tables and their current indexes/foreign keys.
- Alembic reads `DATABASE_URL` through backend settings, so SQLite development and future PostgreSQL deployments use the same migration entry point.
- Disabled implicit application-startup `create_all` by default. The schema must be upgraded before Uvicorn starts serving requests.
- Added `AUTO_CREATE_TABLES=false` to `.env.example`; setting it to true is only for temporary local prototypes.
- Added an automated migration test that creates an isolated SQLite database, upgrades to head, checks metadata drift, downgrades to base, and upgrades again.

Standard database workflow:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

For an ignored/disposable SQLite database created by the earlier `create_all` startup, delete that database and run `alembic upgrade head`. For data that must be retained, first back it up and verify that its schema matches the initial revision before running `alembic stamp 20260813_0001`.

## 18. Multi-Scenario Rule Policy Stage (2026-08-13)

- Added Pydantic-validated rule policy v1 (`app/schemas/rules.py`) and persisted it through migration `20260813_0002`.
- Seed now idempotently maintains six scenarios: personal account opening, cash deposit, cash withdrawal, transfer, card loss reporting, and card replacement.
- Deterministic rules cover required business inputs, numeric minimums, identity/account matches, insufficient balances, disallowed actions, and expected-step order.
- Conditional steps cover large cash deposit review, large withdrawal authorization, and large transfer authorization. They must occur before the corresponding posting/execution step; doing them afterwards remains a violation.
- Frontend now supports scenario switching, policy-driven input fields, and extra authorization actions placed at their required workflow position.
- Test sessions use an isolated temporary SQLite database, so pytest no longer writes business data into the developer database.

Verification for this stage:

```bash
cd backend
source .venv/bin/activate
pytest -q
# 21 passed

cd ../frontend
pnpm build
# TypeScript and Vite production build succeeded
```
