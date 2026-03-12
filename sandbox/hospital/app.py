"""
Hospital sandbox app - demo orchestrator.
Triggers vendors; vendors call FHIR via middleware (middleware logs).
Keeps /audit for ATNA events, /trace for collector.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from pydantic import BaseModel
from cate import compute_patient_hash, compute_provider_hash, log_cate_atna

app = FastAPI(title="CATE Hospital API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET = "sandbox-secret"
TRAD_ML_URL = "http://localhost:8001/predict"
LLM_URL = "http://localhost:8002/summarize"
COLLECTOR_URL = "http://localhost:8003"


def _truncate_hash(h: str, n: int = 16) -> str:
    return f"{h[:n]}..." if len(h) > n else h


def _fetch_trace(patient_id_hash: str, provider_id_hash: str | None = None):
    params = {"patient_id_hash": patient_id_hash}
    if provider_id_hash:
        params["provider_id_hash"] = provider_id_hash
    try:
        r = requests.get(f"{COLLECTOR_URL}/traces", params=params, timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return {"error": "Failed to fetch trace"}


def get_hashes(patient_id: str, provider_id: str, encounter_id: str):
    patient_id_hash = compute_patient_hash(SECRET, patient_id, encounter_id)
    provider_id_hash = compute_provider_hash(SECRET, provider_id)
    return patient_id_hash, provider_id_hash


class Context(BaseModel):
    patient_id: str = "MRN001"
    provider_id: str = "NPI123"
    encounter_id: str = "enc-001"


class AuditRequest(BaseModel):
    patient_id: str = "MRN001"
    provider_id: str = "NPI123"
    encounter_id: str = "enc-001"
    action: str = "chart_open"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
def run_predict(ctx: Context):
    """Trigger Trad ML vendor for sepsis prediction. Vendor calls FHIR via middleware."""
    patient_id_hash, provider_id_hash = get_hashes(ctx.patient_id, ctx.provider_id, ctx.encounter_id)
    body = {"patient_id": ctx.patient_id, "provider_id": ctx.provider_id, "encounter_id": ctx.encounter_id}
    request_info = {
        "hospital_sends": {
            "to": "Trad ML vendor (sepsis prediction)",
            "url": TRAD_ML_URL,
            "body": body,
        },
    }
    try:
        r = requests.post(TRAD_ML_URL, json=body, timeout=5)
        r.raise_for_status()
        vendor_response = r.json()
        return {
            "result": vendor_response,
            "request": request_info,
            "vendor_returns": vendor_response,
            "trace": _fetch_trace(patient_id_hash, provider_id_hash),
        }
    except requests.RequestException as e:
        from fastapi import HTTPException
        raise HTTPException(502, str(e))


@app.post("/summarize")
def run_summarize(ctx: Context):
    """Trigger LLM vendor for note summarization. Vendor calls FHIR via middleware."""
    patient_id_hash, provider_id_hash = get_hashes(ctx.patient_id, ctx.provider_id, ctx.encounter_id)
    body = {
        "patient_id": ctx.patient_id,
        "provider_id": ctx.provider_id,
        "encounter_id": ctx.encounter_id,
        "note": "Patient presents with fever. Labs show elevated WBC.",
    }
    request_info = {
        "hospital_sends": {
            "to": "LLM vendor (note summarization)",
            "url": LLM_URL,
            "body": body,
        },
    }
    try:
        r = requests.post(LLM_URL, json=body, timeout=5)
        r.raise_for_status()
        vendor_response = r.json()
        return {
            "result": vendor_response,
            "request": request_info,
            "vendor_returns": vendor_response,
            "trace": _fetch_trace(patient_id_hash, provider_id_hash),
        }
    except requests.RequestException as e:
        from fastapi import HTTPException
        raise HTTPException(502, str(e))


@app.post("/audit")
def record_audit(req: AuditRequest):
    """Record an ATNA-style audit event (e.g., chart open, view labs)."""
    patient_id_hash, provider_id_hash = get_hashes(req.patient_id, req.provider_id, req.encounter_id)
    action = req.action if req.action in (
        "chart_open", "view_labs", "view_meds", "document_access", "order_entry", "other"
    ) else "other"
    event = log_cate_atna(
        patient_id_hash=patient_id_hash,
        provider_id_hash=provider_id_hash,
        action=action,
        resource_type={"chart_open": "Patient", "view_labs": "Observation", "view_meds": "MedicationRequest"}.get(action),
    )
    try:
        requests.post(f"{COLLECTOR_URL}/events", json=event, timeout=2)
        return {
            "ok": True,
            "action": action,
            "trace": _fetch_trace(patient_id_hash, provider_id_hash),
        }
    except requests.RequestException as e:
        from fastapi import HTTPException
        raise HTTPException(502, str(e))


@app.post("/demo")
def run_demo(ctx: Context):
    """Run full demo: Open Chart → View Labs → Sepsis Prediction → Summarize Notes."""
    import time
    patient_id_hash, provider_id_hash = get_hashes(ctx.patient_id, ctx.provider_id, ctx.encounter_id)
    body = {"patient_id": ctx.patient_id, "provider_id": ctx.provider_id, "encounter_id": ctx.encounter_id}
    steps = []

    audit_event = log_cate_atna(patient_id_hash, provider_id_hash, "chart_open", resource_type="Patient")
    try:
        requests.post(f"{COLLECTOR_URL}/events", json=audit_event, timeout=2)
        steps.append({"step": "chart_open", "ok": True})
    except Exception:
        steps.append({"step": "chart_open", "ok": False})
    time.sleep(0.2)

    audit_event = log_cate_atna(patient_id_hash, provider_id_hash, "view_labs", resource_type="Observation")
    try:
        requests.post(f"{COLLECTOR_URL}/events", json=audit_event, timeout=2)
        steps.append({"step": "view_labs", "ok": True})
    except Exception:
        steps.append({"step": "view_labs", "ok": False})
    time.sleep(0.2)

    try:
        r = requests.post(TRAD_ML_URL, json=body, timeout=5)
        r.raise_for_status()
        steps.append({"step": "predict", "ok": True, "result": r.json()})
    except requests.RequestException:
        steps.append({"step": "predict", "ok": False})
    time.sleep(0.2)

    try:
        r = requests.post(
            LLM_URL,
            json={**body, "note": "Patient presents with fever. Labs show elevated WBC."},
            timeout=5,
        )
        r.raise_for_status()
        steps.append({"step": "summarize", "ok": True, "result": r.json()})
    except requests.RequestException:
        steps.append({"step": "summarize", "ok": False})

    try:
        r = requests.get(f"{COLLECTOR_URL}/traces", params={"patient_id_hash": patient_id_hash, "provider_id_hash": provider_id_hash}, timeout=5)
        r.raise_for_status()
        trace = r.json()
    except requests.RequestException:
        trace = {"error": "Failed to fetch trace"}

    return {
        "steps": steps,
        "trace": trace,
        "request": {"hospital_sends": {"to": "Vendors (FHIR via middleware) + Collector", "body": "patient_id, provider_id, encounter_id"}},
        "vendor_returns": [s.get("result") for s in steps if s.get("result")],
    }


@app.get("/trace")
def get_trace(patient_id: str = "MRN001", provider_id: str = "NPI123", encounter_id: str = "enc-001"):
    """Fetch trace from collector."""
    patient_id_hash, provider_id_hash = get_hashes(patient_id, provider_id, encounter_id)
    return _fetch_trace(patient_id_hash, provider_id_hash)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
