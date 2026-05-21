#!/bin/bash
# =============================================================================
# W6 Demo Loop Script — Thu thập Evidence Screenshots
# Chạy: bash demo_loop.sh
# =============================================================================

set -e

REGION="us-east-1"
COST_GUARD_FN="geekbrain-cost-guard-dev"
SEC_GUARD_FN="geekbrain-security-guard-dev"
KB_SYNC_FN="geekbrain-kb-auto-sync-dev"
KB_BUCKET="geekbrain-kb-dev"
OUT_DIR="/tmp/w6_evidence"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

mkdir -p "$OUT_DIR"

pause() {
  echo ""
  echo -e "${YELLOW}📸 CHỤP ẢNH BÂY GIỜ: $1${NC}"
  echo -e "${CYAN}   Tên file: $2${NC}"
  echo -e "   Nhấn ENTER để tiếp tục sau khi đã chụp..."
  read -r
}

section() {
  echo ""
  echo -e "${GREEN}============================================================${NC}"
  echo -e "${GREEN}  $1${NC}"
  echo -e "${GREEN}============================================================${NC}"
  echo ""
}

# =============================================================================
# PHẦN 1: MH-COST-A — Demo Cost Guard Stop EC2
# =============================================================================

section "PHẦN 1: MH-COST-A — Cost Guard Stop EC2"

echo "[1/3] Tạo EC2 test instance (t3.nano, không có tag keep=true)..."
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id "ami-0c02fb55956c7d316" \
  --instance-type "t3.nano" \
  --count 1 \
  --region "$REGION" \
  --tag-specifications \
    'ResourceType=instance,Tags=[{Key=Name,Value=test-cost-guard-demo},{Key=Environment,Value=dev},{Key=Application,Value=GeekBrain}]' \
  --query "Instances[0].InstanceId" \
  --output text)

echo "   Instance ID: $INSTANCE_ID"
echo ""
echo "[2/3] Đợi instance chuyển sang running..."
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"
echo "   ✅ Instance đang RUNNING"

pause \
  "EC2 Console: EC2 → Instances → filter Name=test-cost-guard-demo → State=running" \
  "costa-04-ec2-running-BEFORE.png"

echo "[3/3] Invoke Cost Guard Lambda..."
aws lambda invoke \
  --function-name "$COST_GUARD_FN" \
  --region "$REGION" \
  --cli-binary-format raw-in-base64-out \
  --payload '{"source":"manual-demo"}' \
  "$OUT_DIR/cost_guard_result.json" > /dev/null

echo ""
echo -e "${GREEN}✅ Cost Guard Lambda response:${NC}"
cat "$OUT_DIR/cost_guard_result.json"
echo ""

pause \
  "Lambda Console: Lambda → geekbrain-cost-guard-dev → Test tab → kết quả có stopped_ec2: [\"$INSTANCE_ID\"]" \
  "costa-05-lambda-invoke-response.png"

echo "Đợi instance chuyển sang stopped..."
aws ec2 wait instance-stopped --instance-ids "$INSTANCE_ID" --region "$REGION"
echo "   ✅ Instance đã STOPPED"

pause \
  "EC2 Console: EC2 → Instances → cùng Instance ID $INSTANCE_ID → State=stopped" \
  "costa-06-ec2-stopped-AFTER.png"

echo ""
echo "Đợi 30 giây để CloudTrail ghi event..."
sleep 30

echo "Lấy CloudTrail event StopInstances..."
aws cloudtrail lookup-events \
  --region "$REGION" \
  --lookup-attributes AttributeKey=EventName,AttributeValue=StopInstances \
  --max-results 1 \
  --query "Events[0].{EventName:EventName,EventTime:EventTime,Resources:Resources}" \
  --output table

pause \
  "CloudTrail: CloudTrail → Event history → Filter: Event name=StopInstances → click event mới nhất → thấy instanceId=$INSTANCE_ID và userAgent chứa lambda" \
  "costa-07-cloudtrail-stop-instances.png"

