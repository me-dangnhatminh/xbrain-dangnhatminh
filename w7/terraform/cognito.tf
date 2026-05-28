# =============================================================================
# COGNITO — User Pool & App Client cho AI
# =============================================================================

# -----------------------------------------------------------------------------
# 1. User Pool
# -----------------------------------------------------------------------------
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

  # Cấu hình MFA — tắt để đơn giản (bật OPTIONAL hoặc ON cho production)
  mfa_configuration = "OFF"

  # Lưu trữ thuộc tính custom:workspace_id cho Tenant Isolation
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

  # Cấu hình email xác thực (dùng Cognito mặc định — giới hạn 50 email/ngày)
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # Cho phép user tự đăng ký (tắt nếu chỉ admin mới tạo được user)
  admin_create_user_config {
    allow_admin_create_user_only = false
  }

  tags = {
    Name = "${var.application}-user-pool"
  }
}

# -----------------------------------------------------------------------------
# 2. User Pool Domain (dùng cho Hosted UI nếu cần)
# -----------------------------------------------------------------------------
resource "aws_cognito_user_pool_domain" "app_domain" {
  domain       = "${var.application}-ai-${data.aws_caller_identity.current.account_id}"
  user_pool_id = aws_cognito_user_pool.app_pool.id
}


# -----------------------------------------------------------------------------
# 3. App Client — dùng cho Frontend (SPA, không có client secret)
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# 5. Outputs — cần điền vào .env của frontend và backend
# -----------------------------------------------------------------------------
output "cognito_user_pool_id" {
  description = "Cognito User Pool ID — điền vào VITE_COGNITO_USER_POOL_ID và COGNITO_USER_POOL_ID"
  value       = aws_cognito_user_pool.app_pool.id
}

output "cognito_client_id" {
  description = "Cognito App Client ID — điền vào VITE_COGNITO_CLIENT_ID và COGNITO_CLIENT_ID"
  value       = aws_cognito_user_pool_client.frontend.id
}

output "cognito_hosted_ui_url" {
  description = "Hosted UI URL (dùng nếu muốn redirect đến Cognito login page)"
  value       = "https://${aws_cognito_user_pool_domain.app_domain.domain}.auth.${data.aws_region.current.region}.amazoncognito.com"
}

data "aws_region" "current" {}
