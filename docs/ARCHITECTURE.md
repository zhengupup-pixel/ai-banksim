# Architecture Notes

AI BankSim uses a frontend/backend split:

- Frontend: React, TypeScript, Vite, Tailwind, TanStack Query
- Backend: FastAPI, SQLAlchemy, Pydantic, Alembic-ready database layer
- Database: SQLite in development, PostgreSQL later
- AI: server-side provider abstraction with MockProvider and DeepSeekProvider

The first development milestone is now a complete narrow training loop:

```text
Scenario -> Training Session -> Teller Action -> Rule Check -> Final Submission
         -> Deterministic Final Score -> Examiner Explanation -> Locked Session
```

`TrainingService` owns session state changes and persistence. The rule engine freezes the
business result before ExaminerAgent explains it. AI-provider failure may degrade the
natural-language explanation but must never change or block the deterministic result.

Future work should enrich this loop before adding unrelated modules.

Database schema lifecycle:

```text
SQLAlchemy metadata -> Alembic revision -> alembic upgrade head -> application startup
```

Application startup does not mutate the schema by default. This prevents an
unversioned `create_all` call from masking missing migrations in deployment.

Authentication uses revocable random bearer tokens. Only a SHA-256 token digest is
stored in the database; passwords are independently salted with PBKDF2-HMAC-SHA256.
Role checks and training-session ownership checks are enforced by FastAPI backend
dependencies, never by frontend claims.

Training analytics is a deterministic read model:

```text
Completed sessions + final Score.details + Scenario
  -> history and stored-report reconstruction
  -> per-business average score and pass rate
  -> repeated missing-step/violation weaknesses
  -> next-business recommendations
```

ExaminerAgent text is displayed in reports but never recalculates pass status,
averages, weakness counts, or recommendations.

Customer simulation keeps a separate boundary:

```text
Public customer profile + private scenario notes + last 12 messages
  -> CustomerAgent role-play
  -> persisted learner/customer Conversation rows
  -> bounded context for Coach/Examiner explanations
```

Private customer notes are never returned in scenario API responses. Conversation
context enriches role-play and explanations but is not passed into rule evaluation.

Personalized planning preserves the same authority boundary:

```text
Deterministic ability analysis
  -> weak trained businesses (ascending score)
  -> untrained businesses (basic before intermediate)
  -> frozen top-3 order and target scores
  -> persisted TrainingPlan + Recommendations
  -> PlannerAgent explanation only
```

Scenario rule policy v1 is stored with each scenario and validated through a
Pydantic schema before evaluation. It supports required inputs, numeric bounds,
identity/account field matching, available-balance checks, operation ordering,
and threshold-triggered authorization steps. `BusinessRuleEngine` alone turns
these policies and teller actions into business violations and the base score.

Teacher scenario changes are auditable:

```text
Current validated Scenario
  -> teacher/admin update request
  -> immutable snapshot of the previous state in ScenarioVersion
  -> updated current Scenario
```

The version table is review history, not a second source of executable rules. Training
still evaluates only the policy attached to the selected current scenario.

Deployment preserves the server trust boundary:

```text
GitHub Pages (React, public configuration only)
  -> HTTPS FastAPI container
      -> rule/scoring services + database
      -> DeepSeek key in server environment only
```
