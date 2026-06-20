# Input variables for the proposal-engine infrastructure.

variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment name (used in resource names)."
  type        = string
  default     = "production"
}

variable "api_image_tag" {
  description = "Image tag the API service runs. deploy.yml pushes :latest each run."
  type        = string
  default     = "latest"
}

variable "api_desired_count" {
  description = "Number of API tasks to run."
  type        = number
  default     = 2
}

variable "api_cpu" {
  description = "Fargate CPU units for the API task (e.g. 256, 512, 1024)."
  type        = string
  default     = "512"
}

variable "api_memory" {
  description = "Fargate memory (MiB) for the API task."
  type        = string
  default     = "1024"
}

variable "api_certificate_arn" {
  description = <<-EOT
    ACM certificate ARN for the API's HTTPS listener. When set, the ALB serves
    HTTPS on 443 and redirects 80→443. When empty, the ALB serves plain HTTP on
    80 (acceptable for an MVP; the Vercel frontend proxies to http://<alb-dns>).
  EOT
  type        = string
  default     = ""
}

variable "cors_origins" {
  description = "Comma-separated allowed CORS origins (the Vercel frontend URL)."
  type        = string
  default     = ""
}
