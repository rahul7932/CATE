"""
CATE: Clinical AI Telemetry

A minimal SDK for logging clinical AI interactions with anonymous,
non-remappable patient and provider identifiers.
"""

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Literal, Optional

# Enums
MODEL_TYPES = ("trad_ml", "llm")
TRAD_ML_TASK_TYPES = ("diagnosis", "risk_prediction", "treatment_recommendation", "other")
LLM_INTERACTION_TYPES = ("summarization", "drafting", "qa", "documentation", "other")


def compute_patient_hash(
    secret: str,
    patient_id: str,
    encounter_id: str,
    *,
    encoding: str = "utf-8",
) -> str:
    """
    Compute a non-remappable patient identifier hash.

    Same patient + encounter produces the same hash across systems.
    Cannot reverse to identify patient.

    Args:
        secret: Tenant secret (held by hospital only)
        patient_id: Patient identifier (e.g., MRN)
        encounter_id: Encounter identifier
        encoding: String encoding for the message

    Returns:
        64-char hex string

    Example:
        >>> compute_patient_hash("my-secret", "MRN123", "enc-456")
        'a1b2c3d4e5f6...'
    """
    message = f"{patient_id}|{encounter_id}"
    return _hmac_sha256_hex(secret.encode(encoding), message.encode(encoding))


def compute_provider_hash(
    secret: str,
    npi_or_provider_id: str,
    *,
    encoding: str = "utf-8",
) -> str:
    """
    Compute a non-remappable provider identifier hash.

    Same provider produces the same hash across systems.
    Cannot reverse to identify provider.

    Args:
        secret: Tenant secret (held by hospital only)
        npi_or_provider_id: NPI or system provider ID
        encoding: String encoding for the message

    Returns:
        64-char hex string
    """
    return _hmac_sha256_hex(secret.encode(encoding), npi_or_provider_id.encode(encoding))


def _hmac_sha256_hex(key: bytes, message: bytes) -> str:
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def generate_trace_id() -> str:
    """Generate a new trace ID (UUID-based)."""
    return f"tr_{uuid.uuid4().hex[:12]}"


def generate_event_id() -> str:
    """Generate a new event ID."""
    return f"evt_{uuid.uuid4().hex[:12]}"


def create_trad_ml_event(
    trace_id: str,
    patient_id_hash: str,
    provider_id_hash: str,
    model_id: str,
    vendor_id: str,
    task_type: Literal["diagnosis", "risk_prediction", "treatment_recommendation", "other"],
    output_label: str,
    *,
    id: Optional[str] = None,
    timestamp: Optional[str] = None,
    output_probability: Optional[float] = None,
) -> dict[str, Any]:
    """
    Create a Traditional ML event.

    Args:
        trace_id: From hospital (session identifier)
        patient_id_hash: From hospital (supplied with request)
        provider_id_hash: From hospital (supplied with request)
        model_id: Model identifier
        vendor_id: Vendor/system identifier
        task_type: diagnosis, risk_prediction, treatment_recommendation, other
        output_label: Predicted label
        id: Optional event ID (auto-generated if omitted)
        timestamp: Optional ISO 8601 (now if omitted)
        output_probability: Optional 0.0-1.0

    Returns:
        Event dict ready for JSON serialization
    """
    event: dict[str, Any] = {
        "id": id or generate_event_id(),
        "trace_id": trace_id,
        "timestamp": timestamp or _now_iso(),
        "model_type": "trad_ml",
        "model_id": model_id,
        "vendor_id": vendor_id,
        "patient_id_hash": patient_id_hash,
        "provider_id_hash": provider_id_hash,
        "task_type": task_type,
        "output_label": output_label,
    }
    if output_probability is not None:
        event["output_probability"] = output_probability
    return event


