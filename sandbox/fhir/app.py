"""
Mock FHIR server for sandbox - minimal FHIR R4 responses.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import FastAPI, Query

app = FastAPI(title="Mock FHIR Server")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/Patient/{patient_id}")
def get_patient(patient_id: str):
    return {
        "resourceType": "Patient",
        "id": patient_id,
        "identifier": [{"system": "http://hospital.org/mrn", "value": patient_id}],
        "name": [{"family": "Demo", "given": ["Patient"]}],
    }


@app.get("/Observation")
def search_observation(patient: str | None = Query(None, alias="patient")):
    patient_id = "unknown"
    if patient:
        if "Patient/" in patient:
            patient_id = patient.split("Patient/")[-1].split("|")[0]
        else:
            patient_id = patient
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": 2,
        "entry": [
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs-1",
                    "subject": {"reference": f"Patient/{patient_id}"},
                    "code": {"coding": [{"code": "8867-4", "display": "Heart rate"}]},
                    "valueQuantity": {"value": 72, "unit": "beats/minute"},
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs-2",
                    "subject": {"reference": f"Patient/{patient_id}"},
                    "code": {"coding": [{"code": "8310-5", "display": "Body temperature"}]},
                    "valueQuantity": {"value": 98.6, "unit": "degF"},
                }
            },
        ],
    }


@app.get("/Condition")
def search_condition(subject: str | None = Query(None, alias="subject")):
    patient_id = "unknown"
    if subject:
        if "Patient/" in subject:
            patient_id = subject.split("Patient/")[-1].split("|")[0]
        else:
            patient_id = subject
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": 0,
        "entry": [],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