# =============================================================================
# PHẦN 2: MH-COST-A — Demo SNS → Lambda chain
# =============================================================================

section "PHẦN 1b: MH-COST-A — Demo SNS Budget → Lambda chain"

SNS_TOPIC_ARN="arn:aws:sns:$REGION:211663743610:geekbrain-budget-alerts"

pause \
  "SNS Console: SNS → Topics → geekbrain-budget-alerts → tab Subscriptions → thấy 2 subscriptions (lambda + email)" \
  "costa-08-sns-subscriptions.png"

echo "Publish test message tới SNS topic..."
aws sns publish \
  --region "$REGION" \
  --topic-arn "$SNS_TOPIC_ARN" \
  --subject "Budget Alert Test" \
  --message '{"AlarmName":"geekbrain-w6-cost-cap","NewStateValue":"ALARM","NewStateReason":"Test","StateChangeTime":"2026-05-21T15:00:00Z"}' \
  --query "MessageId" \
  --output text

pause \
  "SNS Console: SNS → geekbrain-budget-alerts → Publish message → click Publish → thấy success MessageId" \
  "costa-09-sns-publish-test.png"

echo "Đợi 15 giây để Lambda process SNS..."
sleep 15

echo "Lấy Lambda logs để verify SNS trigger..."
aws logs get-log-events \
  --region "$REGION" \
  --log-group-name "/aws/lambda/$COST_GUARD_FN" \
  --log-stream-name "$(aws logs describe-log-streams \
    --region "$REGION" \
    --log-group-name "/aws/lambda/$COST_GUARD_FN" \
    --order-by LastEventTime \
    --descending \
    --max-items 1 \
    --query "logStreams[0].logStreamName" \
    --output text)" \
  --limit 10 \
  --query "events[*].message" \
  --output text 2>/dev/null | head -20

pause \
  "CloudWatch Logs: Lambda → geekbrain-cost-guard-dev → Monitor → View CloudWatch logs → log stream mới nhất → thấy 'Budget SNS alert' hoặc 'Cost Guard triggered'" \
  "costa-10-lambda-triggered-by-sns.png"

# =============================================================================
# PHẦN 3: MH-SEC — Demo Security Guard S3 Public Access
# =============================================================================

section "PHẦN 2: MH-SEC — Security Guard Demo Loop"

echo "[1/4] Xóa Block Public Access trên bucket để tạo violation..."
aws s3api delete-public-access-block \
  --bucket "$KB_BUCKET" \
  --region "$REGION"
echo "   ✅ Bucket $KB_BUCKET đã bị mở (violation tạo thành công)"

echo ""
echo "Verify bucket đang bị mở..."
CURRENT_STATUS=$(aws s3api get-public-access-block --bucket "$KB_BUCKET" 2>&1 || echo "NoPublicAccessBlock")
echo "   Status: $CURRENT_STATUS"

pause \
  "S3 Console: S3 → geekbrain-kb-dev → tab Permissions → Block public access → thấy OFF hoặc cảnh báo đỏ" \
  "sec-04-s3-public-BEFORE.png"

echo "[2/4] Invoke Security Guard Lambda..."
aws lambda invoke \
  --function-name "$SEC_GUARD_FN" \
  --region "$REGION" \
  --cli-binary-format raw-in-base64-out \
  --payload '{"source":"manual-demo"}' \
  "$OUT_DIR/sec_guard_result.json" > /dev/null

echo ""
echo -e "${GREEN}✅ Security Guard Lambda response:${NC}"
cat "$OUT_DIR/sec_guard_result.json"
echo ""

pause \
  "Lambda Console: Lambda → geekbrain-security-guard-dev → Test → kết quả có remediated_s3_buckets: [\"geekbrain-kb-dev\"]" \
  "sec-05-security-guard-invoke-response.png"

