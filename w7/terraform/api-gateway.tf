# -----------------------------------------------------------------------------
# 5. API GATEWAY (REST API) — Cửa ngõ HTTP cho Frontend gọi Lambda
# -----------------------------------------------------------------------------

resource "aws_api_gateway_rest_api" "app" {
  name        = "${var.application}-api"
  description = "REST API"
}

# --- /workspaces ---
resource "aws_api_gateway_resource" "workspaces" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  parent_id   = aws_api_gateway_rest_api.app.root_resource_id
  path_part   = "workspaces"
}

resource "aws_api_gateway_method" "workspaces_get" {
  rest_api_id   = aws_api_gateway_rest_api.app.id
  resource_id   = aws_api_gateway_resource.workspaces.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_method" "workspaces_post" {
  rest_api_id   = aws_api_gateway_rest_api.app.id
  resource_id   = aws_api_gateway_resource.workspaces.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

# CORS OPTIONS for /workspaces
resource "aws_api_gateway_method" "workspaces_options" {
  rest_api_id   = aws_api_gateway_rest_api.app.id
  resource_id   = aws_api_gateway_resource.workspaces.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "workspaces_options" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  resource_id = aws_api_gateway_resource.workspaces.id
  http_method = aws_api_gateway_method.workspaces_options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "workspaces_options_200" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  resource_id = aws_api_gateway_resource.workspaces.id
  http_method = aws_api_gateway_method.workspaces_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "workspaces_options" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  resource_id = aws_api_gateway_resource.workspaces.id
  http_method = aws_api_gateway_method.workspaces_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }

  depends_on = [aws_api_gateway_integration.workspaces_options]
}

# --- /documents ---
resource "aws_api_gateway_resource" "documents" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  parent_id   = aws_api_gateway_rest_api.app.root_resource_id
  path_part   = "documents"
}

resource "aws_api_gateway_method" "documents_get" {
  rest_api_id   = aws_api_gateway_rest_api.app.id
  resource_id   = aws_api_gateway_resource.documents.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

# CORS OPTIONS for /documents
resource "aws_api_gateway_method" "documents_options" {
  rest_api_id   = aws_api_gateway_rest_api.app.id
  resource_id   = aws_api_gateway_resource.documents.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "documents_options" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  resource_id = aws_api_gateway_resource.documents.id
  http_method = aws_api_gateway_method.documents_options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "documents_options_200" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  resource_id = aws_api_gateway_resource.documents.id
  http_method = aws_api_gateway_method.documents_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "documents_options" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  resource_id = aws_api_gateway_resource.documents.id
  http_method = aws_api_gateway_method.documents_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }

  depends_on = [aws_api_gateway_integration.documents_options]
}

# --- /documents/upload ---
resource "aws_api_gateway_resource" "documents_upload" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  parent_id   = aws_api_gateway_resource.documents.id
  path_part   = "upload"
}

resource "aws_api_gateway_method" "documents_upload_post" {
  rest_api_id   = aws_api_gateway_rest_api.app.id
  resource_id   = aws_api_gateway_resource.documents_upload.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

# CORS OPTIONS for /documents/upload
resource "aws_api_gateway_method" "documents_upload_options" {
  rest_api_id   = aws_api_gateway_rest_api.app.id
  resource_id   = aws_api_gateway_resource.documents_upload.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "documents_upload_options" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  resource_id = aws_api_gateway_resource.documents_upload.id
  http_method = aws_api_gateway_method.documents_upload_options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "documents_upload_options_200" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  resource_id = aws_api_gateway_resource.documents_upload.id
  http_method = aws_api_gateway_method.documents_upload_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "documents_upload_options" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  resource_id = aws_api_gateway_resource.documents_upload.id
  http_method = aws_api_gateway_method.documents_upload_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }

  depends_on = [aws_api_gateway_integration.documents_upload_options]
}

# --- /chat (Proxy to ECS ALB) ---
resource "aws_api_gateway_resource" "chat" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  parent_id   = aws_api_gateway_rest_api.app.root_resource_id
  path_part   = "chat"
}

