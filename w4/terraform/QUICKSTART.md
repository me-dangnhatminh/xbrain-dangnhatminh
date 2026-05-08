# Quick Start - Deploy Bedrock Knowledge Base

## TL;DR - 3 Bước

```bash
cd w4/terraform

# Bước 1: Tạo OpenSearch collection
terraform init
terraform apply -target=aws_opensearchserverless_collection.kb_vector_store \
                -target=aws_opensearchserverless_security_policy.kb_encryption \
                -target=aws_opensearchserverless_security_policy.kb_network \
                -target=aws_opensearchserverless_access_policy.kb_data_access \
                -target=aws_iam_role.bedrock_kb_role \
                -target=aws_iam_role_policy.bedrock_kb_s3_policy \
                -target=aws_iam_role_policy.bedrock_kb_aoss_policy \
                -target=time_sleep.wait_for_collection

# Bước 2: Tạo index (chạy sau khi collection active)
bash create_index_manual.sh

# Bước 3: Tạo Bedrock KB
terraform apply

# Bước 4: Trigger ingestion
bash trigger_kb_sync.sh
```

## Chi tiết từng bước

### Bước 1: Initialize và tạo OpenSearch Collection

```bash
cd w4/terraform
terraform init
```

Tạo OpenSearch collection trước (mất 10-15 phút):

```bash
terraform apply -target=aws_opensearchserverless_collection.kb_vector_store \
                -target=aws_opensearchserverless_security_policy.kb_encryption \
                -target=aws_opensearchserverless_security_policy.kb_network \
                -target=aws_opensearchserverless_access_policy.kb_data_access \
                -target=aws_iam_role.bedrock_kb_role \
                -target=aws_iam_role_policy.bedrock_kb_s3_policy \
                -target=aws_iam_role_policy.bedrock_kb_aoss_policy \
                -target=time_sleep.wait_for_collection
```

Nhập `yes` khi được hỏi.

### Bước 2: Tạo OpenSearch Index

Sau khi collection active (đợi thêm 2-3 phút), chạy:

```bash
bash create_index_manual.sh
```

Script này sẽ:
- Lấy endpoint từ terraform output
- Tạo index với knn_vector mapping
- Tự động dùng awscurl hoặc Python boto3

**Nếu thiếu dependencies**:
```bash
# Option 1: Cài awscurl
pip install awscurl

# Option 2: Cài boto3 + urllib3
pip install boto3 urllib3
```

### Bước 3: Tạo Bedrock Knowledge Base

```bash
terraform apply
```

Lần này sẽ tạo:
- Bedrock Knowledge Base
- Data Source với S3

### Bước 4: Verify

```bash
terraform output -json setup_summary | jq '.'
```

### Bước 5: Trigger Ingestion (Task 5.3)

```bash
bash trigger_kb_sync.sh
```

## Tại sao phải tách 3 bước?

1. **OpenSearch collection** mất 10-15 phút để active
2. **Index** phải được tạo sau khi collection active
3. **Bedrock KB** cần index tồn tại trước khi tạo

Terraform không thể đảm bảo thứ tự này một cách đáng tin cậy với external scripts, nên tách thành manual steps.

## Troubleshooting

### Lỗi: "no such index"

Bạn đã chạy `create_index_manual.sh` chưa? Chạy nó trước khi `terraform apply` lần cuối.

### Lỗi: boto3 not found

```bash
pip install boto3 urllib3
# hoặc
pip install awscurl
```

### Lỗi: Collection not active

Đợi thêm 5 phút sau terraform apply đầu tiên, rồi chạy `create_index_manual.sh`.

## Clean up

```bash
terraform destroy
```

## Files quan trọng

- `README.md` - Hướng dẫn đầy đủ
- `TASK_5.2_GUIDE.md` - Hướng dẫn chi tiết
- `QUICKSTART.md` - File này
- `create_index_manual.sh` - Script tạo index (chạy manual)

## Next Steps

1. ✓ Infrastructure ready
2. → Task 5.3: Test retrieval
3. → Task 6: Implement RAG Pipeline
