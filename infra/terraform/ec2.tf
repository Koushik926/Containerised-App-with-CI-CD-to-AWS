# EC2 instance for TaskFlow
resource "aws_instance" "taskflow" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  key_name      = var.key_pair_name

  vpc_security_group_ids = [aws_security_group.taskflow.id]

  # 20 GB gp3 encrypted root volume
  root_block_device {
    volume_size           = 20
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  # Require IMDSv2 (more secure)
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  # User data script to install Docker and set up the server
  user_data = file("${path.module}/user_data.sh")

  tags = {
    Name = "taskflow-server"
  }
}

# Elastic IP for stable public address
resource "aws_eip" "taskflow" {
  domain = "vpc"

  tags = {
    Name = "taskflow-eip"
  }
}

# Associate EIP with EC2 instance
resource "aws_eip_association" "taskflow" {
  instance_id   = aws_instance.taskflow.id
  allocation_id = aws_eip.taskflow.id
}
