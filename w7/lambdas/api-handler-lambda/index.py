"""
API Handler Lambda
Handles all REST CRUD operations for Workspaces and Documents.

Routes:
  GET    /workspaces                    - List all workspaces
  POST   /workspaces                    - Create a workspace
  DELETE /workspaces/{workspace_id}     - Delete workspace + all its documents
  GET    /documents                     - List documents (filter by workspace_id)
  GET    /documents/{document_id}       - Get a single document by ID
  POST   /documents/upload              - Init document upload (presigned POST URL)
  DELETE /documents/{document_id}       - Delete a document (DynamoDB + S3 + metadata)
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
    """Delete all S3 objects under a given prefix (max 1000 for hackathon scale)."""
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
            return get_workspaces()

        if path == "/workspaces" and method == "POST":
            return create_workspace(_body(event))

        if path == "/workspaces/{workspace_id}" and method == "DELETE":
            ws_id = _path_param(event, "workspace_id")
            return delete_workspace(ws_id)

        # ── Documents ───────────────────────────────────────────────────────
        if path == "/documents" and method == "GET":
            return list_documents(event)

        if path == "/documents/{document_id}" and method == "GET":
            doc_id = _path_param(event, "document_id")
            return get_document(doc_id)

        if path == "/documents/upload" and method == "POST":
            return init_upload(_body(event))

        if path == "/documents/{document_id}" and method == "DELETE":
            doc_id = _path_param(event, "document_id")
            return delete_document(doc_id)

        return respond(404, {"error": "Not Found", "path": path, "method": method})

    except ValueError as exc:
        return respond(400, {"error": str(exc)})
    except Exception as exc:
        print("Unhandled error:", repr(exc))
        return respond(500, {"error": "Internal Server Error"})


# ── Workspace Handlers ─────────────────────────────────────────────────────────

def get_workspaces() -> dict:
    table = dynamodb.Table(WORKSPACE_TABLE)
    result = table.scan()
    return respond(200, {"workspaces": result.get("Items", [])})


def create_workspace(body: dict) -> dict:
    workspace_id = (body.get("workspace_id") or "").strip()
    tenant_name = (body.get("tenant_name") or "").strip()

    if not workspace_id or not tenant_name:
        raise ValueError("workspace_id and tenant_name are required")

    table = dynamodb.Table(WORKSPACE_TABLE)

    # Idempotency check — return 409 if already exists
    existing = table.get_item(Key={"workspace_id": workspace_id}).get("Item")
    if existing:
        return respond(409, {"error": "Workspace already exists", "workspace": existing})

    item = {
        "workspace_id": workspace_id,
        "tenant_name": tenant_name,
        "created_at": _now(),
        "updated_at": _now(),
    }
    table.put_item(Item=item)
    return respond(201, {"message": "Workspace created", "workspace": item})


def delete_workspace(workspace_id: str | None) -> dict:
    if not workspace_id:
        raise ValueError("workspace_id path parameter is required")

    ws_table = dynamodb.Table(WORKSPACE_TABLE)
    doc_table = dynamodb.Table(DOCUMENT_TABLE)

    # 1. Check workspace exists
    existing = ws_table.get_item(Key={"workspace_id": workspace_id}).get("Item")
    if not existing:
        return respond(404, {"error": "Workspace not found"})

    # 2. Find and delete all documents belonging to this workspace
    docs = doc_table.scan(
        FilterExpression=Attr("workspace_id").eq(workspace_id)
    ).get("Items", [])

    deleted_docs = []
    for doc in docs:
        _hard_delete_document(doc)
        deleted_docs.append(doc["document_id"])

    # 3. Delete S3 prefix for the workspace (catches any orphaned files)
    _delete_s3_prefix(f"{workspace_id}/")

    # 4. Delete workspace record
    ws_table.delete_item(Key={"workspace_id": workspace_id})

    return respond(200, {
        "message": "Workspace deleted",
        "workspace_id": workspace_id,
        "deleted_documents": deleted_docs,
    })


# ── Document Handlers ──────────────────────────────────────────────────────────

def list_documents(event: dict) -> dict:
    workspace_id = _query_param(event, "workspace_id")
    if not workspace_id:
        raise ValueError("workspace_id query parameter is required")

    table = dynamodb.Table(DOCUMENT_TABLE)

    # Scan with filter — acceptable for hackathon scale.
    # In production: add a GSI on workspace_id for O(1) queries.
    result = table.scan(FilterExpression=Attr("workspace_id").eq(workspace_id))
    documents = sorted(
        result.get("Items", []),
        key=lambda d: d.get("created_at", ""),
        reverse=True,
    )
    return respond(200, {"documents": documents, "count": len(documents)})


def get_document(document_id: str | None) -> dict:
    if not document_id:
        raise ValueError("document_id path parameter is required")

    table = dynamodb.Table(DOCUMENT_TABLE)
    item = table.get_item(Key={"document_id": document_id}).get("Item")
    if not item:
        return respond(404, {"error": "Document not found"})
    return respond(200, {"document": item})


def init_upload(body: dict) -> dict:
    workspace_id = (body.get("workspace_id") or "").strip()
    filename = (body.get("filename") or "").strip()

    if not workspace_id or not filename:
        raise ValueError("workspace_id and filename are required")

    # Validate filename extension
    allowed_ext = {".pdf", ".docx", ".txt", ".md"}
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in allowed_ext:
        raise ValueError(f"Unsupported file type '{ext}'. Allowed: {', '.join(allowed_ext)}")

    document_id = str(uuid.uuid4())
    s3_key = f"{workspace_id}/{document_id}/{filename}"
    metadata_key = f"{s3_key}.metadata.json"

    # 1. Create PENDING record in DynamoDB
    table = dynamodb.Table(DOCUMENT_TABLE)
    item = {
        "document_id": document_id,
        "workspace_id": workspace_id,
        "filename": filename,
        "s3_key": s3_key,
        "status": "PENDING",
        "created_at": _now(),
        "updated_at": _now(),
    }
    table.put_item(Item=item)

    # 2. Write Bedrock metadata.json for Tenant Isolation filtering
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=metadata_key,
        Body=json.dumps({"metadataAttributes": {"workspace_id": workspace_id}}),
        ContentType="application/json",
    )

    # 3. Generate Pre-signed POST URL (valid 5 min, max 20MB)
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


def delete_document(document_id: str | None) -> dict:
    if not document_id:
        raise ValueError("document_id path parameter is required")

    table = dynamodb.Table(DOCUMENT_TABLE)
    item = table.get_item(Key={"document_id": document_id}).get("Item")
    if not item:
        return respond(404, {"error": "Document not found"})

    _hard_delete_document(item)
    return respond(200, {
        "message": "Document deleted",
        "document_id": document_id,
        "filename": item.get("filename"),
    })


def _hard_delete_document(doc: dict) -> None:
    """Delete document from DynamoDB and all associated S3 objects."""
    doc_id = doc["document_id"]
    s3_key = doc.get("s3_key")

    # Delete S3 file + metadata.json
    if s3_key:
        try:
            s3.delete_object(Bucket=S3_BUCKET, Key=s3_key)
            s3.delete_object(Bucket=S3_BUCKET, Key=f"{s3_key}.metadata.json")
        except Exception as exc:
            print(f"Warning: S3 delete failed for {s3_key}: {exc}")

    # Delete DynamoDB record
    dynamodb.Table(DOCUMENT_TABLE).delete_item(Key={"document_id": doc_id})
    print(f"Deleted document {doc_id} from DynamoDB and S3")
