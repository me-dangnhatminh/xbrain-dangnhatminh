import json
import os
import boto3
import uuid
from datetime import datetime

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')

# Environment variables (phải khớp với lambdas.tf)
WORKSPACE_TABLE = os.environ.get('WORKSPACE_TABLE')
DOCUMENT_TABLE = os.environ.get('DOCUMENT_TABLE')
S3_BUCKET = os.environ.get('S3_BUCKET')

def get_body(event):
    if 'body' in event and event['body']:
        return json.loads(event['body'])
    return {}

def create_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*" # CORS for frontend
        },
        "body": json.dumps(body, default=str)
    }

def handler(event, context):
    print("API Handler Received Event:", json.dumps(event))
    
    path = event.get('resource', event.get('path', ''))
    method = event.get('httpMethod', '')

    try:
        if path == '/workspaces' and method == 'GET':
            return get_workspaces()
        elif path == '/workspaces' and method == 'POST':
            return create_workspace(get_body(event))
        elif path == '/documents/upload' and method == 'POST':
            return init_document_upload(get_body(event))
        else:
            return create_response(404, {"error": "Not Found"})
    except Exception as e:
        print("Error:", str(e))
        return create_response(500, {"error": "Internal Server Error", "details": str(e)})


def get_workspaces():
    table = dynamodb.Table(WORKSPACE_TABLE)
    response = table.scan()
    return create_response(200, {"workspaces": response.get('Items', [])})

def create_workspace(body):
    workspace_id = body.get('workspace_id')
    tenant_name = body.get('tenant_name')
    
    if not workspace_id or not tenant_name:
        return create_response(400, {"error": "workspace_id and tenant_name are required"})
        
    table = dynamodb.Table(WORKSPACE_TABLE)
    item = {
        'workspace_id': workspace_id,
        'tenant_name': tenant_name,
        'created_at': datetime.utcnow().isoformat()
    }
    table.put_item(Item=item)
    return create_response(201, {"message": "Workspace created", "workspace": item})

def init_document_upload(body):
    workspace_id = body.get('workspace_id')
    filename = body.get('filename')
    
    if not workspace_id or not filename:
        return create_response(400, {"error": "workspace_id and filename are required"})

    document_id = str(uuid.uuid4())
    s3_key = f"{workspace_id}/{document_id}/{filename}"
    metadata_key = f"{s3_key}.metadata.json"

    # 1. Create PENDING record in DynamoDB
    table = dynamodb.Table(DOCUMENT_TABLE)
    item = {
        'document_id': document_id,
        'workspace_id': workspace_id,
        'filename': filename,
        's3_key': s3_key,
        'status': 'PENDING',
        'created_at': datetime.utcnow().isoformat()
    }
    table.put_item(Item=item)

    # 2. Upload metadata.json to S3 (For Bedrock Tenant Isolation)
    metadata_content = {
        "metadataAttributes": {
            "workspace_id": workspace_id
        }
    }
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=metadata_key,
        Body=json.dumps(metadata_content),
        ContentType='application/json'
    )

    # 3. Generate Pre-signed POST URL for the frontend to upload the actual PDF/DOCX
    presigned_post = s3_client.generate_presigned_post(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Conditions=[
            ["content-length-range", 1, 10485760] # Limit file size to 10MB
        ],
        ExpiresIn=300 # URL expires in 5 minutes
    )

    return create_response(200, {
        "document_id": document_id,
        "upload_url": presigned_post,
        "status": "PENDING"
    })
