terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Data source for AWS credentials
data "aws_caller_identity" "current" {}

# S3 bucket for knowledge base documents
resource "aws_s3_bucket" "knowledge_base" {
  bucket = "geekbrain-kb-${var.environment}"
  
  tags = {
    Name        = "GeekBrain Knowledge Base"
    Environment = var.environment
    Project     = "W4-GeekBrain-AI"
  }
}

# Enable versioning
resource "aws_s3_bucket_versioning" "knowledge_base" {
  bucket = aws_s3_bucket.knowledge_base.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "knowledge_base" {
  bucket = aws_s3_bucket.knowledge_base.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "knowledge_base" {
  bucket = aws_s3_bucket.knowledge_base.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Upload knowledge base documents
resource "aws_s3_object" "kb_documents" {
  for_each = fileset("${path.module}/../data_package/knowledge_base", "*.md")
  
  bucket       = aws_s3_bucket.knowledge_base.id
  key          = "knowledge_base/${each.value}"
  source       = "${path.module}/../data_package/knowledge_base/${each.value}"
  etag         = filemd5("${path.module}/../data_package/knowledge_base/${each.value}")
  content_type = "text/markdown"
}

# ============================================================================
# OpenSearch Serverless Collection for Vector Store
# ============================================================================

# Encryption policy for OpenSearch Serverless
resource "aws_opensearchserverless_security_policy" "kb_encryption" {
  name = "geekbrain-kb-encryption-${var.environment}"
  type = "encryption"
  
  policy = jsonencode({
    Rules = [
      {
        Resource = [
          "collection/geekbrain-kb-${var.environment}"
        ]
        ResourceType = "collection"
      }
    ]
    AWSOwnedKey = true
  })
}

# Network policy for OpenSearch Serverless
resource "aws_opensearchserverless_security_policy" "kb_network" {
  name = "geekbrain-kb-network-${var.environment}"
  type = "network"
  
  policy = jsonencode([
    {
      Rules = [
        {
          Resource = [
            "collection/geekbrain-kb-${var.environment}"
          ]
          ResourceType = "collection"
        }
      ]
      AllowFromPublic = true
    }
  ])
}

# Data access policy for OpenSearch Serverless
resource "aws_opensearchserverless_access_policy" "kb_data_access" {
  name = "geekbrain-kb-access-${var.environment}"
  type = "data"
  
  policy = jsonencode([
    {
      Rules = [
        {
          Resource = [
            "collection/geekbrain-kb-${var.environment}"
          ]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:DeleteCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
          ResourceType = "collection"
        },
        {
          Resource = [
            "index/geekbrain-kb-${var.environment}/*"
          ]
          Permission = [
            "aoss:CreateIndex",
            "aoss:DeleteIndex",
            "aoss:UpdateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
          ]
          ResourceType = "index"
        }
      ]
      Principal = [
        aws_iam_role.bedrock_kb_role.arn,
        data.aws_caller_identity.current.arn
      ]
    }
  ])
}

# OpenSearch Serverless Collection
resource "aws_opensearchserverless_collection" "kb_vector_store" {
  name = "geekbrain-kb-${var.environment}"
  type = "VECTORSEARCH"
  
  depends_on = [
    aws_opensearchserverless_security_policy.kb_encryption,
    aws_opensearchserverless_security_policy.kb_network
  ]
  
  tags = {
    Name        = "GeekBrain KB Vector Store"
    Environment = var.environment
    Project     = "W4-GeekBrain-AI"
  }
}

# Wait for collection to be fully active
resource "time_sleep" "wait_for_collection" {
  depends_on = [
    aws_opensearchserverless_collection.kb_vector_store,
    aws_opensearchserverless_access_policy.kb_data_access
  ]
  
  create_duration = "120s"
}

# Note: OpenSearch index must be created manually before Bedrock KB
# Run: bash create_index.sh after collection is created
# Or use the AWS Console to create the index

# ============================================================================
# IAM Roles and Policies for Bedrock Knowledge Base
# ============================================================================

# IAM role for Bedrock Knowledge Base
resource "aws_iam_role" "bedrock_kb_role" {
  name = "geekbrain-bedrock-kb-role-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
          ArnLike = {
            "aws:SourceArn" = "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:knowledge-base/*"
          }
        }
      }
    ]
  })
  
  tags = {
    Name        = "Bedrock KB Role"
    Environment = var.environment
    Project     = "W4-GeekBrain-AI"
  }
}

# IAM policy for S3 access
resource "aws_iam_role_policy" "bedrock_kb_s3_policy" {
  name = "s3-access"
  role = aws_iam_role.bedrock_kb_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.knowledge_base.arn,
          "${aws_s3_bucket.knowledge_base.arn}/*"
        ]
        Condition = {
          StringEquals = {
            "aws:PrincipalAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
}

# IAM policy for OpenSearch Serverless access
resource "aws_iam_role_policy" "bedrock_kb_aoss_policy" {
  name = "aoss-access"
  role = aws_iam_role.bedrock_kb_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "aoss:APIAccessAll"
        ]
        Resource = [
          aws_opensearchserverless_collection.kb_vector_store.arn
        ]
      }
    ]
  })
}

# IAM policy for Bedrock model access (for embeddings)
resource "aws_iam_role_policy" "bedrock_kb_model_policy" {
  name = "bedrock-model-access"
  role = aws_iam_role.bedrock_kb_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v2:0"
        ]
      }
    ]
  })
}

# ============================================================================
# Bedrock Knowledge Base
# ============================================================================

resource "aws_bedrockagent_knowledge_base" "geekbrain_kb" {
  name     = "geekbrain-kb-${var.environment}"
  role_arn = aws_iam_role.bedrock_kb_role.arn
  
  description = "Knowledge base for GeekBrain fintech startup documentation"
  
  knowledge_base_configuration {
    type = "VECTOR"
    
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v2:0"
    }
  }
  
  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.kb_vector_store.arn
      vector_index_name = "geekbrain-kb-index"
      
      field_mapping {
        vector_field   = "embedding"
        text_field     = "text"
        metadata_field = "metadata"
      }
    }
  }
  
  depends_on = [
    aws_iam_role_policy.bedrock_kb_s3_policy,
    aws_iam_role_policy.bedrock_kb_aoss_policy,
    aws_iam_role_policy.bedrock_kb_model_policy,
    aws_opensearchserverless_access_policy.kb_data_access,
    time_sleep.wait_for_collection
  ]
  
  tags = {
    Name        = "GeekBrain Knowledge Base"
    Environment = var.environment
    Project     = "W4-GeekBrain-AI"
  }
}

# ============================================================================
# Bedrock Knowledge Base Data Source
# ============================================================================

resource "aws_bedrockagent_data_source" "kb_s3_source" {
  name              = "geekbrain-s3-docs"
  knowledge_base_id = aws_bedrockagent_knowledge_base.geekbrain_kb.id
  
  description = "S3 data source containing 36 markdown documents"
  
  data_source_configuration {
    type = "S3"
    
    s3_configuration {
      bucket_arn = aws_s3_bucket.knowledge_base.arn
      
      inclusion_prefixes = ["knowledge_base/"]
    }
  }
  
  vector_ingestion_configuration {
    chunking_configuration {
      chunking_strategy = "FIXED_SIZE"
      
      fixed_size_chunking_configuration {
        max_tokens         = 300
        overlap_percentage = 20
      }
    }
  }
  
  depends_on = [
    aws_s3_object.kb_documents
  ]
}
