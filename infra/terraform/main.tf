# Proposal Engine — Terraform Configuration
# Target: AWS (ECS Fargate + RDS PostgreSQL + S3)

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "proposal-engine-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  default = "us-east-1"
}

variable "environment" {
  default = "production"
}

# ── VPC ──────────────────────────────────────────────────

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "proposal-engine-${var.environment}"
  cidr = "10.0.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true
}

# ── Database ─────────────────────────────────────────────
# Postgres is hosted on Supabase (managed), not RDS. The full connection
# string (DATABASE_URL) is stored in Secrets Manager — see security.tf —
# and injected into the ECS task as the DATABASE_URL env var. Run
# `alembic upgrade head` against it to apply migrations.

# ── ECS Cluster ──────────────────────────────────────────

resource "aws_ecs_cluster" "main" {
  name = "proposal-engine-${var.environment}"
}

# ── S3 for document storage ──────────────────────────────

resource "aws_s3_bucket" "documents" {
  bucket = "proposal-engine-documents-${var.environment}"
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}
