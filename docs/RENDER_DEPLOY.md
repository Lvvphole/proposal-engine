# Deploy the backend on Render

Render is the simplest production host for this app: it runs the existing
Docker image as a long-running web service, so the in-process background
tasks (extract → price) and SSE event bridge work without modification. Pair
with **Supabase** (Postgres) and **Vercel** (frontend).

```
        Browser
           │  (same-origin /api/* — Vercel rewrites proxy here)
           ▼
   ┌──────────────┐        ┌──────────────────┐
   │  Vercel      │ ─────► │  Render Web      │ ──► Anthropic API
   │  (Next.js)   │  /api  │  (FastAPI)       │
   └──────────────┘        └────────┬─────────┘
                                    │ asyncpg + TLS
                                    ▼
                            ┌──────────────┐
                            │   Supabase   │
                            │   Postgres   │
                            └──────────────┘
```

## What you need

- A Render account (the free `starter` plan works for a pilot; the blueprint
  uses it by default).
- A Supabase project with `DATABASE_URL` and the JWT secret to hand.
- An Anthropic API key.

## Steps

### 1. Create the service from the blueprint

In Render: **Blueprints → New Blueprint** → connect this repo. Render reads
[`render.yaml`](../render.yaml) and proposes one web service
(`proposal-engine-api`) built from `infra/Dockerfile`.

The blueprint sets all non-secret config inline (model IDs, budget limits,
`AUTH_ENABLED=false`, etc.) and marks the three secrets as `sync: false` so
you supply them in the dashboard before the first deploy.

### 2. Set the secrets

In the service's **Environment** tab, set:

| Key | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your Anthropic key |
| `DATABASE_URL` | Supabase connection string (the pooler URL is fine: `postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres`) |
| `SUPABASE_JWT_SECRET` | Supabase → Project Settings → API → JWT Secret. Only used when you flip `AUTH_ENABLED=true`. |
| `CORS_ORIGINS` | leave blank for now; set to the Vercel URL after step 4 |

### 3. Deploy

Render builds the Dockerfile (final stage `production`), then runs the blueprint's
`preDeployCommand: alembic upgrade head` against Supabase. When that succeeds
it starts the API and routes traffic only after `/health` returns 200.
Subsequent pushes to `main` redeploy automatically.

### 4. Point Vercel at it

Render gives the service a URL like `https://proposal-engine-api.onrender.com`.
In Vercel → Project Settings → Environment Variables, set:

```
API_PROXY_TARGET = https://<your-service>.onrender.com
```

(That's the rewrite target in `frontend/next.config.js`; the browser still
calls same-origin `/api/*`, no CORS to wire.) Redeploy the frontend.

### 5. Smoke test

```bash
curl https://<your-service>.onrender.com/health   # {"status":"healthy"}
```

Then upload a quote through the Review Surface; the full extract → price →
review → deliver loop should run.

### 6. (When ready) Turn on auth

After the frontend Supabase login is configured (`NEXT_PUBLIC_SUPABASE_*` set
on Vercel — see [`DEPLOYMENT.md`](./DEPLOYMENT.md)):

- Set `AUTH_ENABLED=true` in the Render environment.
- Set `CORS_ORIGINS` to the Vercel URL.

Render redeploys; auth + per-user tenancy is live.

## Comparison with the AWS path

The AWS path ([`AWS_SETUP.md`](./AWS_SETUP.md)) gives you fine-grained control
(VPC, ALB, OIDC role, ECS service) but is meaningful first-time work. **Render
needs no Terraform, no IAM, no AWS state bucket** — connect the repo, paste
three secrets, deploy. Re-platforming to AWS later is straightforward (the
Terraform is already written) since the application image is the same.

## What about MCP?

The MCP server is stdio-only and not deployed as a service anywhere. Run it
locally for Claude Desktop / Claude Code via `python -m proposal_engine_mcp`
when needed.
