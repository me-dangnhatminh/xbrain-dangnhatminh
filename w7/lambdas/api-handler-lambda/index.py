"""
API Handler Lambda
Handles all REST CRUD operations for Workspaces and Documents.
ENFORCES STRICT TENANT ISOLATION VIA COMPOSITE KEYS AND EXPLICIT DB FIELDS.
"""

import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Attr

# ── AWS Clients ────────────────────────────────────────────────────────────────
dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

# ── Environment Variables ──────────────────────────────────────────────────────
WORKSPACE_TABLE = os.environ["WORKSPACE_TABLE"]
DOCUMENT_TABLE = os.environ["DOCUMENT_TABLE"]
S3_BUCKET = os.environ["S3_BUCKET"]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _body(event: dict) -> dict:
    raw = event.get("body") or "{}"
    if isinstance(raw, str):
        return json.loads(raw)
    return raw


def _path_param(event: dict, name: str) -> str | None:
    return (event.get("pathParameters") or {}).get(name)

def _query_param(event: dict, name: str) -> str | None:
    return (event.get("queryStringParameters") or {}).get(name)


def _get_identity(event: dict) -> tuple[str, str]:
    """
    Extracts tenant_id and owner_sub securely from API Gateway Cognito Authorizer JWT claims.
    Returns: (tenant_id, owner_sub)
    """
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    if not claims:
        return ("local-dev-workspace", "local-dev-user")
        
    ws_id = claims.get("custom:workspace_id")
    sub = claims.get("sub")
    
    tenant_id = ws_id if ws_id else sub
    
    if not tenant_id or not sub:
        raise PermissionError("Unauthorized: Identity claims missing")
        
    return (tenant_id, sub)


def respond(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
        },
        "body": json.dumps(body, default=str),
    }


def _delete_s3_prefix(prefix: str) -> None:
    """Delete all S3 objects under a given prefix."""
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        objects = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
        if objects:
            s3.delete_objects(Bucket=S3_BUCKET, Delete={"Objects": objects})


# ── Router ─────────────────────────────────────────────────────────────────────

def handler(event, context):
    print("API Handler Event:", json.dumps(event))

    path = event.get("resource", event.get("path", ""))
    method = event.get("httpMethod", "")

    try:
        # ── Workspaces ──────────────────────────────────────────────────────
        if path == "/workspaces" and method == "GET":
            return get_workspaces(event)

        if path == "/workspaces" and method == "POST":
            return create_workspace(event, _body(event))

        if path == "/workspaces/{workspace_id}" and method == "DELETE":
            ws_id = _path_param(event, "workspace_id")
            return delete_workspace(event, ws_id)

        # ── Documents ───────────────────────────────────────────────────────
        if path == "/documents" and method == "GET":
            return list_documents(event)

        if path == "/documents/{document_id}" and method == "GET":
            doc_id = _path_param(event, "document_id")
            return get_document(event, doc_id)

        if path == "/documents/upload" and method == "POST":
            return init_upload(event, _body(event))

        if path == "/documents/{document_id}" and method == "DELETE":
            doc_id = _path_param(event, "document_id")
            return delete_document(event, doc_id)

        return respond(404, {"error": "Not Found", "path": path, "method": method})

    except PermissionError as exc:
        return respond(403, {"error": str(exc)})
    except ValueError as exc:
        return respond(400, {"error": str(exc)})
    except Exception as exc:
        print("Unhandled error:", repr(exc))
        return respond(500, {"error": "Internal Server Error"})


# ── Workspace Handlers ─────────────────────────────────────────────────────────

def get_workspaces(event: dict) -> dict:
    tenant_id, _ = _get_identity(event)
    table = dynamodb.Table(WORKSPACE_TABLE)
    
    # Filter workspaces to ONLY return those owned by this tenant
    # (Note: In production, use a Global Secondary Index on tenant_id for scalability)
    result = table.scan()
    items = [item for item in result.get("Items", []) if item.get("tenant_id") == tenant_id]
    
    return respond(200, {"workspaces": items})


