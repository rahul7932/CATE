"""
Clinical LLM sandbox app - mock note summarization vendor.
Calls FHIR via middleware to fetch notes (optional), runs mock summarization.
Middleware logs FHIR access; vendor no longer logs CATE events.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI(title="CATE LLM")
FHIR_URL = "http://localhost:8080"


class SummarizeBody(BaseModel):
    patient_id: str = "MRN001"
    provider_id: str = "NPI123"
    encounter_id: str = "enc-001"
    note: str = ""


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/summarize")
def summarize(body: SummarizeBody | None = None):
    patient_id = (body.patient_id if body else None) or "MRN001"
    note = (body.note if body else "") or ""

    if not note:
        headers = {"X-Vendor-ID": "sandbox-llm"}
        fhir_url = f"{FHIR_URL}/Observation?patient=Patient/{patient_id}"
        try:
            r = requests.get(fhir_url, headers=headers, timeout=5)
            r.raise_for_status()
            obs = r.json()
            entries = obs.get("entry", []) if isinstance(obs, dict) else []
            note = " ".join(
                str(e.get("resource", {}).get("valueQuantity", {}).get("value", ""))
                for e in entries[:3]
            ) or "No observations"
        except requests.RequestException:
            note = "Patient presents with fever. Labs show elevated WBC."

    summary = f"[Mock summary] Key points: fever, elevated WBC. ({len(note)} chars in input)"
    return {"summary": summary}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
