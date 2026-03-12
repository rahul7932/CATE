"""
Trad ML sandbox app - mock sepsis prediction vendor.
Calls FHIR via middleware to fetch vitals, runs mock prediction.
Middleware logs FHIR access; vendor no longer logs CATE events.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI(title="CATE Trad ML")
FHIR_URL = "http://localhost:8080"


class PredictBody(BaseModel):
    patient_id: str = "MRN001"
    provider_id: str = "NPI123"
    encounter_id: str = "enc-001"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
def predict(body: PredictBody | None = None):
    patient_id = (body.patient_id if body else None) or "MRN001"
    headers = {"X-Vendor-ID": "sandbox-trad-ml"}
    fhir_url = f"{FHIR_URL}/Observation?patient=Patient/{patient_id}"
    try:
        r = requests.get(fhir_url, headers=headers, timeout=5)
        r.raise_for_status()
        observations = r.json()
    except requests.RequestException:
        observations = {"entry": []}

    vitals = []
    if isinstance(observations, dict) and "entry" in observations:
        for e in observations.get("entry", []):
            res = e.get("resource", {})
            if res.get("resourceType") == "Observation":
                vq = res.get("valueQuantity", {})
                vitals.append({"value": vq.get("value"), "unit": vq.get("unit")})

    prediction = {"label": "high_risk", "probability": 0.87}
    return prediction


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
