# =============================================================================
# OBSERVABILITY — Dashboard, Metrics, Alarms, Log Insights
# =============================================================================

# 1. SNS Topic for Alerts
resource "aws_sns_topic" "alerts" {
  name = "${var.application}-alerts"
}

resource "aws_sns_topic_subscription" "alert_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# 2. CloudWatch Alarms

# ECS CPU High Alarm
resource "aws_cloudwatch_metric_alarm" "ecs_cpu_high" {
  alarm_name          = "${var.application}-ecs-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "ECS CPU > 80% for 10 minutes"

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.ai_backend.name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

# ECS Memory High Alarm
resource "aws_cloudwatch_metric_alarm" "ecs_memory_high" {
  alarm_name          = "${var.application}-ecs-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "ECS Memory > 80% for 10 minutes"

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.ai_backend.name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

# API Gateway 5XX Errors Alarm
resource "aws_cloudwatch_metric_alarm" "api_5xx_errors" {
  alarm_name          = "${var.application}-api-5xx-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "API Gateway 5XX errors > 5 in 5 minutes"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = aws_api_gateway_rest_api.app.name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

# DynamoDB Throttled Requests Alarm (Workspaces)
resource "aws_cloudwatch_metric_alarm" "dynamodb_workspaces_throttle" {
  alarm_name          = "${var.application}-dynamodb-workspaces-throttled"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ThrottledRequests"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "DynamoDB throttled requests detected on workspaces table"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.workspaces.name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}

# 3. CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.application}-ops-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      # Row 1: Custom Metrics (Chat)
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "AI Chat Invocations (Custom Metric)"
          view   = "timeSeries"
          region = var.region
          metrics = [
            ["DocHub/Application", "ChatInvocations",
            { label = "Queries", stat = "Sum", period = 60, color = "#4CAF50" }]
          ]
          yAxis    = { left = { label = "count", min = 0 } }
          liveData = true
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "AI Chat Latency (Custom Metric)"
          view   = "timeSeries"
          region = var.region
          metrics = [
            ["DocHub/Application", "ChatLatency",
            { label = "Latency (ms)", stat = "Average", period = 60, color = "#2196F3" }]
          ]
          yAxis    = { left = { label = "ms", min = 0 } }
          liveData = true
        }
      },
      # Row 2: Standard ECS Metrics
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title  = "ECS CPU & Memory Utilization"
          view   = "timeSeries"
          region = var.region
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ClusterName", aws_ecs_cluster.main.name, "ServiceName", aws_ecs_service.ai_backend.name, { label = "CPU %", stat = "Average", period = 60, color = "#FF9800" }],
            ["AWS/ECS", "MemoryUtilization", "ClusterName", aws_ecs_cluster.main.name, "ServiceName", aws_ecs_service.ai_backend.name, { label = "Memory %", stat = "Average", period = 60, color = "#9C27B0" }]
          ]
          annotations = {
            horizontal = [{ value = 80, label = "Alarm threshold", color = "#FF5252" }]
          }
          yAxis = { left = { label = "%", min = 0, max = 100 } }
        }
      },
      # Row 2: API Gateway Metrics
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          title  = "API Gateway Errors (4xx / 5xx)"
          view   = "timeSeries"
          region = var.region
          metrics = [
            ["AWS/ApiGateway", "5XXError", "ApiName", aws_api_gateway_rest_api.app.name, { label = "5xx Errors", stat = "Sum", period = 300, color = "#F44336" }],
            ["AWS/ApiGateway", "4XXError", "ApiName", aws_api_gateway_rest_api.app.name, { label = "4xx Errors", stat = "Sum", period = 300, color = "#FF9800" }]
          ]
          yAxis = { left = { label = "count", min = 0 } }
        }
      },
      # Row 3: Active Alarms
      {
        type   = "alarm"
        x      = 0
        y      = 12
        width  = 24
        height = 6
        properties = {
          title = "Active CloudWatch Alarms"
          alarms = [
            aws_cloudwatch_metric_alarm.ecs_cpu_high.arn,
            aws_cloudwatch_metric_alarm.ecs_memory_high.arn,
            aws_cloudwatch_metric_alarm.api_5xx_errors.arn,
            aws_cloudwatch_metric_alarm.dynamodb_workspaces_throttle.arn
          ]
        }
      }
    ]
  })
}

# 4. CloudWatch Log Insights Saved Query
resource "aws_cloudwatch_query_definition" "ecs_errors" {
  name            = "DocHub/Backend-Error-Spikes"
  log_group_names = [aws_cloudwatch_log_group.ecs_logs.name]

  query_string = <<-EOT
    fields @timestamp, @message
    | filter @message like /ERROR|Exception|5[0-9][0-9]/
    | stats count(*) as error_count by bin(5m)
    | sort @timestamp desc
    | limit 20
  EOT
}
