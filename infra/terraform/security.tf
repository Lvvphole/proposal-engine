# Security configuration — IAM, security groups, secrets

# ── Security Groups ──────────────────────────────────────

resource "aws_security_group" "api" {
  name_prefix = "proposal-engine-api-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Postgres lives on Supabase (managed), so no in-VPC database security
# group is required; the API egresses to Supabase over TLS.

# ── Secrets Manager ──────────────────────────────────────

resource "aws_secretsmanager_secret" "anthropic_api_key" {
  name        = "proposal-engine/${var.environment}/anthropic-api-key"
  description = "Anthropic API key for LLM calls"
}

resource "aws_secretsmanager_secret" "db_credentials" {
  name        = "proposal-engine/${var.environment}/database-url"
  description = "Supabase Postgres connection string (DATABASE_URL)"
}

# ── IAM ──────────────────────────────────────────────────

resource "aws_iam_role" "ecs_task" {
  name = "proposal-engine-ecs-task-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "ecs_secrets" {
  name = "secrets-access"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["secretsmanager:GetSecretValue"]
      Resource = [
        aws_secretsmanager_secret.anthropic_api_key.arn,
        aws_secretsmanager_secret.db_credentials.arn,
      ]
    }]
  })
}

resource "aws_iam_role_policy" "ecs_s3" {
  name = "s3-documents-access"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
      Resource = [
        aws_s3_bucket.documents.arn,
        "${aws_s3_bucket.documents.arn}/*",
      ]
    }]
  })
}
