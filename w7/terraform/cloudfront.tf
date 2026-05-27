# -----------------------------------------------------------------------------
# 7. FRONTEND HOSTING (S3 Static Website + CloudFront)
# -----------------------------------------------------------------------------

# Bucket chứa Frontend đã build (HTML/CSS/JS)
resource "aws_s3_bucket" "frontend_bucket" {
  bucket_prefix = "dochub-frontend-"
  force_destroy = true
}

# Cấu hình chặn Public Access cho S3 (Bảo mật theo chuẩn mới, chỉ CloudFront mới được đọc)
resource "aws_s3_bucket_public_access_block" "frontend_block" {
  bucket                  = aws_s3_bucket.frontend_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# OAC (Origin Access Control) để CloudFront truy cập S3 an toàn
resource "aws_cloudfront_origin_access_control" "frontend_oac" {
  name                              = "dochub-frontend-oac"
  description                       = "OAC for DocHub Frontend"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# CloudFront Distribution (HTTPS + CDN toàn cầu)
resource "aws_cloudfront_distribution" "frontend_distribution" {
  origin {
    domain_name              = aws_s3_bucket.frontend_bucket.bucket_regional_domain_name
    origin_id                = "S3-DocHub-Frontend"
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend_oac.id
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-DocHub-Frontend"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  # Quan trọng cho ứng dụng React (SPA): chuyển hướng lỗi 404 về index.html
  custom_error_response {
    error_caching_min_ttl = 10
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
  }

  custom_error_response {
    error_caching_min_ttl = 10
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

# S3 Bucket Policy cho phép CloudFront OAC đọc file
resource "aws_s3_bucket_policy" "frontend_policy" {
  bucket = aws_s3_bucket.frontend_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.frontend_bucket.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.frontend_distribution.arn
          }
        }
      }
    ]
  })
}

# --- Output URL ---
output "frontend_url" {
  description = "URL của Frontend (CloudFront HTTPS) - Nhấn vào đây để xem web!"
  value       = "https://${aws_cloudfront_distribution.frontend_distribution.domain_name}"
}
