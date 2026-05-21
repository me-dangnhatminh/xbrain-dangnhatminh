# Tagging Strategy — GeekBrain Platform (W6)

## Overview

This document defines the mandatory tagging strategy for all billable AWS resources
deployed as part of the GeekBrain platform (W6 Operations Hardening).

**Effective date:** 2026-05-21  
**Owner:** dangnhatminh09032002@gmail.com  
**CostCenter:** G5

---

## Mandatory Tag Keys

All billable resources (EC2, ECS, Lambda, S3, DynamoDB, EFS, API Gateway,
CloudFront, Bedrock KB, OpenSearch Serverless) **must** carry all four keys below.

| Tag Key | Required Values | Rule |
|---------|----------------|------|
| `Owner` | `dangnhatminh09032002@gmail.com` | One accountable person — must be consistent casing. Never mix `Owner` and `owner`. |
| `Environment` | `dev` | Lowercase only. Never mix `dev` / `Dev`. |
| `CostCenter` | `G5` | Team/group ID. Uppercase. |
| `Application` | `GeekBrain` | Consistent capitalisation. `GeekBrain` ≠ `geekbrain` in Cost Explorer. |

These four keys are defined once in `terraform/main.tf` as AWS provider `default_tags`
and automatically applied to every resource Terraform manages:

```hcl
provider "aws" {
  default_tags {
    tags = {
      Project     = var.project_name   # "geekbrain"
      Environment = var.environment    # "dev"
      CostCenter  = var.cost_center    # "G5"
      Owner       = var.owner          # "dangnhatminh09032002@gmail.com"
      Application = var.project_name   # "GeekBrain"
    }
  }
}
```

Resource-level `tags` blocks use `{ Name = "..." }` only — no duplication of the
four keys above.

---

## Enforcement Approach

### In This Workshop Account

1. **Terraform default_tags** — every resource gets the four mandatory tags at
   provision time without any per-resource repetition.
2. **Cost Guard Lambda** (`cost_guard_lambda.py`) — sweeps EC2 instances daily
   and stops any instance that does **not** carry `keep=true`. This indirectly
   enforces tagging: untagged or improperly tagged compute is automatically shut down.
3. **Security Guard Lambda** (`security_guard_lambda.py`) — also sweeps for
   security misconfigurations, ensuring tags are not accidentally removed by
   manual console changes.

### In a Production Account

1. **AWS Config rule `required-tags`** — flags any resource missing the four
   mandatory tag keys within minutes of creation.
2. **Service Control Policy (SCP)** on the AWS Organization — denies creation
   of any EC2, RDS, or Lambda resource that does not include all four tags in
   the request.
3. **Tag Policy** on the AWS Organization — enforces allowed values and
   correct capitalisation (e.g., `Environment` must be one of `dev | staging | prod`).

---

## Cost Allocation Tag Activation (Required Step)

Tags only appear as Cost Explorer filter dimensions **after** being explicitly
activated in Billing console.

Steps:
1. AWS Console → **Billing and Cost Management** → **Cost allocation tags**
2. Search for `Owner` and `Application`
3. Select both → **Activate**

> This is a two-step process: tagging resources AND activating allocation tags.
> Skipping activation means tags will not appear in Cost Explorer filters.

---

## Tag Value Registry

| Key | Allowed Values | Notes |
|-----|---------------|-------|
| `Owner` | `dangnhatminh09032002@gmail.com` | Single owner for this workshop |
| `Environment` | `dev` | Only `dev` in this account |
| `CostCenter` | `G5` | Maps to Group 5 |
| `Application` | `GeekBrain` | Consistent with project name |
| `Name` | Resource-specific (e.g., `geekbrain-ecs-cluster`) | Per-resource identifier for console readability |
| `keep` | `true` | Optional — prevents Cost Guard from stopping a resource |

---

## Resource Coverage

| Resource Type | Tagged By | Tag Method |
|--------------|-----------|-----------|
| ECS Cluster / Service / Task | Terraform | `default_tags` |
| Application Load Balancer | Terraform | `default_tags` |
| ECR Repository | Terraform | `default_tags` |
| Lambda Functions (all) | Terraform | `default_tags` |
| S3 Buckets (KB, frontend) | Terraform | `default_tags` |
| DynamoDB Table | Terraform | `default_tags` |
| EFS File System | Terraform | `default_tags` |
| CloudFront Distribution | Terraform | `default_tags` |
| API Gateway | Terraform | `default_tags` |
| Bedrock Knowledge Base | Terraform | `default_tags` |
| OpenSearch Serverless | Terraform | `default_tags` |
| CloudWatch Alarms / Dashboard | Terraform | `default_tags` |
| KMS CMK | Terraform | `default_tags` |
| SNS Topics | Terraform | `default_tags` |
| SQS Queue (DLQ) | Terraform | `default_tags` |
| EventBridge Scheduler Rules | Terraform | `default_tags` |
| IAM Roles | Terraform | `default_tags` |

---

## Cost Guard Integration

The Cost Guard Lambda (`geekbrain-cost-guard-dev`) is triggered daily at 20:00 UTC
and via AWS Budgets → SNS when the account spend approaches $150.

**Stop logic:** any EC2 instance in `running` state that does **not** have tag
`keep=true` is automatically stopped. This creates a financial incentive for
developers to tag resources correctly.

**Metric:** `GeekBrain/CostGuard::ResourcesStopped` is published to CloudWatch
after each run, visible on the W6 Ops dashboard.

---

## Security Trade-Off Statement

- **KMS CMK** (`alias/geekbrain-s3-kb-prod`): costs **$1/month**. Justified
  because the S3 knowledge base holds proprietary educational content — the CMK
  provides a per-principal audit trail via CloudTrail `kms:GenerateDataKey`
  events, which is required for data governance and would be mandatory in any
  production environment handling user-facing AI content.

- **S3 Block Public Access**: costs **$0**. Applied at bucket level for all S3
  buckets and automatically remediated by Security Guard Lambda if disabled.
