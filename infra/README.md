# Infrastructure

Deployment and environment configuration for the proposal engine.

| File | Purpose |
|---|---|
| `Dockerfile` | Container image for the Python backend |
| `docker-compose.yml` | Local development stack (API + DB + frontend) |
| `.env.example` | Template for required environment variables |
| `.dockerignore` | Files excluded from Docker builds |
| `terraform/main.tf` | VPC, ECS cluster, S3 document bucket |
| `terraform/variables.tf` | Input variables (region, image tag, sizing, cert, CORS) |
| `terraform/ecr.tf` | ECR repository for the API image |
| `terraform/logs.tf` | CloudWatch log group |
| `terraform/alb.tf` | Load balancer, target group, listeners (HTTP/HTTPS) |
| `terraform/ecs.tf` | Task execution role, API task definition, ECS service |
| `terraform/security.tf` | IAM task role, secrets, security groups |
| `terraform/github_oidc.tf` | GitHub Actions OIDC deploy role (the `AWS_ROLE_ARN`) |
| `terraform/PLAN.md` | Original design notes for the deployment infra |

The backend runs on **AWS ECS Fargate** behind an ALB; Postgres is **Supabase**
and the frontend is on **Vercel**. First-time AWS bootstrap (OIDC role, secrets,
state bucket) is in [../docs/AWS_SETUP.md](../docs/AWS_SETUP.md); the full
apply/runbook is in [../docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md).
