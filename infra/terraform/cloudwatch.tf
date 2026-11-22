# Optional CloudWatch alarm for CPU utilization
resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  count = var.enable_cloudwatch_alarm ? 1 : 0

  alarm_name          = "taskflow-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Alarm when CPU exceeds 80% for 10 minutes"
  alarm_actions       = [aws_sns_topic.alerts[0].arn]
  ok_actions          = [aws_sns_topic.alerts[0].arn]

  dimensions = {
    InstanceId = aws_instance.taskflow.id
  }

  tags = {
    Name = "taskflow-cpu-alarm"
  }
}

# SNS topic for alerts
resource "aws_sns_topic" "alerts" {
  count = var.enable_cloudwatch_alarm ? 1 : 0

  name = "taskflow-alerts"

  tags = {
    Name = "taskflow-alerts"
  }
}

# SNS subscription for email alerts
resource "aws_sns_topic_subscription" "email" {
  count = var.enable_cloudwatch_alarm && var.alarm_email != "" ? 1 : 0

  topic_arn = aws_sns_topic.alerts[0].arn
  protocol  = "email"
  endpoint  = var.alarm_email
}
