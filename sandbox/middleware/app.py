"""
CATE FHIR Middleware - reverse proxy that intercepts FHIR requests,
extracts patient/resource/caller, hashes, logs to collector, forwards unchanged.
"""

import base64
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from cate import compute_patient_hash, log_fhir_access

app = FastAPI(title="CATE FHIR Middleware")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET = os.environ.get("CATE_SECRET", "sandbox-secret")
UPSTREAM_FHIR_URL = os.environ.get("UPSTREAM_FHIR_URL", "http://localhost:8081")
COLLECTOR_URL = os.environ.get("COLLECTOR_URL", "http://localhost:8003")
DEFAULT_ENCOUNTER_ID = "enc-default"


def _extract_vendor_id(request: Request) -> str:
    """Extract caller identity: X-Vendor-ID (sandbox) or JWT client_id."""
    vendor_header = request.headers.get("X-Vendor-ID")
    if vendor_header:
        return vendor_header.strip()

    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        try:
            payload_b64 = token.split(".")[1]
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            return payload.get("client_id") or payload.get("azp") or payload.get("sub") or "unknown"
        except Exception:
            pass
    return "unknown"


def _extract_patient_and_resource(path: str, query: str, body: bytes | None) -> tuple[str | None, str | None]:
    """Extract patient_id and resource_type from FHIR request."""
    patient_id = None
    resource_type = None

    path = path.strip("/")
    parts = path.split("/")

    if len(parts) >= 1:
        resource_type = parts[0]
    if len(parts) >= 2 and parts[1]:
        patient_id = parts[1]

    if patient_id is None and query:
        for param in query.split("&"):
            if "=" in param:
                k, v = param.split("=", 1)
                if k in ("patient", "subject") and v:
                    match = re.search(r"Patient/([^|&]+)", v)
                    if match:
                        patient_id = match.group(1)
                    elif v and not v.startswith("http"):
                        patient_id = v
                    break

    if patient_id is None and body:
        try:
            data = json.loads(body)
            ref = (
                data.get("subject", {}).get("reference")
                or data.get("patient", {}).get("reference")
                or (data.get("subject") if isinstance(data.get("subject"), str) else None)
            )
            if ref:
                match = re.search(r"Patient/([^|&]+)", ref)
                if match:
                    patient_id = match.group(1)
        except Exception:
            pass

    return patient_id, resource_type


def _infer_fhir_action(method: str, path: str, has_query: bool = False) -> str:
    """Infer FHIR action from HTTP method and path."""
    path = path.strip("/")
    parts = path.split("/")
    has_id = len(parts) >= 2 and bool(parts[1])
    if method == "GET":
        return "search" if has_query or not has_id else "read"
    if method == "POST":
        return "create" if not has_id else "update"
    if method in ("PUT", "PATCH"):
        return "update"
    if method == "DELETE":
        return "delete"
    return "read"


def _log_to_collector(event: dict):
    try:
        requests.post(f"{COLLECTOR_URL}/events", json=event, timeout=2)
    except Exception:
        pass


@app.get("/health")
def health():
    return {"status": "ok"}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(request: Request, path: str):
    """Proxy FHIR requests to upstream, extract metadata, log, forward."""
    full_path = request.url.path
    query = request.url.query
    method = request.method
    body = await request.body()

    vendor_id = _extract_vendor_id(request)
    patient_id, resource_type = _extract_patient_and_resource(full_path, query, body)

    if patient_id and resource_type:
        patient_id_hash = compute_patient_hash(SECRET, patient_id, DEFAULT_ENCOUNTER_ID)
        fhir_action = _infer_fhir_action(method, full_path, has_query=bool(query))
        event = log_fhir_access(
            vendor_id=vendor_id,
            resource_type=resource_type,
            patient_id_hash=patient_id_hash,
            fhir_action=fhir_action,
            http_method=method,
        )
        _log_to_collector(event)

    upstream_url = f"{UPSTREAM_FHIR_URL.rstrip('/')}{full_path}"
    if query:
        upstream_url += f"?{query}"

    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
    resp = requests.request(
        method=method,
        url=upstream_url,
        headers=headers,
        data=body,
        timeout=30,
    )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers={k: v for k, v in resp.headers.items() if k.lower() not in ("transfer-encoding", "content-encoding")},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
