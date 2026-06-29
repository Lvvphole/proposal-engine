# GitHub Actions → AWS via OIDC.
#
# deploy.yml assumes this role (set its ARN as the AWS_ROLE_ARN repo secret) to
# push the API image to ECR and roll the ECS service. No long-lived AWS keys.
# After `terraform apply`, copy the `github_actions_role_arn` output into the
# repo secret.

data "aws_caller_identity" "current" {}

locals {
  github_oidc_url = "token.actions.githubusercontent.com"
  # Long-form ECS service ARN: arn:aws:ecs:<region>:<acct>:service/<cluster>/<service>
  account_id      = data.aws_caller_identity.current.account_id
  api_service_arn = "arn:aws:ecs:${var.aws_region}:${local.account_id}:service/proposal-engine-${var.environment}/proposal-engine-api"
}

resource "aws_iam_openid_connect_provider" "github" {
  count = var.create_github_oidc_provider ? 1 : 0

  url            = "https://${local.github_oidc_url}"
  client_id_list = ["sts.amazonaws.com"]
  # AWS validates GitHub's certificate via its own trust store; this well-known
  # thumbprint is kept for provider compatibility.
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

data "aws_iam_openid_connect_provider" "github" {
  count = var.create_github_oidc_provider ? 0 : 1
  url   = "https://${local.github_oidc_url}"
}

locals {
  github_oidc_provider_arn = (
    var.create_github_oidc_provider
    ? aws_iam_openid_connect_provider.github[0].arn
    : data.aws_iam_openid_connect_provider.github[0].arn
  )
}

resource "aws_iam_role" "github_actions" {
  name = "proposal-engine-github-actions-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRoleWithWebIdentity"
      Principal = { Federated = local.github_oidc_provider_arn }
      Condition = {
        StringEquals = {
          "${local.github_oidc_url}:aud" = "sts.amazonaws.com"
        }
        # Scope to this repo's main branch (deploy.yml runs on push to main).
        StringLike = {
          "${local.github_oidc_url}:sub" = "repo:${var.github_repo}:ref:refs/heads/main"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_actions_deploy" {
  name = "deploy"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "EcrAuth"
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
        Sid    = "EcrPushPull"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage",
        ]
        Resource = aws_ecr_repository.api.arn
      },
      {
        Sid      = "EcsDeploy"
        Effect   = "Allow"
        Action   = ["ecs:UpdateService", "ecs:DescribeServices"]
        Resource = local.api_service_arn
      },
    ]
  })
}

output "github_actions_role_arn" {
  description = "Set this as the GitHub Actions repo secret AWS_ROLE_ARN."
  value       = aws_iam_role.github_actions.arn
}
