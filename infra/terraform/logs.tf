# CloudWatch log group for the API service's container logs.

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/proposal-engine-${var.environment}"
  retention_in_days = 30
}
