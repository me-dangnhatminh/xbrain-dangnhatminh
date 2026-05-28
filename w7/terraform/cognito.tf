# =============================================================================
# COGNITO — User Pool & App Client cho AI
# =============================================================================
resource "aws_cognito_user_pool" "app_pool" {
  name = "${var.application}-user-pool"

  # Cho phép đăng nhập bằng username hoặc email
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  # Chính sách mật khẩu
  password_policy {
    minimum_length                   = 8
    require_uppercase                = true
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = false
    temporary_password_validity_days = 7
  }

  mfa_configuration = "OFF"

  schema {
    name                = "workspace_id"
    attribute_data_type = "String"
    mutable             = true
    required            = false

    string_attribute_constraints {
      min_length = 0
      max_length = 256
    }
  }

  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  admin_create_user_config {
    allow_admin_create_user_only = false
  }

  tags = {
    Name = "${var.application}-user-pool"
  }
}

# -----------------------------------------------------------------------------
resource "aws_cognito_user_pool_domain" "app_domain" {
  domain       = "${var.application}-ai-${data.aws_caller_identity.current.account_id}"
  user_pool_id = aws_cognito_user_pool.app_pool.id
}
resource "aws_cognito_user_pool_client" "frontend" {
  name         = "${var.application}-frontend-client"
  user_pool_id = aws_cognito_user_pool.app_pool.id

  # SPA không nên có client secret
  generate_secret = false

  # Các OAuth flows hỗ trợ
  allowed_oauth_flows                  = ["code", "implicit"]
  allowed_oauth_scopes                 = ["email", "openid", "profile"]
  allowed_oauth_flows_user_pool_client = true

  # Callback và logout URLs — cập nhật khi deploy lên domain thật
  callback_urls = [
    "http://localhost:5173",
    "https://${aws_cloudfront_distribution.frontend_distribution.domain_name}",
  ]
  logout_urls = [
    "http://localhost:5173",
    "https://${aws_cloudfront_distribution.frontend_distribution.domain_name}",
  ]

  # Supported identity providers
  supported_identity_providers = ["COGNITO"]

  # Token expiry (giây)
  access_token_validity  = 60 # 1 giờ
  id_token_validity      = 60 # 1 giờ
  refresh_token_validity = 30 # 30 ngày

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }

  # Không cho phép user-password flow qua SRP từ server — chỉ dùng USER_SRP_AUTH
  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_PASSWORD_AUTH", # Cần cho amazon-cognito-identity-js SRP flow
  ]

  # Các attribute mà client được đọc/ghi
  read_attributes  = ["email", "custom:workspace_id"]
  write_attributes = ["email", "custom:workspace_id"]

  prevent_user_existence_errors = "ENABLED"
}

# -----------------------------------------------------------------------------
# 4. Cognito Authorizer cho API Gateway
# -----------------------------------------------------------------------------
resource "aws_api_gateway_authorizer" "cognito" {
  name            = "${var.application}-cognito-authorizer"
  rest_api_id     = aws_api_gateway_rest_api.app.id
  type            = "COGNITO_USER_POOLS"
  identity_source = "method.request.header.Authorization"
  provider_arns   = [aws_cognito_user_pool.app_pool.arn]
}



data "aws_region" "current" {}

# -----------------------------------------------------------------------------
# 6. Test Accounts (Tạo sẵn một vài tài khoản để test)
# -----------------------------------------------------------------------------
locals {
  test_users = {
    "company_a@example.com" = { password = "Dochub@2025!" }
    "company_b@example.com" = { password = "Dochub@2025!" }
  }
}

resource "aws_cognito_user" "test_users" {
  for_each       = local.test_users
  user_pool_id   = aws_cognito_user_pool.app_pool.id
  username       = each.key
  password       = each.value.password
  message_action = "SUPPRESS"

  attributes = {
    email                 = each.key
    email_verified        = true
    "custom:workspace_id" = each.value.workspace_id
  }
}

resource "null_resource" "set_permanent_passwords" {
  for_each   = local.test_users
  depends_on = [aws_cognito_user.test_users]

  provisioner "local-exec" {
    command = "aws cognito-idp admin-set-user-password --region ${data.aws_region.current.region} --user-pool-id ${aws_cognito_user_pool.app_pool.id} --username ${each.key} --password '${each.value.password}' --permanent"
  }
}
