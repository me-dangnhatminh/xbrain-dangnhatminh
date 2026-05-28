# =============================================================================
# WAF v2 for CloudFront (Frontend Protection)
# Scope: CLOUDFRONT (must be in us-east-1)
# =============================================================================

resource "aws_wafv2_web_acl" "cloudfront" {
  name        = "${var.application}-waf"
  description = "WAF for CloudFront - Frontend Protection"
  scope       = "CLOUDFRONT"

  default_action {
    allow {}
  }

  # 1. AWS Managed Rule: Amazon IP Reputation List (Chặn bot/IP xấu)
  rule {
    name     = "aws-managed-ip-reputation"
    priority = 1
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesAmazonIpReputationList"
      }
    }
    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.application}-waf-ip-rep"
    }
  }

  # 2. AWS Managed Rule: Core Rule Set (Bảo vệ XSS, LFI/RFI cho frontend)
  rule {
    name     = "aws-managed-common"
    priority = 2
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesCommonRuleSet"
      }
    }
    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.application}-waf-common"
    }
  }

  # 3. Rate limiting: Chống DDoS/Spam request vào Frontend (2000 req/5p)
  rule {
    name     = "rate-limit"
    priority = 3
    action {
      block {}
    }
    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }
    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.application}-waf-rate-limit"
    }
  }

  visibility_config {
    sampled_requests_enabled   = true
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.application}-waf-cf"
  }
}

# =============================================================================
# WAF v2 for API Gateway (Backend & AI Protection)
# Scope: REGIONAL
# =============================================================================
resource "aws_wafv2_web_acl" "apigw" {
  name        = "${var.application}-apigw-waf"
  description = "WAF for API Gateway - Backend and AI Protection"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  # 1. AWS Managed Rule: Known Bad Inputs (Chặn các payload độc hại vào API)
  rule {
    name     = "aws-managed-bad-inputs"
    priority = 1
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
      }
    }
    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.application}-apigw-waf-bad-inputs"
    }
  }

  # 2. Strict Rate limiting cho API: Rất quan trọng để chống bòn rút tiền AWS Bedrock
  # Giới hạn 300 requests / 5 phút (~1 req/giây từ cùng 1 IP)
  rule {
    name     = "api-rate-limit"
    priority = 2
    action {
      block {}
    }
    statement {
      rate_based_statement {
        limit              = 300
        aggregate_key_type = "IP"
      }
    }
    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.application}-apigw-waf-rate-limit"
    }
  }

  visibility_config {
    sampled_requests_enabled   = true
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.application}-apigw-waf"
  }
}

resource "aws_wafv2_web_acl_association" "apigw" {
  resource_arn = aws_api_gateway_stage.prod.arn
  web_acl_arn  = aws_wafv2_web_acl.apigw.arn
}
