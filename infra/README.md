# Infrastructure

Deployment and environment configuration for the proposal engine.

| File | Purpose |
|---|---|
| `Dockerfile` | Container image for the Python backend |
| `docker-compose.yml` | Local development stack (API + DB + frontend) |
| `.env.example` | Template for required environment variables |
| `.dockerignore` | Files excluded from Docker builds |
| `terraform/main.tf` | Cloud infrastructure provisioning |
| `terraform/security.tf` | IAM, secrets, and network security |