resource "aws_api_gateway_method" "chat_post" {
  rest_api_id   = aws_api_gateway_rest_api.app.id
  resource_id   = aws_api_gateway_resource.chat.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.header.Authorization" = true
  }
}

# CORS OPTIONS for /chat
resource "aws_api_gateway_method" "chat_options" {
  rest_api_id   = aws_api_gateway_rest_api.app.id
  resource_id   = aws_api_gateway_resource.chat.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "chat_options" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  resource_id = aws_api_gateway_resource.chat.id
  http_method = aws_api_gateway_method.chat_options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "chat_options_200" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  resource_id = aws_api_gateway_resource.chat.id
  http_method = aws_api_gateway_method.chat_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "chat_options" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  resource_id = aws_api_gateway_resource.chat.id
  http_method = aws_api_gateway_method.chat_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }

  depends_on = [aws_api_gateway_integration.chat_options]
}

# --- Lambda Integrations ---
resource "aws_api_gateway_integration" "workspaces_get" {
  rest_api_id             = aws_api_gateway_rest_api.app.id
  resource_id             = aws_api_gateway_resource.workspaces.id
  http_method             = aws_api_gateway_method.workspaces_get.http_method
  integration_http_method = "POST" # Lambda luôn nhận POST từ API Gateway
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

resource "aws_api_gateway_integration" "workspaces_post" {
  rest_api_id             = aws_api_gateway_rest_api.app.id
  resource_id             = aws_api_gateway_resource.workspaces.id
  http_method             = aws_api_gateway_method.workspaces_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

resource "aws_api_gateway_integration" "documents_get" {
  rest_api_id             = aws_api_gateway_rest_api.app.id
  resource_id             = aws_api_gateway_resource.documents.id
  http_method             = aws_api_gateway_method.documents_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

resource "aws_api_gateway_integration" "documents_upload_post" {
  rest_api_id             = aws_api_gateway_rest_api.app.id
  resource_id             = aws_api_gateway_resource.documents_upload.id
  http_method             = aws_api_gateway_method.documents_upload_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

resource "aws_api_gateway_integration" "chat_post" {
  rest_api_id             = aws_api_gateway_rest_api.app.id
  resource_id             = aws_api_gateway_resource.chat.id
  http_method             = aws_api_gateway_method.chat_post.http_method
  integration_http_method = "POST"
  type                    = "HTTP_PROXY"
  uri                     = "http://${aws_lb.ecs_alb.dns_name}/chat"

  request_parameters = {
    "integration.request.header.Authorization" = "method.request.header.Authorization"
  }
}

# --- Permission: cho API Gateway gọi Lambda ---
resource "aws_lambda_permission" "api_gw_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.app.execution_arn}/*/*"
}

# =============================================================================
# NEW CRUD ROUTES
# =============================================================================

# --- /workspaces/{workspace_id} ---
resource "aws_api_gateway_resource" "workspace_item" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  parent_id   = aws_api_gateway_resource.workspaces.id
  path_part   = "{workspace_id}"
}

resource "aws_api_gateway_method" "workspace_delete" {
  rest_api_id   = aws_api_gateway_rest_api.app.id
  resource_id   = aws_api_gateway_resource.workspace_item.id
  http_method   = "DELETE"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "workspace_delete" {
  rest_api_id             = aws_api_gateway_rest_api.app.id
  resource_id             = aws_api_gateway_resource.workspace_item.id
  http_method             = aws_api_gateway_method.workspace_delete.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

resource "aws_api_gateway_method" "workspace_item_options" {
  rest_api_id   = aws_api_gateway_rest_api.app.id
  resource_id   = aws_api_gateway_resource.workspace_item.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "workspace_item_options" {
  rest_api_id       = aws_api_gateway_rest_api.app.id
  resource_id       = aws_api_gateway_resource.workspace_item.id
  http_method       = aws_api_gateway_method.workspace_item_options.http_method
  type              = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}

resource "aws_api_gateway_method_response" "workspace_item_options_200" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  resource_id = aws_api_gateway_resource.workspace_item.id
  http_method = aws_api_gateway_method.workspace_item_options.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "workspace_item_options" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  resource_id = aws_api_gateway_resource.workspace_item.id
  http_method = aws_api_gateway_method.workspace_item_options.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'DELETE,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
  depends_on = [aws_api_gateway_integration.workspace_item_options]
}

# --- /documents/{document_id} ---
resource "aws_api_gateway_resource" "document_item" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  parent_id   = aws_api_gateway_resource.documents.id
  path_part   = "{document_id}"
}

resource "aws_api_gateway_method" "document_get" {
  rest_api_id   = aws_api_gateway_rest_api.app.id
  resource_id   = aws_api_gateway_resource.document_item.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "document_get" {
  rest_api_id             = aws_api_gateway_rest_api.app.id
  resource_id             = aws_api_gateway_resource.document_item.id
  http_method             = aws_api_gateway_method.document_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

resource "aws_api_gateway_method" "document_delete" {
  rest_api_id   = aws_api_gateway_rest_api.app.id
  resource_id   = aws_api_gateway_resource.document_item.id
  http_method   = "DELETE"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "document_delete" {
  rest_api_id             = aws_api_gateway_rest_api.app.id
  resource_id             = aws_api_gateway_resource.document_item.id
  http_method             = aws_api_gateway_method.document_delete.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

resource "aws_api_gateway_method" "document_item_options" {
  rest_api_id   = aws_api_gateway_rest_api.app.id
  resource_id   = aws_api_gateway_resource.document_item.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "document_item_options" {
  rest_api_id       = aws_api_gateway_rest_api.app.id
  resource_id       = aws_api_gateway_resource.document_item.id
  http_method       = aws_api_gateway_method.document_item_options.http_method
  type              = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}

resource "aws_api_gateway_method_response" "document_item_options_200" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  resource_id = aws_api_gateway_resource.document_item.id
  http_method = aws_api_gateway_method.document_item_options.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "document_item_options" {
  rest_api_id = aws_api_gateway_rest_api.app.id
  resource_id = aws_api_gateway_resource.document_item.id
  http_method = aws_api_gateway_method.document_item_options.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,DELETE,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
  depends_on = [aws_api_gateway_integration.document_item_options]
}

# --- Deploy ---
resource "aws_api_gateway_deployment" "app_api" {
  rest_api_id = aws_api_gateway_rest_api.app.id

  depends_on = [
    # Original routes
    aws_api_gateway_integration.workspaces_get,
    aws_api_gateway_integration.workspaces_post,
    aws_api_gateway_integration.documents_get,
    aws_api_gateway_integration.documents_upload_post,
    aws_api_gateway_integration.chat_post,
    aws_api_gateway_integration_response.workspaces_options,
    aws_api_gateway_integration_response.documents_options,
    aws_api_gateway_integration_response.documents_upload_options,
    aws_api_gateway_integration_response.chat_options,
    # New CRUD routes
    aws_api_gateway_integration.workspace_delete,
    aws_api_gateway_integration.document_get,
    aws_api_gateway_integration.document_delete,
    aws_api_gateway_integration_response.workspace_item_options,
    aws_api_gateway_integration_response.document_item_options,
    aws_api_gateway_authorizer.cognito,
  ]

  # Force re-deploy on changes (including authorizer)
  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.workspaces,
      aws_api_gateway_resource.workspace_item,
      aws_api_gateway_resource.documents,
      aws_api_gateway_resource.document_item,
      aws_api_gateway_resource.documents_upload,
      aws_api_gateway_resource.chat,
      aws_api_gateway_method.workspaces_get,
      aws_api_gateway_method.workspaces_post,
      aws_api_gateway_method.workspace_delete,
      aws_api_gateway_method.documents_get,
      aws_api_gateway_method.documents_upload_post,
      aws_api_gateway_method.document_get,
      aws_api_gateway_method.document_delete,
      aws_api_gateway_method.chat_post,
      aws_api_gateway_authorizer.cognito,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.app_api.id
  rest_api_id   = aws_api_gateway_rest_api.app.id
  stage_name    = "prod"
}

