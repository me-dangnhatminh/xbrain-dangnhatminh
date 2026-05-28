data "aws_caller_identity" "current" {}

# -----------------------------------------------------------------------------
# VECTOR STORE — Amazon S3 Vectors (thay thế OpenSearch Serverless)
# Chi phí gần $0 ở scale hackathon, so với ~$13/ngày của OpenSearch Serverless
# -----------------------------------------------------------------------------

# Bucket S3 riêng để lưu vector embeddings (KHÔNG phải bucket file PDF)
resource "aws_s3vectors_vector_bucket" "kb_vectors" {
  vector_bucket_name = "${var.application}-ai-kb-vectors"
}

# Vector Index bên trong bucket — Bedrock KB sẽ write embeddings vào đây
resource "aws_s3vectors_index" "kb_index" {
  vector_bucket_name = aws_s3vectors_vector_bucket.kb_vectors.vector_bucket_name
  index_name         = "${var.application}-ai-kb-index"

  data_type       = "float32"
  dimension       = 1024 # Titan Embed Text v2 output dimension
  distance_metric = "cosine"

  metadata_configuration {
    non_filterable_metadata_keys = [
      "AMAZON_BEDROCK_TEXT",
      "AMAZON_BEDROCK_METADATA"
    ]
  }
}

# -----------------------------------------------------------------------------
# IAM Role for Bedrock Knowledge Base
# -----------------------------------------------------------------------------

resource "aws_iam_role" "bedrock_kb_role" {
  name = "${var.application}-ai-bedrock-kb-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "bedrock.amazonaws.com" }
      Action    = "sts:AssumeRole"
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = data.aws_caller_identity.current.account_id
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "bedrock_kb_policy" {
  name = "${var.application}-ai-bedrock-kb-policy"
  role = aws_iam_role.bedrock_kb_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Quyen tao embeddings bang Titan va parse bang Claude 3 Haiku
      {
        Effect   = "Allow"
        Action   = ["bedrock:InvokeModel"]
        Resource = [
          "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v2:0",
          "arn:aws:bedrock:*::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
          "arn:aws:bedrock:*:${data.aws_caller_identity.current.account_id}:inference-profile/*"
        ]
      },
      # Quyen doc thong tin model va inference profile de validate
      {
        Effect   = "Allow"
        Action   = [
          "bedrock:GetInferenceProfile",
          "bedrock:GetFoundationModel"
        ]
        Resource = "*"
      },
      # Quyền đọc file PDF từ S3 data bucket (để ingestion)
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:ListBucket"]
        Resource = [aws_s3_bucket.app_data.arn, "${aws_s3_bucket.app_data.arn}/*"]
      },
      # Quyền đọc/ghi vào S3 Vectors bucket (để lưu/query embeddings)
      {
        Effect = "Allow"
        Action = [
          "s3vectors:PutVectors",
          "s3vectors:GetVectors",
          "s3vectors:DeleteVectors",
          "s3vectors:QueryVectors",
          "s3vectors:ListVectors",
        ]
        Resource = [
          aws_s3vectors_vector_bucket.kb_vectors.vector_bucket_arn,
          "${aws_s3vectors_vector_bucket.kb_vectors.vector_bucket_arn}/*",
          aws_s3vectors_index.kb_index.index_arn,
          "${aws_s3vectors_index.kb_index.index_arn}/*",
        ]
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# Bedrock Knowledge Base — dùng S3 Vectors làm vector store
# -----------------------------------------------------------------------------

resource "aws_bedrockagent_knowledge_base" "app_kb" {
  name     = "${var.application}-ai-kb"
  role_arn = aws_iam_role.bedrock_kb_role.arn

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"
    }
  }

  storage_configuration {
    type = "S3_VECTORS"
    s3_vectors_configuration {
      vector_bucket_arn = aws_s3vectors_vector_bucket.kb_vectors.vector_bucket_arn
      index_name        = aws_s3vectors_index.kb_index.index_name
    }
  }

  depends_on = [
    aws_iam_role_policy.bedrock_kb_policy,
    aws_s3vectors_index.kb_index,
  ]
}

# -----------------------------------------------------------------------------
# Bedrock Data Source — S3 bucket chứa file PDF (không đổi)
# -----------------------------------------------------------------------------

resource "aws_bedrockagent_data_source" "app_ds" {
  name                 = "${var.application}-ai-s3-datasource"
  knowledge_base_id    = aws_bedrockagent_knowledge_base.app_kb.id
  data_deletion_policy = "RETAIN"

  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn = aws_s3_bucket.app_data.arn
    }
  }

  vector_ingestion_configuration {
    parsing_configuration {
      parsing_strategy = "BEDROCK_FOUNDATION_MODEL"
      bedrock_foundation_model_configuration {
        model_arn = "arn:aws:bedrock:us-east-1:${data.aws_caller_identity.current.account_id}:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0"
      }
    }

    chunking_configuration {
      chunking_strategy = "FIXED_SIZE"
      fixed_size_chunking_configuration {
        max_tokens         = 512
        overlap_percentage = 20
      }
    }
  }
}
