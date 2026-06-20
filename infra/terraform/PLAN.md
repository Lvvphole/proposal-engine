# Plan: Complete the Backend Deployment Terraform

## Why

`deploy.yml` pushes images to ECR and forces a new ECS deployment, but
`infra/terraform/` currently provisions only the **VPC, ECS cluster, S3
bucket, IAM task role, and Secrets Manager entries**. The compute resources
the workflow targets do not exist yet, so the first `deploy` job will fail:

| `deploy.yml` references | Exists in Terraform? |
|---|---|
| ECR repo `proposal-engine-api` | ❌ |
| ECR repo `proposal-engine-mcp` | ❌ |
| ECS cluster `proposal-engine-production` | ✅ |
| ECS service `proposal-engine-api` | ❌ |
| ECS service `proposal-engine-mcp` | ❌ |
| Task definitions / ALB / log groups | ❌ |

This document is the implementation plan to close that gap. It is intentionally
shipped as a plan (not applied Terraform) so the resource shapes and the open
decisions below can be reviewed first.

## Decision needed first: MCP transport

The MCP image runs `python -m proposal_engine_mcp`, which serves over **stdio**,
not a network port. A stdio process behind an ECS *service* + load balancer
exposes nothing useful. There is an `http.py` in the package suggesting an HTTP
variant. Pick one before building the `mcp` service:

- **(A) Drop the MCP ECS service.** Ship MCP only for local stdio use (Claude
  Desktop / Claude Code). Remove the MCP build/deploy steps from `deploy.yml`.
  *Recommended* unless there's a remote-MCP requirement.
- **(B) Serve MCP over HTTP/SSE.** Finish an HTTP entrypoint, expose port 3100
  behind the ALB (separate listener/path), and keep the service.

The rest of this plan assumes **(A)** for the load-balanced surface and treats
the MCP service as optional.

## Resources to add

Suggested new files: `infra/terraform/ecr.tf`, `ecs.tf`, `alb.tf`,
`logs.tf`, plus additions to `security.tf` / `variables.tf`.

1. **ECR repositories** (`ecr.tf`)
   - `aws_ecr_repository.api` (`proposal-engine-api`) and, if (B),
     `.mcp` (`proposal-engine-mcp`).
   - `image_scanning_configuration { scan_on_push = true }`,
     `image_tag_mutability = "MUTABLE"`.
   - `aws_ecr_lifecycle_policy` to expire untagged images after N days.

2. **CloudWatch log groups** (`logs.tf`)
   - `/ecs/proposal-engine-api` (and `-mcp`), `retention_in_days = 30`.

3. **ECS task execution role** (`security.tf`)
   - New role assumed by `ecs-tasks.amazonaws.com` with
     `AmazonECSTaskExecutionRolePolicy` (ECR pull + CloudWatch logs) and
     `secretsmanager:GetSecretValue` on the two secrets. Keep the existing
     `aws_iam_role.ecs_task` as the **task role** (app S3 access).

4. **Task definition — API** (`ecs.tf`)
   - Fargate, `cpu = 512`, `memory = 1024`.
   - Container `api` from the ECR image, `containerPort = 8000`.
   - `secrets`: `ANTHROPIC_API_KEY` ← anthropic secret,
     `DATABASE_URL` ← `database-url` secret.
   - `environment`: `CORS_ORIGINS` = the Vercel URL, `HOST=0.0.0.0`,
     `PORT=8000`.
   - `healthCheck`: `CMD-SHELL curl -f http://localhost:8000/health || exit 1`.
   - `logConfiguration` → the API log group.

5. **ALB + target group + listener** (`alb.tf`)
   - `aws_lb.api` (internet-facing) in the public subnets.
   - `aws_lb_target_group.api` (`target_type = "ip"`, port 8000,
     health check path `/health`).
   - HTTPS `aws_lb_listener` on 443 with an ACM cert (`var.api_certificate_arn`);
     optional HTTP→HTTPS redirect listener on 80.

6. **ECS service — API** (`ecs.tf`)
   - `aws_ecs_service.api` on the existing cluster, `launch_type = "FARGATE"`,
     `desired_count = 2`, network config in **private** subnets with the API
     task SG, `load_balancer` block wiring the target group → container:8000.
   - `depends_on` the listener.

7. **Security group adjustments** (`security.tf`)
   - New `alb` SG: ingress 80/443 from `0.0.0.0/0`.
   - Change the API task SG ingress to allow 8000 **only from the ALB SG**
     (today `aws_security_group.api` allows 8000 from the internet — tighten it).
   - Confirm egress allows 443 (Anthropic) and the Supabase port (5432/6543).

8. **Secret values**
   - Terraform creates the secret *containers*; populate
     `anthropic-api-key` and `database-url` (Supabase connection string) via
     `aws_secretsmanager_secret_version` fed by sensitive variables, or set
     them out-of-band. Never commit the values.

9. **Autoscaling (optional)** (`ecs.tf`)
   - `aws_appautoscaling_target` + target-tracking policy on ECS CPU ~60%.

10. **DNS/TLS (optional)**
    - `aws_acm_certificate` (DNS-validated) + `aws_route53_record` for the API
      hostname; feed the cert ARN into the listener.

## New variables (`variables.tf` / `terraform.tfvars`)

`api_certificate_arn`, `cors_origins` (Vercel URL), `api_desired_count`,
`api_image_tag` (default `latest`), and the two sensitive secret values.

## Apply sequence

1. `terraform apply` the ECR repos first (so images have a push target).
2. Push images via `deploy.yml` (or manually) so the task def has an image.
3. `terraform apply` the rest (logs, roles, task defs, ALB, service).
4. Point Vercel's `API_PROXY_TARGET` and the backend `CORS_ORIGINS` at the
   ALB/custom domain.

## Acceptance

- `deploy.yml`'s `deploy` job succeeds end-to-end.
- `GET https://<api-domain>/health` returns `{"status":"healthy"}`.
- The Vercel frontend's `/api/*` calls reach the API through the ALB.
