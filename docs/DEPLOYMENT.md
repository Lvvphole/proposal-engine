# Deployment

The system deploys as three pieces:

| Piece | Host | How it ships |
|---|---|---|
| **Database** | Supabase (managed Postgres) | Schema via Alembic migrations |
| **Frontend** (Review Surface, Next.js) | Vercel | Vercel Git integration |
| **Backend** (FastAPI API + MCP server) | AWS ECS Fargate | `deploy.yml` → ECR → ECS |

```
        Browser
           │  (same-origin /api/* — proxied by Next rewrites)
           ▼
   ┌──────────────┐        ┌──────────────────┐
   │  Vercel      │ ─────► │  Backend (ECS)   │ ──► Anthropic API
   │  (Next.js)   │  /api  │  FastAPI + MCP   │
   └──────────────┘        └────────┬─────────┘
                                    │ asyncpg + TLS
                                    ▼
                            ┌──────────────┐
                            │   Supabase   │
                            │   Postgres   │
                            └──────────────┘
```

## 1. Database — Supabase

1. Create a Supabase project.
2. Copy the connection string from **Project Settings → Database**
   (use the **Connection pooling** string, port `6543`, for serverless/high-
   concurrency backends; the direct string on `5432` is fine otherwise).
3. Set it as `DATABASE_URL`. The app normalises `postgresql://` to the
   asyncpg driver and enables TLS automatically for `*.supabase.co` /
   `*.supabase.com` hosts — paste the URI as-is.
4. Apply the schema:

   ```bash
   DATABASE_URL='postgresql://postgres:...@db.<ref>.supabase.co:5432/postgres' \
   ANTHROPIC_API_KEY=sk-ant-... \
   alembic upgrade head
   ```

   In CI/CD this runs automatically in the `migrate` job of `deploy.yml`.

## 2. Frontend — Vercel

1. Import the repo into Vercel.
2. Set **Root Directory** to `frontend/`.
3. Add an environment variable:
   - `API_PROXY_TARGET` = the backend's public URL (e.g.
     `https://api.proposal-engine.example.com`).

   The browser only ever calls same-origin `/api/*`; `next.config.js`
   rewrites proxy those requests to `API_PROXY_TARGET`, so there is **no
   CORS** to configure for the browser. (If you instead call the API
   cross-origin, set `CORS_ORIGINS` on the backend to the Vercel URL.)
4. Deploy. Vercel runs `npm ci && npm run build` from `frontend/`.

## 3. Backend — AWS ECS

`deploy.yml` (on push to `main`) builds the API and MCP images, pushes them
to ECR, runs migrations, then forces a new ECS deployment.

### Required GitHub Actions secrets

| Secret | Purpose |
|---|---|
| `AWS_ROLE_ARN` | OIDC role for ECR push + ECS deploy |
| `ANTHROPIC_API_KEY` | LLM access (also needed by the migrate job) |
| `DATABASE_URL` | Supabase connection string (migrate job) |

### Infrastructure (Terraform)

`infra/terraform/` provisions the VPC, ECS cluster, S3 document bucket, IAM,
and Secrets Manager entries. **Note:** the Terraform currently defines the
cluster but not the ECS services, task definitions, ALB, or ECR repos that
`deploy.yml` targets — those must be added before the first deploy will
succeed. The database is **not** in Terraform (it's Supabase); store the
`DATABASE_URL` in the `database-url` secret and inject it into the task.

## Local development

```bash
cp infra/.env.example .env        # fill in ANTHROPIC_API_KEY; DATABASE_URL
                                  # defaults to a local sqlite file
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000

cd frontend && cp .env.example .env.local && npm install && npm run dev
```
