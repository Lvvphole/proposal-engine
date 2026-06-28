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

### Authentication (Supabase JWT)

The API verifies Supabase access tokens when `AUTH_ENABLED=true`, deriving the
user from the token's `sub` and scoping quotes/contractors to that user. The
Next.js frontend signs users in with Supabase Auth (`components/AuthGate.tsx`)
and attaches the access token to every API call (`lib/api.ts`). Both are
**off by default** so local dev keeps working. To turn auth on, set all of
these together (frontend and backend must agree):

| Where | Variable | Value |
|---|---|---|
| Backend (API task) | `AUTH_ENABLED` | `true` |
| Backend (API task) | `SUPABASE_JWT_SECRET` | Supabase → Settings → API → JWT Secret (a real secret) |
| Frontend (Vercel) | `NEXT_PUBLIC_SUPABASE_URL` | `https://<ref>.supabase.co` |
| Frontend (Vercel) | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | the project's anon (publishable) key |

If only one side is configured the app will 401 — enable both at once. The
anon key is publishable; never put the JWT secret or `service_role` key in the
frontend.

### Infrastructure (Terraform)

`infra/terraform/` provisions the full backend: VPC, ECS cluster + **Fargate
service + task definition**, **ALB + target group + listeners**, **ECR repo**,
CloudWatch logs, IAM roles, and Secrets Manager entries. The database is **not**
in Terraform (it's Supabase) — its connection string lives in the `database-url`
secret and is injected into the task as `DATABASE_URL`.

Key variables (`variables.tf`): `api_certificate_arn` (set to an ACM cert ARN
for HTTPS; empty = HTTP-only MVP), `cors_origins` (the Vercel URL), plus
`api_desired_count` / `api_cpu` / `api_memory` for sizing.

The MCP server is **stdio-only** and is intentionally not deployed as a service.

#### First-time apply runbook

```bash
# 1. Populate the secret values (Terraform only creates the containers).
aws secretsmanager put-secret-value \
  --secret-id proposal-engine/production/anthropic-api-key --secret-string "sk-ant-..."
aws secretsmanager put-secret-value \
  --secret-id proposal-engine/production/database-url \
  --secret-string "postgresql://postgres:...@db.<ref>.supabase.co:5432/postgres"

cd infra/terraform
terraform init

# 2. Create the ECR repo first so the image has a push target.
terraform apply -target=aws_ecr_repository.api

# 3. Push the first image + run migrations + deploy (push to main, or run
#    deploy.yml manually). build-and-push tags :latest, which the task def uses.

# 4. Apply the rest (ALB, ECS service, logs, roles).
terraform apply

# 5. Smoke test, then point the frontend at the ALB.
curl http://$(terraform output -raw api_alb_dns_name)/health   # {"status":"healthy"}
```

Then set Vercel's `API_PROXY_TARGET` (and the backend `CORS_ORIGINS`) to the
ALB URL (`terraform output api_alb_dns_name`) and upload a quote through the
Review Surface to confirm the end-to-end path.

## Local development

```bash
cp infra/.env.example .env        # fill in ANTHROPIC_API_KEY; DATABASE_URL
                                  # defaults to a local sqlite file
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000

cd frontend && cp .env.example .env.local && npm install && npm run dev
```
