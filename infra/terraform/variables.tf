variable "aws_region" {
  description = "AWS region to deploy to"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type (t4g.micro is Free Tier eligible)"
  type        = string
  default     = "t4g.micro"
}

variable "key_pair_name" {
  description = "Name of an existing EC2 key pair for SSH access"
  type        = string
}

variable "my_ip_cidr" {
  description = "Your IP address in CIDR notation for SSH access (e.g., 1.2.3.4/32)"
  type        = string
}

variable "enable_cloudwatch_alarm" {
  description = "Enable CloudWatch CPU alarm with SNS notification"
  type        = bool
  default     = false
}

variable "alarm_email" {
  description = "Email address for CloudWatch alarm notifications (required if enable_cloudwatch_alarm is true)"
  type        = string
  default     = ""
}

variable "github_org" {
  description = "GitHub organization or username for OIDC (e.g., Koushik926)"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name for OIDC (e.g., Containerised-App-with-CI-CD-to-AWS)"
  type        = string
  default     = "Containerised-App-with-CI-CD-to-AWS"
}
