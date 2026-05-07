# Task 5.2: Create Bedrock Knowledge Base - Hướng dẫn

## Tổng quan

Task này tạo Bedrock Knowledge Base infrastructure:
- ✓ OpenSearch Serverless collection
- ✓ OpenSearch index với knn_vector mapping
- ✓ Bedrock Knowledge Base với S3 data source
- ✓ Titan Embeddings v2
- ✓ Chunking: 300 tokens, 20% overlap
- ✓ IAM roles và policies

## Yêu cầu

1. ✓ Task 5.1 hoàn thành
2. AWS CLI configured
3. Terraform installed
4. Python 3 với boto3 + urllib3 HOẶC awscurl
5. Bedrock access enabled

## Thực thi - 3 Bước

### Bước 1: Tạo OpenSearch Collection

```bash
cd w4/terraform
terraform init

terraform apply -target=aws_opensearchserverless_collection.kb_vector_store \
                -target=aws_opensearchserverless_security_policy.kb_encryption \
                -target=aws_opensearchserverless_security_policy.kb_network \
                -target=aws_opensearchserverless_access_policy.kb_data_access \
                -target=aws_iam_role.bedrock_kb_role \
                -target=aws_iam_role_policy.bedrock_kb_s3_policy \
                -target=aws_iam_role_policy.bedrock_kb_aoss_policy \
                -target=time_sleep.wait_for_collection
```

**Thời gian**: 10-15 phút

### Bước 2: Tạo Index (Manual)

```bash
bash create_index_manual.sh
```

Script sẽ:
- Lấy endpoint từ terraform
- Tạo index với knn_vector mapping
- Dùng awscurl hoặc Python boto3

**Nếu thiếu dependencies**:
```bash
pip install boto3 urllib3
# hoặc
pip install awscurl
```

### Bước 3: Tạo Bedrock KB

```bash
terraform apply
```

**Thời gian**: 2-3 phút

### Bước 4: Verify

```bash
terraform output -json setup_summary | jq '.'
```

## Những gì được tạo

### 1. OpenSearch Serverless Collection
- Name: `geekbrain-kb-{env}`
- Type: VECTORSEARCH
- Encryption: AWS-owned key

### 2. OpenSearch Index (Manual)
- Name: `geekbrain-kb-index`
- Mapping: knn_vector (1024 dim, hnsw)

### 3. IAM Role
- Name: `geekbrain-bedrock-kb-role-{env}`
- Permissions: S3, OpenSearch, Bedrock

### 4. Bedrock Knowledge Base
- Name: `geekbrain-kb-{env}`
- Embedding: Titan Embeddings v2
- Storage: OpenSearch Serverless

### 5. Data Source
- Name: `geekbrain-s3-docs`
- Type: S3
- Chunking: 300 tokens, 20% overlap

## Verification Checklist

- [ ] Terraform apply bước 1 thành công
- [ ] OpenSearch collection ACTIVE
- [ ] Script tạo index thành công
- [ ] Terraform apply bước 3 thành công
- [ ] Bedrock KB ACTIVE
- [ ] Data source AVAILABLE

## Troubleshooting

### Issue: "no such index"

**Nguyên nhân**: Chưa chạy `create_index_manual.sh`

**Giải pháp**: Chạy script trước terraform apply lần cuối.

### Issue: boto3 not found

```bash
pip install boto3 urllib3
```

### Issue: Collection not active

Đợi 5 phút sau bước 1.

### Issue: awscurl not found

```bash
pip install awscurl
```

## Chi phí

- OpenSearch: ~$350/tháng
- Bedrock: ~$0.01 (một lần)
- S3: Rất nhỏ

**Tổng**: $350-400/tháng

## Expected Outputs

```json
{
  "s3_bucket": "geekbrain-kb-dev",
  "documents_uploaded": 36,
  "opensearch_endpoint": "https://xxxxx.us-east-1.aoss.amazonaws.com",
  "knowledge_base_id": "XXXXXXXXXX",
  "embedding_model": "amazon.titan-embed-text-v2:0",
  "chunking_strategy": "FIXED_SIZE: 300 tokens, 20% overlap"
}
```

## Next Steps

1. ✓ Infrastructure ready
2. → Task 5.3: Trigger KB sync
3. → Task 6: Implement RAG Pipeline

## Files

- `main.tf` - Infrastructure code
- `create_index_manual.sh` - Script tạo index
- `trigger_kb_sync.sh` - Script cho task 5.3

## Task Completion Criteria

- [x] OpenSearch collection created
- [x] Index created với knn_vector mapping
- [x] Bedrock KB created
- [x] Embedding model: Titan v2
- [x] Chunking: 300 tokens, 20% overlap
- [x] Data source configured
- [x] IAM roles created
- [ ] Deployment thành công không lỗi

**Status**: Code hoàn thành, ready to deploy.
