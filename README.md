<p align="center">
  <img src="https://img.shields.io/badge/CATE-Clinical%20AI%20Telemetry-2563eb?style=for-the-badge" alt="CATE" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-CC%20BY%204.0-blue.svg" alt="License: CC BY 4.0" />
  <img src="https://img.shields.io/badge/python-3.10+-3776ab?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/spec-v0.1.0-22c55e.svg" alt="Spec" />
</p>

<p align="center">
  <strong>Provenance logging for clinical AI</strong> — anonymous, non-remappable patient and provider identifiers
</p>

---

## Overview

**CATE** (Clinical AI Telemetry) is a minimal specification and SDK for logging clinical AI interactions—both traditional ML (predictions, risk scores) and LLMs (summarization, drafting)—with audit trails that support medical malpractice defense.

**Key features:**

- **Anonymous identity** — Hospitals compute patient/provider hashes; vendors never see raw IDs
- **Trace grouping** — Events group by provider–patient session for unified timelines
- **ATNA integration** — Include IHE ATNA audit logs in traces for full context
- **Spec-first** — JSON schema, clear spec, minimal vendor integration burden

---

## Installation

```bash
pip install -e .
```

Or with a virtual environment:

```bash
python -m venv .venv && source .venv/bin/activate  # Linux/macOS
pip install -e .
```

---

## Quick Start

### Hospital: Compute identity hashes

```python
from cate import compute_patient_hash, compute_provider_hash, generate_trace_id

# When a session starts (e.g., provider opens chart)
trace_id = generate_trace_id()
patient_id_hash = compute_patient_hash(secret="your-tenant-secret", patient_id="MRN123", encounter_id="enc-456")
provider_id_hash = compute_provider_hash(secret="your-tenant-secret", npi="1234567890")

# Include in every vendor request
```

### Hospital: Include in vendor requests

Send with each request (headers or body):

| Header | Description |
|--------|-------------|
| `X-CATE-Trace-ID` | Trace ID (generated when session starts) |
| `X-CATE-Patient-ID-Hash` | Patient hash |
| `X-CATE-Provider-ID-Hash` | Provider hash |

### Vendor: Log events

```python
from cate import create_trad_ml_event, create_llm_event

# Traditional ML
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

# LLM
event = create_llm_event(
    trace_id="tr_550e8400e29b",
    patient_id_hash="a1b2c3...",
    provider_id_hash="d4e5f6...",
    model_id="clinical-llm-1.0",
    vendor_id="docu-ai",
    interaction_type="summarization",
    output_token_count=200,
)
```

### Platform: Build traces

```python
from cate import build_trace

trace = build_trace(events)
# trace_id, patient_id_hash, provider_id_hash, start_time, end_time, events
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Hospital (EHR)                                                          │
│  • Has patient_id, provider_id, secret                                  │
│  • Generates trace_id when session starts                                │
│  • Computes hashes with HMAC-SHA256                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │  trace_id, patient_id_hash, provider_id_hash
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Vendor (AI)                                                             │
│  • Receives hashes from hospital                                         │
│  • Runs model, returns result                                            │
│  • Logs CATE event with received hashes                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │  events
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Platform                                                                │
│  • Aggregates events by trace_id                                         │
│  • Builds traces (provider–patient timeline)                              │
│  • Optionally merges ATNA audit events                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
CATE/
├── README.md
├── pyproject.toml
├── spec/
│   ├── overview.md          # Full specification
│   └── atna-extension.md    # ATNA integration
├── schemas/
│   ├── event.schema.json
│   └── trace.schema.json
├── cate/
│   └── __init__.py          # Python SDK
├── examples/
│   ├── trad-ml.json
│   └── llm.json
└── tests/
```

---

## Specification

| Document | Description |
|----------|-------------|
| [spec/overview.md](spec/overview.md) | Full spec: request flow, trace, event, identity |
| [spec/atna-extension.md](spec/atna-extension.md) | ATNA integration: add trace_id to audit logs |
| [schemas/event.schema.json](schemas/event.schema.json) | JSON Schema for events |
| [schemas/trace.schema.json](schemas/trace.schema.json) | JSON Schema for traces |

---

## API Reference

| Function | Description |
|----------|-------------|
| `compute_patient_hash(secret, patient_id, encounter_id)` | HMAC-SHA256 patient hash |
| `compute_provider_hash(secret, npi_or_provider_id)` | HMAC-SHA256 provider hash |
| `generate_trace_id()` | New trace ID |
| `generate_event_id()` | New event ID |
| `create_trad_ml_event(...)` | Create traditional ML event |
| `create_llm_event(...)` | Create LLM event |
| `build_trace(events)` | Build trace from events |
| `validate_event(event)` | Validate event (returns list of errors) |

---

## License

Creative Commons Attribution 4.0 International (CC BY 4.0). See [LICENSE](LICENSE) for details.
