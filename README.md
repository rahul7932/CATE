# CATE: Clinical AI Telemetry

A minimal specification for logging clinical AI interactions (trad ML or LLM) with anonymous, non-remappable patient and provider identifiers.

## Goal

Enable hospitals to:
- Log AI interactions with some level of detail
- Specify anonymously which patient and provider each interaction is for
- Build traces that group events by provider–patient session
- Integrate with ATNA audit logs for unified timelines

## Installation

```bash
pip install -e .
# or with venv:
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Quick Start

### Hospital: Compute identity hashes

```python
from cate import compute_patient_hash, compute_provider_hash

patient_id_hash = compute_patient_hash(secret="your-tenant-secret", patient_id="MRN123", encounter_id="enc-456")
provider_id_hash = compute_provider_hash(secret="your-tenant-secret", npi="1234567890")
```

### Hospital: Include in vendor requests

Send with each request (headers or body):
- `X-CATE-Trace-ID`: trace_id (UUID, generated when session starts)
- `X-CATE-Patient-ID-Hash`: patient_id_hash
- `X-CATE-Provider-ID-Hash`: provider_id_hash

### Vendor: Log events

```python
from cate import create_trad_ml_event, create_llm_event

event = create_trad_ml_event(
    trace_id="tr_550e8400e29b",
    patient_id_hash="a1b2c3...",
    provider_id_hash="d4e5f6...",
    model_id="sepsis-v2",
    vendor_id="acme",
    task_type="risk_prediction",
    output_label="high_risk",
    output_probability=0.87,
)
```

## Project Structure

```
CATE/
├── README.md
├── spec/
│   └── overview.md       # Full specification
├── schemas/
│   ├── event.schema.json
│   └── trace.schema.json
├── cate/
│   └── __init__.py       # Python SDK
├── examples/
│   ├── trad-ml.json
│   └── llm.json
└── tests/
```

## License

MIT
