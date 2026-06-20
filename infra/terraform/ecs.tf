# API service: task execution role, task definition, and ECS service.
# Task health is judged by the ALB target-group health check (GET /health),
# so no in-container healthcheck is needed (the slim image ships no curl).

# ── Task execution role (ECR pull, logs, secret injection) ──

resource "aws_iam_role" "ecs_execution" {
  name = "proposal-engine-ecs-execution-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_managed" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Lets ECS fetch the secrets it injects into the task at startup.
resource "aws_iam_role_policy" "ecs_execution_secrets" {
  name = "secrets-injection"
  role = aws_iam_role.ecs_execution.id

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

# ── Task definition ─────────────────────────────────────

resource "aws_ecs_task_definition" "api" {
  family                   = "proposal-engine-api-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "api"
    image     = "${aws_ecr_repository.api.repository_url}:${var.api_image_tag}"
    essential = true

    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]

    environment = [
      { name = "HOST", value = "0.0.0.0" },
      { name = "PORT", value = "8000" },
      { name = "CORS_ORIGINS", value = var.cors_origins },
    ]

    secrets = [
      { name = "ANTHROPIC_API_KEY", valueFrom = aws_secretsmanager_secret.anthropic_api_key.arn },
      { name = "DATABASE_URL", valueFrom = aws_secretsmanager_secret.db_credentials.arn },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "api"
      }
    }
  }])
}

# ── Service ─────────────────────────────────────────────

resource "aws_ecs_service" "api" {
  name            = "proposal-engine-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.api_task.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  health_check_grace_period_seconds = 60

  # Ensure a listener (and thus the target group attachment) exists first.
  depends_on = [
    aws_lb_listener.https,
    aws_lb_listener.http_redirect,
    aws_lb_listener.http_forward,
  ]

  lifecycle {
    # deploy.yml pushes a new :latest image and forces a new deployment; don't
    # fight it on subsequent applies over the running task definition.
    ignore_changes = [task_definition]
  }
}
