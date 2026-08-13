# AI BankSim Deployment

## Deployment model

AI BankSim has two deployable parts:

1. The React application is static and can be hosted free on GitHub Pages.
2. FastAPI, SQLite/PostgreSQL, and all DeepSeek calls run on a server or container host.

GitHub Pages does not execute Python services. A Pages release without `VITE_API_BASE_URL`
can run the explicitly labelled competition demonstration when `VITE_DEMO_MODE=true`.
That mode is session-local and reproducible; it does not claim to be the hosted FastAPI
or real DeepSeek service.

## Local container deployment

From the repository root:

```bash
docker compose up --build
```

The backend container applies Alembic migrations before starting. Local SQLite data is
stored in the named `banksim_data` volume. Set `AI_PROVIDER=deepseek` and
`DEEPSEEK_API_KEY` only in an untracked local `.env` when real AI calls are required.

## GitHub Pages

The workflow `.github/workflows/pages.yml` builds with:

- `VITE_BASE_PATH=/<repository-name>/`
- `VITE_API_BASE_URL=${{ vars.VITE_API_BASE_URL }}`
- `VITE_DEMO_MODE=true` for the public competition experience

Repository setup:

1. Keep the default branch named `main`.
2. In repository Settings > Pages, select GitHub Actions as the source if it is not selected automatically.
3. Add the repository Actions variable `VITE_API_BASE_URL` with the public HTTPS FastAPI origin.
4. Add the Pages URL to backend `CORS_ORIGINS`, then redeploy the backend.
5. Run the Pages workflow again and verify login, training completion, and teacher review.

## Backend container contract

`backend/Dockerfile` expects these production variables:

- `DATABASE_URL`
- `CORS_ORIGINS`
- `AI_PROVIDER`
- `DEEPSEEK_API_KEY` when `AI_PROVIDER=deepseek`
- `DEEPSEEK_BASE_URL` and `DEEPSEEK_MODEL` when overriding defaults

Use PostgreSQL and a production secret manager for a durable public deployment. The Docker
Compose SQLite volume is suitable for a single-node demo, not horizontal scaling.

## Release verification

```bash
cd backend
source .venv/bin/activate
pytest -q
alembic upgrade head
alembic check

cd ../frontend
pnpm install --frozen-lockfile
pnpm build
```

Before every public push, confirm that `backend/.env`, database files, virtual environments,
`node_modules`, and build output are ignored and that no API key appears in staged content.