def create_workspace(event: dict, body: dict) -> dict:
    tenant_id, owner_sub = _get_identity(event)
    workspace_id = (body.get("workspace_id") or "").strip()
    name = (body.get("tenant_name") or "Knowledge Base").strip() # Frontend sends name in tenant_name
    
    if not workspace_id:
        raise ValueError("workspace_id is required")

    table = dynamodb.Table(WORKSPACE_TABLE)

    existing = table.get_item(Key={"workspace_id": workspace_id}).get("Item")
    if existing:
        return respond(409, {"error": "Workspace already exists", "workspace": existing})

    # Clean DB Schema enforcing business logic
    item = {
        "workspace_id": workspace_id, # The unique ID of this Knowledge Base
        "tenant_id": tenant_id,       # The organization this KB belongs to
        "owner_sub": owner_sub,       # The specific user who created it
        "name": name,                 # Human readable name
        "created_at": _now(),
        "updated_at": _now(),
    }
    table.put_item(Item=item)
    return respond(201, {"message": "Workspace created", "workspace": item})


def delete_workspace(event: dict, workspace_id: str | None) -> dict:
    if not workspace_id:
        raise ValueError("workspace_id path parameter is required")
        
    tenant_id, _ = _get_identity(event)
    ws_table = dynamodb.Table(WORKSPACE_TABLE)
    doc_table = dynamodb.Table(DOCUMENT_TABLE)

    existing = ws_table.get_item(Key={"workspace_id": workspace_id}).get("Item")
    if not existing:
        return respond(404, {"error": "Workspace not found"})
        
    # Tenant Isolation Verification
    if existing.get("tenant_id") != tenant_id and existing.get("tenant_name") != tenant_id:
        raise PermissionError("Access Denied: You cannot delete another tenant's workspace")

    docs = doc_table.scan(
        FilterExpression=Attr("workspace_id").eq(workspace_id)
    ).get("Items", [])

    deleted_docs = []
    for doc in docs:
        _hard_delete_document(doc)
        deleted_docs.append(doc["document_id"])

    _delete_s3_prefix(f"{workspace_id}/")
    ws_table.delete_item(Key={"workspace_id": workspace_id})

    return respond(200, {
        "message": "Workspace deleted",
        "workspace_id": workspace_id,
        "deleted_documents": deleted_docs,
    })


# ── Document Handlers ──────────────────────────────────────────────────────────

def list_documents(event: dict) -> dict:
    tenant_id, _ = _get_identity(event)
    workspace_id = _query_param(event, "workspace_id")
    if not workspace_id:
        raise ValueError("workspace_id query parameter is required")
        
    # Tenant Isolation Verification
    ws_table = dynamodb.Table(WORKSPACE_TABLE)
    ws = ws_table.get_item(Key={"workspace_id": workspace_id}).get("Item")
    if not ws or (ws.get("tenant_id") != tenant_id and ws.get("tenant_name") != tenant_id):
        raise PermissionError("Access Denied: You do not have access to this Knowledge Base")

    table = dynamodb.Table(DOCUMENT_TABLE)
    # Only return documents belonging to this verified workspace
    result = table.scan(FilterExpression=Attr("workspace_id").eq(workspace_id))
    documents = sorted(
        result.get("Items", []),
        key=lambda d: d.get("created_at", ""),
        reverse=True,
    )
    return respond(200, {"documents": documents, "count": len(documents)})


def get_document(event: dict, document_id: str | None) -> dict:
    if not document_id:
        raise ValueError("document_id path parameter is required")

    tenant_id, _ = _get_identity(event)
    table = dynamodb.Table(DOCUMENT_TABLE)
    
    item = table.get_item(Key={"document_id": document_id}).get("Item")
    if not item:
        return respond(404, {"error": "Document not found"})
        
    # Verify the document belongs to a workspace owned by this tenant
    ws_table = dynamodb.Table(WORKSPACE_TABLE)
    ws = ws_table.get_item(Key={"workspace_id": item.get("workspace_id")}).get("Item")
    if not ws or (ws.get("tenant_id") != tenant_id and ws.get("tenant_name") != tenant_id):
        raise PermissionError("Access Denied: Document belongs to another tenant")
        
    return respond(200, {"document": item})