echo "[3/4] Verify bucket đã được remediate..."
aws s3api get-public-access-block \
  --bucket "$KB_BUCKET" \
  --region "$REGION" \
  --query "PublicAccessBlockConfiguration" \
  --output table

pause \
  "S3 Console: S3 → geekbrain-kb-dev → tab Permissions → Block public access → thấy tất cả ON (xanh)" \
  "sec-06-s3-public-AFTER.png"

echo "[4/4] Đợi 30 giây để CloudTrail ghi event PutPublicAccessBlock..."
sleep 30

aws cloudtrail lookup-events \
  --region "$REGION" \
  --lookup-attributes AttributeKey=EventName,AttributeValue=PutPublicAccessBlock \
  --max-results 1 \
  --query "Events[0].{EventName:EventName,EventTime:EventTime,Resources:Resources}" \
  --output table

pause \
  "CloudTrail: CloudTrail → Event history → Filter: Event name=PutPublicAccessBlock → click event mới nhất → thấy bucketName=geekbrain-kb-dev và userAgent chứa lambda" \
  "sec-07-cloudtrail-put-public-access-block.png"

# =============================================================================
# PHẦN 4: MH-SEC — KMS GenerateDataKey
# =============================================================================

section "PHẦN 2b: MH-SEC — KMS CMK verify"

echo "Upload file test để trigger KMS GenerateDataKey..."
echo "kms-verify-$(date +%s)" | aws s3 cp - "s3://$KB_BUCKET/kms-verify.txt" --region "$REGION"
echo "   ✅ File uploaded, KMS GenerateDataKey đã được trigger"

echo ""
echo "Đợi 30 giây để CloudTrail ghi event..."
sleep 30

pause \
  "KMS Console: KMS → Customer managed keys → key alias geekbrain-s3-kb-prod → Key status=Enabled, Automatic rotation=Enabled" \
  "sec-08-kms-cmk-overview.png"

pause \
  "S3 Console: S3 → geekbrain-kb-dev → Properties → Default encryption → SSE-KMS, Key ARN chứa geekbrain-s3-kb-prod" \
  "sec-09-s3-kms-encryption.png"

pause \
  "CloudTrail: CloudTrail → Event history → Filter: Event name=GenerateDataKey → click event có userAgent chứa 's3'" \
  "sec-10-cloudtrail-kms-generate-data-key.png"

# =============================================================================
# PHẦN 5: MH-OBS — Trigger Alarm ALARM → OK
# =============================================================================

section "PHẦN 3: MH-OBS — Alarm State Demo"

echo "Push custom metrics vào GeekBrain/Application namespace..."
for i in {1..5}; do
  VALUE=$((150 + RANDOM % 300))
  aws cloudwatch put-metric-data \
    --region "$REGION" \
    --namespace "GeekBrain/Application" \
    --metric-name "BedrockQueryLatencyMs" \
    --dimensions Name=Service,Value=geekbrain-backend \
    --value "$VALUE" --unit Milliseconds
  aws cloudwatch put-metric-data \
    --region "$REGION" \
    --namespace "GeekBrain/Application" \
    --metric-name "KBSyncItemsCount" \
    --dimensions Name=Service,Value=geekbrain-backend \
    --value "$i" --unit Count
  echo "   [${i}/5] Pushed: BedrockQueryLatencyMs=$VALUE, KBSyncItemsCount=$i"
  sleep 3
done
echo "   ✅ Custom metrics pushed"

pause \
  "CloudWatch: CloudWatch → Metrics → All metrics → GeekBrain/Application → thấy BedrockQueryLatencyMs và KBSyncItemsCount" \
  "obs-03-custom-metric-namespace.png"

echo ""
echo "Invoke Lambda 6 lần với force_error để trigger alarm..."
for i in {1..6}; do
  aws lambda invoke \
    --function-name "$KB_SYNC_FN" \
    --region "$REGION" \
    --cli-binary-format raw-in-base64-out \
    --payload '{"force_error": true}' \
    "$OUT_DIR/err_$i.json" 2>/dev/null || true
  echo "   [${i}/6] Error invocation sent"
  sleep 5
