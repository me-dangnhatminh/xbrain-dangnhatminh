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
    
    # 1. Handle S3 ObjectCreated Event (Triggered when user uploads PDF successfully)
    if 'Records' in event and len(event['Records']) > 0:
        record = event['Records'][0]
        if record.get('eventSource') == 'aws:s3' and 'ObjectCreated' in record.get('eventName', ''):
            handle_s3_upload(record)
            return {"statusCode": 200, "body": "S3 Event Processed"}
            
    # 2. Handle EventBridge Event (Triggered by Bedrock Knowledge Base Ingestion state change)
    if event.get('source') == 'aws.bedrock' and event.get('detail-type') == 'Knowledge Base Ingestion State Change':
        handle_bedrock_ingestion_event(event)
        return {"statusCode": 200, "body": "Bedrock Event Processed"}
        
    return {"statusCode": 200, "body": "Unknown Event, Ignored"}

def handle_s3_upload(record):
    bucket = record['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(record['s3']['object']['key'], encoding='utf-8')
    
    # Ignore .metadata.json uploads, we only care about the actual files
    if key.endswith('.metadata.json'):
        print("Ignoring metadata file upload.")
        return
        
    print(f"File uploaded to S3: s3://{bucket}/{key}")
    
    # Extract document_id from key (format: workspace_id/document_id/filename)
    parts = key.split('/')
    if len(parts) >= 3:
        document_id = parts[1]
        
        # FIX #1: Set status to INDEXING (NOT READY) — file is uploaded but not yet indexed
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
            
            # Store job_id in DB for tracking
            dynamodb.update_item(
                TableName=DOCUMENT_TABLE,
                Key={'document_id': {'S': document_id}},
                UpdateExpression='SET ingestion_job_id = :j',
                ExpressionAttributeValues={':j': {'S': job_id}}
            )
        except Exception as e:
            # FIX #2: If ingestion fails, set status to ERROR (don't silently swallow)
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


def handle_bedrock_ingestion_event(event):
    detail = event.get('detail', {})
    job_id = detail.get('ingestionJobId')
    kb_id = detail.get('knowledgeBaseId')
    status = detail.get('status') # e.g., COMPLETE, FAILED
    
    print(f"Bedrock Ingestion Job {job_id} for KB {kb_id} changed to {status}")
    
    # FIX #3: Only set READY when Bedrock confirms COMPLETE
    new_status = 'READY' if status == 'COMPLETE' else 'ERROR'
    
    # Without a GSI on ingestion_job_id, we have to scan (okay for Hackathon scale)
    response = dynamodb.scan(
        TableName=DOCUMENT_TABLE,
        FilterExpression='ingestion_job_id = :j',
        ExpressionAttributeValues={':j': {'S': job_id}}
    )
    
    items = response.get('Items', [])
    for item in items:
        doc_id = item['document_id']['S']
        dynamodb.update_item(
            TableName=DOCUMENT_TABLE,
            Key={'document_id': {'S': doc_id}},
            UpdateExpression='SET #status = :s, updated_at = :u',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':s': {'S': new_status},
                ':u': {'S': datetime.utcnow().isoformat()}
            }
        )
        print(f"Updated document {doc_id} to {new_status}")

    # FIX #4: If no documents matched by job_id, scan for all INDEXING docs and mark READY
    # This handles the case where EventBridge doesn't carry job_id or it doesn't match
    if not items and status == 'COMPLETE':
        print("No docs matched by job_id, falling back to marking all INDEXING docs as READY")
        fallback = dynamodb.scan(
            TableName=DOCUMENT_TABLE,
            FilterExpression='#status = :s',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':s': {'S': 'INDEXING'}}
        )
        for item in fallback.get('Items', []):
            doc_id = item['document_id']['S']
            dynamodb.update_item(
                TableName=DOCUMENT_TABLE,
                Key={'document_id': {'S': doc_id}},
                UpdateExpression='SET #status = :s, updated_at = :u',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':s': {'S': 'READY'},
                    ':u': {'S': datetime.utcnow().isoformat()}
                }
            )
            print(f"[Fallback] Updated document {doc_id} to READY")
