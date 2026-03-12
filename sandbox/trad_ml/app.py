"""
Trad ML sandbox app - mock sepsis prediction vendor.
Pulls CATE headers, runs mock prediction, logs CATE event to collector.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import FastAPI, Header
import requests
from cate import log_cate_trad_ml

app = FastAPI(title="CATE Trad ML")
COLLECTOR_URL = "http://localhost:8003/events"


def _send_event(event: dict):
    try:
        requests.post(COLLECTOR_URL, json=event, timeout=2)
    except Exception:
        pass


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
def predict(
    x_cate_patient_id_hash: str | None = Header(None, alias="X-CATE-Patient-ID-Hash"),
    x_cate_provider_id_hash: str | None = Header(None, alias="X-CATE-Provider-ID-Hash"),
    body: dict | None = None,
):
    patient_id_hash = x_cate_patient_id_hash
    provider_id_hash = x_cate_provider_id_hash

    prediction = {"label": "high_risk", "probability": 0.87}

    if patient_id_hash and provider_id_hash:
        event = log_cate_trad_ml(
            patient_id_hash=patient_id_hash,
            provider_id_hash=provider_id_hash,
            model_id="sepsis-v2",
            vendor_id="sandbox-trad-ml",
            task_type="risk_prediction",
            output_label=prediction["label"],
            output_probability=prediction["probability"],
        )
        _send_event(event)

    return prediction


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
