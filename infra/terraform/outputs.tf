output "public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_eip.taskflow.public_ip
}

output "ssh_command" {
  description = "SSH command to connect to the server"
  value       = "ssh -i ~/.ssh/${var.key_pair_name}.pem ubuntu@${aws_eip.taskflow.public_ip}"
}

output "ssh_command_deploy" {
  description = "SSH command to connect as deploy user"
  value       = "ssh -i ~/.ssh/${var.key_pair_name}.pem deploy@${aws_eip.taskflow.public_ip}"
}

output "app_url" {
  description = "Application URL"
  value       = "http://${aws_eip.taskflow.public_ip}"
}

output "api_docs_url" {
  description = "API documentation URL"
  value       = "http://${aws_eip.taskflow.public_ip}/docs"
}

output "security_group_id" {
  description = "Security group ID (needed for OIDC SSH rule management)"
  value       = aws_security_group.taskflow.id
}

output "github_actions_role_arn" {
  description = "IAM role ARN for GitHub Actions OIDC"
  value       = aws_iam_role.github_actions.arn
}

output "ami_id" {
  description = "AMI ID used for the EC2 instance"
  value       = data.aws_ami.ubuntu.id
}

output "github_secrets" {
  description = "GitHub secrets to create for CI/CD deployment"
  value       = <<-EOT

    ============================================================
    CREATE THESE GITHUB SECRETS in your repository settings:
    ============================================================

    EC2_HOST          = ${aws_eip.taskflow.public_ip}
    EC2_USER          = deploy
    EC2_SSH_KEY       = (contents of ~/.ssh/${var.key_pair_name}.pem)
    EC2_KNOWN_HOSTS   = (run: ssh-keyscan ${aws_eip.taskflow.public_ip})

    Optional (for dynamic SSH rules via OIDC):
    AWS_ROLE_ARN      = ${aws_iam_role.github_actions.arn}
    AWS_REGION        = ${var.aws_region}
    SECURITY_GROUP_ID = ${aws_security_group.taskflow.id}

    ============================================================
    ALSO CREATE .env on the server at /opt/taskflow/.env:
    ============================================================

    SECRET_KEY=<generate with: openssl rand -hex 32>
    DATABASE_URL=postgresql+asyncpg://taskflow:taskflow@db:5432/taskflow
    ENVIRONMENT=production
    DEBUG=false
    CORS_ORIGINS_STR=http://${aws_eip.taskflow.public_ip}

    ============================================================

  EOT
}
