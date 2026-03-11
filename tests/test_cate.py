"""Tests for CATE SDK."""

import pytest
from cate import (
    compute_patient_hash,
    compute_provider_hash,
    generate_trace_id,
    generate_event_id,
    create_trad_ml_event,
    create_llm_event,
    build_trace,
    validate_event,
)


def test_compute_patient_hash_deterministic():
    secret = "test-secret"
    h1 = compute_patient_hash(secret, "MRN123", "enc-456")
    h2 = compute_patient_hash(secret, "MRN123", "enc-456")
    assert h1 == h2
    assert len(h1) == 64
    assert all(c in "0123456789abcdef" for c in h1)


def test_compute_patient_hash_different_inputs():
    secret = "test-secret"
    h1 = compute_patient_hash(secret, "MRN123", "enc-456")
    h2 = compute_patient_hash(secret, "MRN124", "enc-456")
    h3 = compute_patient_hash(secret, "MRN123", "enc-457")
    assert h1 != h2 != h3


def test_compute_provider_hash_deterministic():
    secret = "test-secret"
    h1 = compute_provider_hash(secret, "1234567890")
    h2 = compute_provider_hash(secret, "1234567890")
    assert h1 == h2
    assert len(h1) == 64


def test_generate_trace_id():
    t = generate_trace_id()
    assert t.startswith("tr_")
    assert len(t) == 15  # tr_ + 12 hex chars


def test_generate_event_id():
    e = generate_event_id()
    assert e.startswith("evt_")
    assert len(e) == 16


def test_create_trad_ml_event():
    event = create_trad_ml_event(
        trace_id="tr_abc",
        patient_id_hash="ph1",
        provider_id_hash="pr1",
        model_id="sepsis-v2",
        vendor_id="acme",
        task_type="risk_prediction",
        output_label="high_risk",
        output_probability=0.87,
    )
    assert event["model_type"] == "trad_ml"
    assert event["task_type"] == "risk_prediction"
    assert event["output_label"] == "high_risk"
    assert event["output_probability"] == 0.87
    assert "id" in event
    assert "timestamp" in event


def test_create_llm_event():
    event = create_llm_event(
        trace_id="tr_abc",
        patient_id_hash="ph1",
        provider_id_hash="pr1",
        model_id="llm-1",
        vendor_id="docu",
        interaction_type="summarization",
        output_token_count=200,
    )
    assert event["model_type"] == "llm"
    assert event["interaction_type"] == "summarization"
    assert event["output_token_count"] == 200
    assert "id" in event
    assert "timestamp" in event


def test_build_trace():
    e1 = create_trad_ml_event(
        trace_id="tr_abc",
        patient_id_hash="ph1",
        provider_id_hash="pr1",
        model_id="m1",
        vendor_id="v1",
        task_type="risk_prediction",
        output_label="high",
        timestamp="2025-03-10T14:32:00Z",
    )
    e2 = create_llm_event(
        trace_id="tr_abc",
        patient_id_hash="ph1",
        provider_id_hash="pr1",
        model_id="m2",
        vendor_id="v2",
        interaction_type="summarization",
        timestamp="2025-03-10T14:35:00Z",
    )
    trace = build_trace([e1, e2])
    assert trace["trace_id"] == "tr_abc"
    assert trace["patient_id_hash"] == "ph1"
    assert trace["provider_id_hash"] == "pr1"
    assert trace["start_time"] == "2025-03-10T14:32:00Z"
    assert trace["end_time"] == "2025-03-10T14:35:00Z"
    assert len(trace["events"]) == 2


def test_build_trace_empty_raises():
    with pytest.raises(ValueError, match="must not be empty"):
        build_trace([])


def test_validate_event_valid_trad_ml():
    event = create_trad_ml_event(
        trace_id="tr_abc",
        patient_id_hash="ph1",
        provider_id_hash="pr1",
        model_id="m1",
        vendor_id="v1",
        task_type="risk_prediction",
        output_label="high",
    )
    assert validate_event(event) == []


def test_validate_event_valid_llm():
    event = create_llm_event(
        trace_id="tr_abc",
        patient_id_hash="ph1",
        provider_id_hash="pr1",
        model_id="m1",
        vendor_id="v1",
        interaction_type="summarization",
    )
    assert validate_event(event) == []


def test_validate_event_missing_required():
    event = {"model_type": "trad_ml"}
    errors = validate_event(event)
    assert "Missing required field" in errors[0]


def test_validate_event_trad_ml_missing_task_type():
    event = {
        "id": "evt_1",
        "trace_id": "tr_1",
        "timestamp": "2025-03-10T14:32:00Z",
        "model_type": "trad_ml",
        "model_id": "m1",
        "vendor_id": "v1",
        "patient_id_hash": "ph1",
        "provider_id_hash": "pr1",
        "output_label": "high",
    }
    errors = validate_event(event)
    assert "task_type" in str(errors).lower()


def test_validate_event_invalid_probability():
    event = create_trad_ml_event(
        trace_id="tr_abc",
        patient_id_hash="ph1",
        provider_id_hash="pr1",
        model_id="m1",
        vendor_id="v1",
        task_type="risk_prediction",
        output_label="high",
        output_probability=1.5,
    )
    errors = validate_event(event)
    assert "output_probability" in str(errors).lower()
