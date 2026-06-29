# AWS Setup (first-time)

The `Deploy` workflow fails at **Configure AWS credentials** until AWS is
provisioned and the `AWS_ROLE_ARN` secret is set. This is the one-time bootstrap
to make it pass. You run these locally with an AWS admin profile; nothing here
needs to be committed.

The GitHub→AWS OIDC role is codified in Terraform
(`infra/terraform/github_oidc.tf`), so you don't hand-create it — `apply`
produces it and outputs its ARN.

## Prerequisites

- An AWS account + AWS CLI configured with admin credentials (`aws sts get-caller-identity` works).
- Terraform ≥ 1.5.
- Your Supabase `DATABASE_URL` and Anthropic API key.

## Steps

### 1. Create the Terraform state bucket

`main.tf` uses an S3 backend named `proposal-engine-terraform-state`:

```bash
aws s3api create-bucket --bucket proposal-engine-terraform-state --region us-east-1
aws s3api put-bucket-versioning --bucket proposal-engine-terraform-state \
  --versioning-configuration Status=Enabled
```

### 2. Init + create the bootstrap resources (role, ECR, secret containers)

```bash
cd infra/terraform
terraform init
terraform apply \
  -target=aws_iam_openid_connect_provider.github \
  -target=aws_iam_role.github_actions \
  -target=aws_iam_role_policy.github_actions_deploy \
  -target=aws_ecr_repository.api \
  -target=aws_secretsmanager_secret.anthropic_api_key \
  -target=aws_secretsmanager_secret.db_credentials
```

> If the account already has a GitHub OIDC provider (only one is allowed per
> account), set `-var create_github_oidc_provider=false` so Terraform references
> the existing one instead of trying to create a duplicate.

### 3. Populate the secret values

```bash
aws secretsmanager put-secret-value \
  --secret-id proposal-engine/production/anthropic-api-key \
  --secret-string 'sk-ant-...'
aws secretsmanager put-secret-value \
  --secret-id proposal-engine/production/database-url \
  --secret-string 'postgresql://postgres:...@db.<ref>.supabase.co:5432/postgres'
```

### 4. Set the GitHub Actions repo secrets

`AWS_ROLE_ARN` is the Terraform output from step 2:

```bash
terraform output -raw github_actions_role_arn   # → set as AWS_ROLE_ARN
```

In **GitHub → Settings → Secrets and variables → Actions**, add:

| Secret | Value |
|---|---|
| `AWS_ROLE_ARN` | the `github_actions_role_arn` output |
| `ANTHROPIC_API_KEY` | your Anthropic key (used by the `migrate` job) |
| `DATABASE_URL` | the Supabase connection string (used by the `migrate` job) |

### 5. Apply the rest of the infrastructure

```bash
terraform apply   # VPC, ALB, ECS cluster + service + task definition, logs
```

The ECS service starts unhealthy until an image exists in ECR — that's fixed by
the first deploy.

### 6. Trigger a deploy

Push to `main` (or re-run the failed **Deploy** workflow). It will:
`build-and-push` (image → ECR) → `migrate` (`alembic upgrade head` on Supabase)
→ `deploy` (`ecs update-service`). Then:

```bash
curl http://$(terraform output -raw api_alb_dns_name)/health   # {"status":"healthy"}
```

### 7. Point the frontend at the API

Set Vercel `API_PROXY_TARGET` (and the backend `CORS_ORIGINS`) to the ALB URL.
To enable auth, also set `AUTH_ENABLED=true` + `SUPABASE_JWT_SECRET` on the
backend and the `NEXT_PUBLIC_SUPABASE_*` vars on Vercel (see DEPLOYMENT.md).

## The deploy role's permissions

`github_oidc.tf` grants the CI role only what the workflow needs: ECR auth +
push/pull on the `proposal-engine-api` repo, and `ecs:UpdateService` /
`ecs:DescribeServices` on the API service. The trust policy is scoped to
`repo:<owner/repo>:ref:refs/heads/main`, so only `main`-branch runs can assume it.