def create_llm_event(
    trace_id: str,
    patient_id_hash: str,
    provider_id_hash: str,
    model_id: str,
    vendor_id: str,
    interaction_type: Literal["summarization", "drafting", "qa", "documentation", "other"],
    *,
    id: Optional[str] = None,
    timestamp: Optional[str] = None,
    output_token_count: Optional[int] = None,
) -> dict[str, Any]:
    """
    Create a Clinical LLM event.

    Args:
        trace_id: From hospital (session identifier)
        patient_id_hash: From hospital (supplied with request)
        provider_id_hash: From hospital (supplied with request)
        model_id: Model identifier
        vendor_id: Vendor/system identifier
        interaction_type: summarization, drafting, qa, documentation, other
        id: Optional event ID (auto-generated if omitted)
        timestamp: Optional ISO 8601 (now if omitted)
        output_token_count: Optional

    Returns:
        Event dict ready for JSON serialization
    """
    event: dict[str, Any] = {
        "id": id or generate_event_id(),
        "trace_id": trace_id,
        "timestamp": timestamp or _now_iso(),
        "model_type": "llm",
        "model_id": model_id,
        "vendor_id": vendor_id,
        "patient_id_hash": patient_id_hash,
        "provider_id_hash": provider_id_hash,
        "interaction_type": interaction_type,
    }
    if output_token_count is not None:
        event["output_token_count"] = output_token_count
    return event


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def build_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Build a trace from a list of events.

    Groups events by trace_id and derives start_time, end_time, patient_id_hash, provider_id_hash
    from the first event.

    Args:
        events: List of CATE events (must share same trace_id)

    Returns:
        Trace dict with events, start_time, end_time
    """
    if not events:
        raise ValueError("events must not be empty")

    trace_id = events[0]["trace_id"]
    patient_id_hash = events[0]["patient_id_hash"]
    provider_id_hash = events[0]["provider_id_hash"]

    timestamps = [e["timestamp"] for e in events]
    start_time = min(timestamps)
    end_time = max(timestamps)

    return {
        "trace_id": trace_id,
        "patient_id_hash": patient_id_hash,
        "provider_id_hash": provider_id_hash,
        "start_time": start_time,
        "end_time": end_time,
        "events": events,
    }


def validate_event(event: dict[str, Any]) -> list[str]:
    """
    Validate an event against the spec. Returns list of error messages (empty if valid).

    Does not perform full JSON Schema validation; checks required fields and basic constraints.
    """
    errors: list[str] = []
    required = ["id", "trace_id", "timestamp", "model_type", "model_id", "vendor_id", "patient_id_hash", "provider_id_hash"]
    for field in required:
        if field not in event:
            errors.append(f"Missing required field: {field}")
        elif event[field] is None or event[field] == "":
            errors.append(f"Field {field} must not be empty")

    if event.get("model_type") == "trad_ml":
        if "task_type" not in event:
            errors.append("trad_ml events require task_type")
        elif event["task_type"] not in TRAD_ML_TASK_TYPES:
            errors.append(f"task_type must be one of {TRAD_ML_TASK_TYPES}")
        if "output_label" not in event:
            errors.append("trad_ml events require output_label")
        if "output_probability" in event and not (0 <= event["output_probability"] <= 1):
            errors.append("output_probability must be 0.0-1.0")

    elif event.get("model_type") == "llm":
        if "interaction_type" not in event:
            errors.append("llm events require interaction_type")
        elif event["interaction_type"] not in LLM_INTERACTION_TYPES:
            errors.append(f"interaction_type must be one of {LLM_INTERACTION_TYPES}")

    if event.get("model_type") not in MODEL_TYPES:
        errors.append(f"model_type must be one of {MODEL_TYPES}")

    return errors


__all__ = [
    "compute_patient_hash",
    "compute_provider_hash",
    "generate_trace_id",
    "generate_event_id",
    "create_trad_ml_event",
    "create_llm_event",
    "build_trace",
    "validate_event",
    "MODEL_TYPES",
    "TRAD_ML_TASK_TYPES",
    "LLM_INTERACTION_TYPES",
]
