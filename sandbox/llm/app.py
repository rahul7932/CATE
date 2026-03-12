"""
Clinical LLM sandbox app - mock note summarization vendor.
Pulls CATE headers, runs mock summarization, logs CATE event to collector.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import FastAPI, Header
from pydantic import BaseModel
import requests
from cate import log_cate_llm

app = FastAPI(title="CATE LLM")
COLLECTOR_URL = "http://localhost:8003/events"


def _send_event(event: dict):
    try:
        requests.post(COLLECTOR_URL, json=event, timeout=2)
    except Exception:
        pass


@app.get("/health")
def health():
    return {"status": "ok"}


class SummarizeBody(BaseModel):
    note: str = ""


@app.post("/summarize")
def summarize(
    x_cate_patient_id_hash: str | None = Header(None, alias="X-CATE-Patient-ID-Hash"),
    x_cate_provider_id_hash: str | None = Header(None, alias="X-CATE-Provider-ID-Hash"),
    body: SummarizeBody | None = None,
):
    patient_id_hash = x_cate_patient_id_hash
    provider_id_hash = x_cate_provider_id_hash

    note = (body.note if body else "") or ""
    summary = f"[Mock summary] Key points: fever, elevated WBC. ({len(note)} chars in input)"

    if patient_id_hash and provider_id_hash:
        event = log_cate_llm(
            patient_id_hash=patient_id_hash,
            provider_id_hash=provider_id_hash,
            model_id="clinical-llm-1.0",
            vendor_id="sandbox-llm",
            interaction_type="summarization",
            output_token_count=len(summary.split()),
        )
        _send_event(event)

    return {"summary": summary}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
