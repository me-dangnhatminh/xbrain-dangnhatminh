# -----------------------------------------------------------------------------
# OUTPUTS
# -----------------------------------------------------------------------------

# --- Output URL ---
output "frontend_url" {
  description = "URL của Frontend (CloudFront HTTPS) - Nhấn vào đây để xem web!"
  value       = "https://${aws_cloudfront_distribution.frontend_distribution.domain_name}"
}

# --- Output: URL cho Frontend ---
output "api_gateway_url" {
  description = "Base URL cho Frontend (điền vào VITE_API_URL)"
  value       = aws_api_gateway_stage.prod.invoke_url
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

output "ecr_ai_backend_url" {
  description = "ECR Repository URL cho AI Backend"
  value       = aws_ecr_repository.ai_backend.repository_url
}