done
echo "   ✅ 6 errors triggered"
echo ""
echo -e "${YELLOW}⏳ Đợi 2-3 phút để CloudWatch alarm chuyển sang ALARM state...${NC}"
echo "   (Alarm threshold = 3 errors trong 5 phút)"
sleep 120

pause \
  "CloudWatch: CloudWatch → Alarms → geekbrain-lambda-errors → State = IN ALARM (đỏ)" \
  "obs-04-alarm-in-ALARM-state.png"

echo ""
echo -e "${YELLOW}⏳ Đợi thêm 5-7 phút để alarm tự chuyển về OK (không có error mới)...${NC}"
sleep 360

pause \
  "CloudWatch: CloudWatch → Alarms → geekbrain-lambda-errors → State = OK (xanh)" \
  "obs-05-alarm-back-to-OK.png"

pause \
  "CloudWatch: CloudWatch → Alarms → All alarms → toàn bộ danh sách, không có INSUFFICIENT_DATA" \
  "obs-06-all-alarms-no-insufficient-data.png"

# =============================================================================
# PHẦN 6: MH-OBS — Dashboard + Log Insights
# =============================================================================

section "PHẦN 3b: MH-OBS — Dashboard & Log Insights"

pause \
  "CloudWatch: CloudWatch → Dashboards → geekbrain-w6-ops → chụp toàn màn hình dashboard" \
  "obs-01-dashboard-full.png"

pause \
  "CloudWatch: Zoom vào widget 'Bedrock Query Latency (Custom Metric)' → thấy data points không phải 'No data'" \
  "obs-02-custom-metric-widget.png"

pause \
  "CloudWatch: CloudWatch → Logs Insights → Saved queries → thấy danh sách GeekBrain/ECS-Error-Spikes, GeekBrain/Bedrock-Query-Latency..." \
  "obs-07-log-insights-saved-queries.png"

pause \
  "CloudWatch: Click GeekBrain/ECS-Error-Spikes → Run query → thấy query text + ≥5 rows kết quả" \
  "obs-08-log-insights-query-results.png"

# =============================================================================
# HOÀN THÀNH
# =============================================================================

section "✅ HOÀN THÀNH — Tóm tắt"

echo "Các ảnh đã chụp nên được lưu vào: w6/docs/screenshots/"
echo ""
echo "Danh sách ảnh cần có:"
echo "  MH-COST-V: costv-01 đến costv-07 (7 ảnh) — chụp riêng từ console"
echo "  MH-COST-A: costa-01 đến costa-10 (10 ảnh) — script đã hướng dẫn"
echo "  MH-OBS:    obs-01 đến obs-09 (9 ảnh) — script đã hướng dẫn"
echo "  MH-SEC:    sec-01 đến sec-10 (10 ảnh) — script đã hướng dẫn"
echo ""
echo "Còn cần chụp thủ công (không cần script):"
echo "  costv-01: Lambda Tags"
echo "  costv-02: S3 Tags"
echo "  costv-03: ECS Tags"
echo "  costv-04: Billing → Cost Allocation Tags Activated"
echo "  costv-05: Budget config"
echo "  costv-06: Cost Explorer by tag"
echo "  costv-07: Baseline cost breakdown"
echo "  costa-01: Cost Guard Lambda overview"
echo "  costa-02: Cost Guard IAM policy"
echo "  costa-03: EventBridge schedule"
echo "  sec-01:   Security Guard Lambda overview"
echo "  sec-02:   Security Guard IAM policy"
echo "  sec-03:   EventBridge CloudTrail rule"
echo "  obs-09:   PutMetricData code snippet"
echo ""
echo "Lambda invoke results saved to: $OUT_DIR/"
ls -la "$OUT_DIR/"
