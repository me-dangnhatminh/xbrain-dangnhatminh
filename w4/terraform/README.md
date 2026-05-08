# Terraform Infrastructure cho W4 GeekBrain AI System

## Tổng quan

Terraform configuration này tạo toàn bộ AWS infrastructure cho GeekBrain AI System.

### Components

**Phase 1: S3 và Document Upload (Task 5.1)** ✓
- S3 bucket với versioning và encryption
- 36 markdown documents được upload tự động

**Phase 2: Bedrock Knowledge Base (Task 5.2)** ✓
- OpenSearch Serverless Collection (vector store)
- OpenSearch Index với knn_vector mapping (tạo manual)
- Bedrock Knowledge Base với S3 data source
- Embedding Model: Amazon Titan Embeddings v2
- Chunking: 300 tokens, 20% overlap
- IAM Roles với least-privilege permissions

## Yêu cầu

1. **Terraform** >= 1.0
2. **AWS CLI** đã cấu hình credentials
3. **Python 3** với **boto3** và **urllib3** HOẶC **awscurl**
4. AWS account với quyền:
   - Amazon Bedrock (Titan Embeddings v2 enabled)
   - OpenSearch Serverless
   - S3, IAM

## Deployment - 3 Bước

### Bước 1: Tạo OpenSearch Collection

```bash
cd w4/terraform
terraform init

# Tạo collection và IAM roles (10-15 phút)
terraform apply -target=aws_opensearchserverless_collection.kb_vector_store \
                -target=aws_opensearchserverless_security_policy.kb_encryption \
                -target=aws_opensearchserverless_security_policy.kb_network \
                -target=aws_opensearchserverless_access_policy.kb_data_access \
                -target=aws_iam_role.bedrock_kb_role \
                -target=aws_iam_role_policy.bedrock_kb_s3_policy \
                -target=aws_iam_role_policy.bedrock_kb_aoss_policy \
                -target=time_sleep.wait_for_collection
```

### Bước 2: Tạo OpenSearch Index (Manual)

Sau khi collection active, chạy:

```bash
bash create_index_manual.sh
```

**Nếu thiếu dependencies**:
```bash
# Option 1: awscurl
pip install awscurl

# Option 2: boto3 + urllib3
pip install boto3 urllib3
```

### Bước 3: Tạo Bedrock Knowledge Base

```bash
terraform apply
```

### Bước 4: Verify

```bash
terraform output -json setup_summary | jq '.'
```

### Bước 5: Trigger Ingestion (Task 5.3)

```bash
bash trigger_kb_sync.sh
```

## Tại sao phải 3 bước?

1. **OpenSearch collection** mất 10-15 phút để active
2. **Index** phải tồn tại trước khi tạo Bedrock KB
3. Terraform không thể đảm bảo thứ tự với external dependencies

Cách này đảm bảo **không có lỗi** trong môi trường mới.

## Configuration Variables

File `terraform.tfvars`:

```hcl
aws_region  = "us-east-1"
environment = "dev"
```

## Outputs

- `knowledge_base_id` - Dùng cho Bedrock Retrieve API
- `opensearch_collection_endpoint` - Vector store endpoint
- `s3_bucket_name` - Bucket chứa documents
- `setup_summary` - Tổng hợp setup

## Kiến trúc

```
S3 Bucket (geekbrain-kb-{env})
  └── knowledge_base/*.md (36 files)
          ↓
Bedrock Knowledge Base
  ├── Embedding: Titan Embeddings v2
  ├── Chunking: 300 tokens, 20% overlap
  └── Vector Store: OpenSearch Serverless
      └── Collection: geekbrain-kb-{env}
          └── Index: geekbrain-kb-index
```

## Troubleshooting

### Lỗi: "no such index"

Chạy `bash create_index_manual.sh` trước khi `terraform apply` lần cuối.

### Lỗi: boto3/urllib3 not found

```bash
pip install boto3 urllib3
```

### Lỗi: Collection not active

Đợi 5 phút sau bước 1, rồi chạy bước 2.

### Lỗi: Bedrock model not found

```bash
aws bedrock list-foundation-models \
  --region us-east-1 \
  --query 'modelSummaries[?contains(modelId, `titan-embed`)]'
```

## Clean Up

```bash
terraform destroy
```

## Chi phí ước tính

- OpenSearch Serverless: ~$350/tháng
- Bedrock Embeddings: ~$0.01 (một lần)
- S3: Rất nhỏ

**Tổng**: $350-400/tháng

**Mẹo**: `terraform destroy` khi không dùng.

## Files

- `main.tf` - Infrastructure configuration
- `variables.tf` - Input variables
- `outputs.tf` - Output values
- `create_index_manual.sh` - Script tạo index (manual)
- `trigger_kb_sync.sh` - Script trigger ingestion
- `README.md` - File này
- `QUICKSTART.md` - Hướng dẫn nhanh
- `TASK_5.2_GUIDE.md` - Chi tiết task 5.2

## Next Steps

1. ✓ Task 5.1: S3 và documents
2. ✓ Task 5.2: Bedrock KB
3. → Task 5.3: Test retrieval
4. → Task 6: Implement RAG Pipeline
