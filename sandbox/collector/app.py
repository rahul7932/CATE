"""
Collector sandbox app - receives CATE events, builds traces.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import FastAPI, HTTPException, Body
from cate import build_trace

app = FastAPI(title="CATE Collector")
events: list = []


@app.post("/events")
def add_event(event: dict | None = Body(None)):
    if event:
        events.append(event)
    return {"ok": True}


@app.get("/traces")
def get_traces(patient_id_hash: str | None = None, provider_id_hash: str | None = None):
    if not patient_id_hash or not provider_id_hash:
        raise HTTPException(400, "patient_id_hash and provider_id_hash required")

    matching = [
        e for e in events
        if e.get("patient_id_hash") == patient_id_hash and e.get("provider_id_hash") == provider_id_hash
    ]
    if not matching:
        return {"error": "No events found", "trace": None}

    trace = build_trace(matching)
    return trace


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