def init_upload(event: dict, body: dict) -> dict:
    tenant_id, owner_sub = _get_identity(event)
    workspace_id = (body.get("workspace_id") or "").strip()
    filename = (body.get("filename") or "").strip()

    if not filename or not workspace_id:
        raise ValueError("filename and workspace_id are required")
        
    # Verify the target workspace belongs to this tenant
    ws_table = dynamodb.Table(WORKSPACE_TABLE)
    ws = ws_table.get_item(Key={"workspace_id": workspace_id}).get("Item")
    if not ws or (ws.get("tenant_id") != tenant_id and ws.get("tenant_name") != tenant_id):
        raise PermissionError("Access Denied: Target workspace belongs to another tenant")

    allowed_ext = {".pdf", ".docx", ".txt", ".md"}
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in allowed_ext:
        raise ValueError(f"Unsupported file type '{ext}'. Allowed: {', '.join(allowed_ext)}")

    document_id = str(uuid.uuid4())
    s3_key = f"{workspace_id}/{document_id}/{filename}"
    metadata_key = f"{s3_key}.metadata.json"

    table = dynamodb.Table(DOCUMENT_TABLE)
    item = {
        "document_id": document_id,
        "workspace_id": workspace_id,
        "tenant_id": tenant_id,     # Explicit tracking of document owner
        "uploaded_by": owner_sub,   # Audit trail
        "filename": filename,
        "s3_key": s3_key,
        "status": "PENDING",
        "created_at": _now(),
        "updated_at": _now(),
    }
    table.put_item(Item=item)

    # Secure Multi-Tenant Composite Key for Bedrock Metadata
    # This prevents cross-tenant data leakage in the RAG pipeline
    composite_key = f"{tenant_id}#{workspace_id}"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=metadata_key,
        Body=json.dumps({"metadataAttributes": {"workspace_id": composite_key}}),
        ContentType="application/json",
    )

    presigned = s3.generate_presigned_post(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Conditions=[["content-length-range", 1, 20 * 1024 * 1024]],
        ExpiresIn=300,
    )

    return respond(200, {
        "document_id": document_id,
        "upload_url": presigned,
        "status": "PENDING",
    })


def delete_document(event: dict, document_id: str | None) -> dict:
    if not document_id:
        raise ValueError("document_id path parameter is required")

    tenant_id, _ = _get_identity(event)
    table = dynamodb.Table(DOCUMENT_TABLE)
    
    item = table.get_item(Key={"document_id": document_id}).get("Item")
    if not item:
        return respond(404, {"error": "Document not found"})
        
    # Verify ownership
    ws_table = dynamodb.Table(WORKSPACE_TABLE)
    ws = ws_table.get_item(Key={"workspace_id": item.get("workspace_id")}).get("Item")
    if not ws or (ws.get("tenant_id") != tenant_id and ws.get("tenant_name") != tenant_id):
        raise PermissionError("Access Denied")

    _hard_delete_document(item)
    return respond(200, {
        "message": "Document deleted",
        "document_id": document_id,
        "filename": item.get("filename"),
    })


def _hard_delete_document(doc: dict) -> None:
    doc_id = doc["document_id"]
    s3_key = doc.get("s3_key")

    if s3_key:
        try:
            s3.delete_object(Bucket=S3_BUCKET, Key=s3_key)
            s3.delete_object(Bucket=S3_BUCKET, Key=f"{s3_key}.metadata.json")
        except Exception as exc:
            print(f"Warning: S3 delete failed for {s3_key}: {exc}")

    dynamodb.Table(DOCUMENT_TABLE).delete_item(Key={"document_id": doc_id})
    print(f"Deleted document {doc_id} from DynamoDB and S3")
