# -----------------------------------------------------------------------------
# EVENT TRIGGERS — S3 → Lambda, EventBridge → Lambda, Scheduled Polling
# -----------------------------------------------------------------------------

# --- S3 Event Notification: Khi file upload xong, gọi event-handler-lambda ---
resource "aws_lambda_permission" "s3_invoke_event_handler" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.event_handler.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.app_data.arn
}

resource "aws_s3_bucket_notification" "app_data_notification" {
  bucket = aws_s3_bucket.app_data.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.event_handler.arn
    events              = ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
  }

  depends_on = [aws_lambda_permission.s3_invoke_event_handler]
}

# --- EventBridge Rule (secondary): Bedrock Ingestion state change ---
resource "aws_cloudwatch_event_rule" "bedrock_ingestion" {
  name        = "${var.application}-bedrock-ingestion-status"
  description = "Capture Bedrock KB ingestion state changes"

  event_pattern = jsonencode({
    source      = ["aws.bedrock"]
    detail-type = ["Knowledge Base Ingestion State Change"]
  })
}

resource "aws_cloudwatch_event_target" "bedrock_to_lambda" {
  rule      = aws_cloudwatch_event_rule.bedrock_ingestion.name
  target_id = "EventHandlerLambda"
  arn       = aws_lambda_function.event_handler.arn
}

resource "aws_lambda_permission" "eventbridge_invoke_event_handler" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.event_handler.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.bedrock_ingestion.arn
}

# --- Scheduled Polling (primary): Check INDEXING docs every 1 minute ---
resource "aws_cloudwatch_event_rule" "ingestion_poller" {
  name                = "${var.application}-ingestion-poller"
  description         = "Poll Bedrock ingestion job status every 1 minute"
  schedule_expression = "rate(1 minute)"
}

resource "aws_cloudwatch_event_target" "poller_to_lambda" {
  rule      = aws_cloudwatch_event_rule.ingestion_poller.name
  target_id = "IngestionPollerLambda"
  arn       = aws_lambda_function.event_handler.arn
}

resource "aws_lambda_permission" "poller_invoke_event_handler" {
  statement_id  = "AllowPollerInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.event_handler.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ingestion_poller.arn
}
