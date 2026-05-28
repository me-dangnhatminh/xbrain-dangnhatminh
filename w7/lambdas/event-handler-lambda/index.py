import json
import os
import boto3
import urllib.parse
from datetime import datetime

# Initialize AWS clients
dynamodb = boto3.client('dynamodb')
bedrock_agent = boto3.client('bedrock-agent')

DOCUMENT_TABLE = os.environ.get('DOCUMENT_TABLE')
BEDROCK_KB_ID = os.environ.get('BEDROCK_KB_ID')
BEDROCK_DS_ID = os.environ.get('BEDROCK_DS_ID')

def handler(event, context):
    print("Event Handler Received:", json.dumps(event))
    
    # 1. Handle S3 ObjectCreated Event
    if 'Records' in event and len(event['Records']) > 0:
        record = event['Records'][0]
        if record.get('eventSource') == 'aws:s3' and 'ObjectCreated' in record.get('eventName', ''):
            handle_s3_upload(record)
            return {"statusCode": 200, "body": "S3 Event Processed"}
            
    # 2. Handle EventBridge Event (Bedrock ingestion state change — kept as secondary)
    if event.get('source') == 'aws.bedrock' and event.get('detail-type') == 'Knowledge Base Ingestion State Change':
        handle_bedrock_ingestion_event(event)
        return {"statusCode": 200, "body": "Bedrock Event Processed"}

    # 3. Handle Scheduled Polling (primary mechanism to update INDEXING → READY)
    if event.get('source') == 'aws.events' or event.get('detail-type') == 'Scheduled Event':
        poll_indexing_documents()
        return {"statusCode": 200, "body": "Polling Completed"}
        
    return {"statusCode": 200, "body": "Unknown Event, Ignored"}


def handle_s3_upload(record):
    bucket = record['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(record['s3']['object']['key'], encoding='utf-8')
    
    if key.endswith('.metadata.json'):
        print("Ignoring metadata file upload.")
        return
        
    print(f"File uploaded to S3: s3://{bucket}/{key}")
    
    # Extract document_id from key (format: workspace_id/document_id/filename)
    parts = key.split('/')
    if len(parts) >= 3:
        document_id = parts[1]
        
        # Set status to INDEXING — file uploaded but not yet indexed
        dynamodb.update_item(
            TableName=DOCUMENT_TABLE,
            Key={'document_id': {'S': document_id}},
            UpdateExpression='SET #status = :s, updated_at = :u',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':s': {'S': 'INDEXING'},
                ':u': {'S': datetime.utcnow().isoformat()}
            }
        )
        print(f"Updated document {document_id} to INDEXING")

        # Trigger Bedrock Knowledge Base Ingestion Job
        try:
            response = bedrock_agent.start_ingestion_job(
                knowledgeBaseId=BEDROCK_KB_ID,
                dataSourceId=BEDROCK_DS_ID,
                description=f"Auto-sync for document {document_id}"
            )
            job_id = response['ingestionJob']['ingestionJobId']
            print(f"Started Bedrock Ingestion Job: {job_id}")
            
            dynamodb.update_item(
                TableName=DOCUMENT_TABLE,
                Key={'document_id': {'S': document_id}},
                UpdateExpression='SET ingestion_job_id = :j',
                ExpressionAttributeValues={':j': {'S': job_id}}
            )
        except Exception as e:
            print(f"Failed to start Bedrock Ingestion: {str(e)}")
            dynamodb.update_item(
                TableName=DOCUMENT_TABLE,
                Key={'document_id': {'S': document_id}},
                UpdateExpression='SET #status = :s, updated_at = :u, error_message = :e',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':s': {'S': 'ERROR'},
                    ':u': {'S': datetime.utcnow().isoformat()},
                    ':e': {'S': str(e)}
                }
            )


def poll_indexing_documents():
    """
    Scheduled polling: scan for all INDEXING documents, check their ingestion
    job status via Bedrock API, and update DynamoDB accordingly.
    This is the PRIMARY mechanism — does not depend on EventBridge.
    """
    print("Polling for INDEXING documents...")
    
    response = dynamodb.scan(
        TableName=DOCUMENT_TABLE,
        FilterExpression='#status = :s',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={':s': {'S': 'INDEXING'}}
    )
    
    items = response.get('Items', [])
    print(f"Found {len(items)} documents in INDEXING state")
    
    if not items:
        return
    
    # Collect unique ingestion job IDs to check
    jobs_checked = set()
    
    for item in items:
        doc_id = item['document_id']['S']
        job_id_attr = item.get('ingestion_job_id', {}).get('S')
        
        if not job_id_attr:
            print(f"Document {doc_id} has no ingestion_job_id, skipping")
            continue
        
        # Avoid checking the same job multiple times
        if job_id_attr in jobs_checked:
            continue
        jobs_checked.add(job_id_attr)
            
        try:
            job_response = bedrock_agent.get_ingestion_job(
                knowledgeBaseId=BEDROCK_KB_ID,
                dataSourceId=BEDROCK_DS_ID,
                ingestionJobId=job_id_attr
            )
            job_status = job_response['ingestionJob']['status']
            print(f"Ingestion job {job_id_attr} status: {job_status}")
            
            if job_status == 'COMPLETE':
                _update_docs_by_job_id(job_id_attr, 'READY')
            elif job_status == 'FAILED':
                failure_reasons = job_response['ingestionJob'].get('failureReasons', [])
                error_msg = '; '.join(failure_reasons) if failure_reasons else 'Ingestion failed'
                _update_docs_by_job_id(job_id_attr, 'ERROR', error_msg)
            # If still IN_PROGRESS or STARTING, do nothing — next poll will check again
            
        except Exception as e:
            print(f"Failed to check ingestion job {job_id_attr}: {str(e)}")


def _update_docs_by_job_id(job_id, new_status, error_msg=None):
    """Update all documents matching the given ingestion_job_id."""
    response = dynamodb.scan(
        TableName=DOCUMENT_TABLE,
        FilterExpression='ingestion_job_id = :j',
        ExpressionAttributeValues={':j': {'S': job_id}}
    )
    
    for item in response.get('Items', []):
        doc_id = item['document_id']['S']
        update_expr = 'SET #status = :s, updated_at = :u'
        expr_names = {'#status': 'status'}
        expr_values = {
            ':s': {'S': new_status},
            ':u': {'S': datetime.utcnow().isoformat()}
        }
        
        if error_msg:
            update_expr += ', error_message = :e'
            expr_values[':e'] = {'S': error_msg}
        
        dynamodb.update_item(
            TableName=DOCUMENT_TABLE,
            Key={'document_id': {'S': doc_id}},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values
        )
        print(f"[Poll] Updated document {doc_id} to {new_status}")


def handle_bedrock_ingestion_event(event):
    """Secondary handler — kept as fallback if EventBridge happens to fire."""
    detail = event.get('detail', {})
    job_id = detail.get('ingestionJobId')
    kb_id = detail.get('knowledgeBaseId')
    status = detail.get('status')
    
    print(f"Bedrock Ingestion Job {job_id} for KB {kb_id} changed to {status}")
    
    new_status = 'READY' if status == 'COMPLETE' else 'ERROR'
    _update_docs_by_job_id(job_id, new_status)
