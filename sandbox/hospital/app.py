"""
Hospital sandbox app - simulates EHR API.
Computes CATE hashes and calls vendors with headers.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from pydantic import BaseModel
from cate import compute_patient_hash, compute_provider_hash

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


def get_hashes(patient_id: str, provider_id: str, encounter_id: str):
    patient_id_hash = compute_patient_hash(SECRET, patient_id, encounter_id)
    provider_id_hash = compute_provider_hash(SECRET, provider_id)
    return patient_id_hash, provider_id_hash


class Context(BaseModel):
    patient_id: str = "MRN001"
    provider_id: str = "NPI123"
    encounter_id: str = "enc-001"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
def run_predict(ctx: Context):
    """Call Trad ML vendor for sepsis prediction."""
    patient_id_hash, provider_id_hash = get_hashes(ctx.patient_id, ctx.provider_id, ctx.encounter_id)
    headers = {
        "X-CATE-Patient-ID-Hash": patient_id_hash,
        "X-CATE-Provider-ID-Hash": provider_id_hash,
        "Content-Type": "application/json",
    }
    try:
        r = requests.post(TRAD_ML_URL, json={"vitals": []}, headers=headers, timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        from fastapi import HTTPException
        raise HTTPException(502, str(e))


@app.post("/summarize")
def run_summarize(ctx: Context):
    """Call LLM vendor for note summarization."""
    patient_id_hash, provider_id_hash = get_hashes(ctx.patient_id, ctx.provider_id, ctx.encounter_id)
    headers = {
        "X-CATE-Patient-ID-Hash": patient_id_hash,
        "X-CATE-Provider-ID-Hash": provider_id_hash,
        "Content-Type": "application/json",
    }
    try:
        r = requests.post(
            LLM_URL,
            json={"note": "Patient presents with fever. Labs show elevated WBC."},
            headers=headers,
            timeout=5,
        )
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        from fastapi import HTTPException
        raise HTTPException(502, str(e))


@app.get("/trace")
def get_trace(patient_id: str = "MRN001", provider_id: str = "NPI123", encounter_id: str = "enc-001"):
    """Fetch trace from collector for current provider-patient."""
    patient_id_hash, provider_id_hash = get_hashes(patient_id, provider_id, encounter_id)
    try:
        r = requests.get(
            f"{COLLECTOR_URL}/traces",
            params={"patient_id_hash": patient_id_hash, "provider_id_hash": provider_id_hash},
            timeout=5,
        )
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        from fastapi import HTTPException
        raise HTTPException(502, str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
