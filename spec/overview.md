# CATE: Clinical AI Telemetry (Specification)

## Goal

A way to log trad ML or clinical LLM interactions with some level of detail, and specify anonymously and in a non-remappable way which patient (and provider) it's for.

---

## 1. Request Flow

The **hospital (EHR)** supplies `patient_id_hash` and `provider_id_hash` with each request to the vendor. The vendor never sees raw patient IDs or the hashing secret.

```
Hospital (has patient_id, provider_id, secret)
    → computes hashes (patient_id_hash includes encounter_id)
    → sends request to vendor WITH patient_id_hash, provider_id_hash (header or body)
    → Vendor receives hashes, runs AI, returns result
    → Vendor logs event using the hashes it received
```

**Hospital responsibility:** Compute hashes and include `patient_id_hash`, `provider_id_hash` on every vendor request.

**Vendor responsibility:** Accept these from the caller, include them in each event. Never compute hashes; never receive raw patient ID or secret.

**Recommended request format:** `X-CATE-Patient-ID-Hash`, `X-CATE-Provider-ID-Hash` (or equivalent in body).

---

## 2. Trace

A **Trace** groups all AI interactions for a single provider–patient encounter. The platform derives traces by grouping events on `(provider_id_hash, patient_id_hash)`—`patient_id_hash` already encodes the encounter.

| Field              | Type   | Description                           |
| ------------------ | ------ | ------------------------------------- |
| `patient_id_hash`  | string | Same as events                        |
| `provider_id_hash` | string | Same as events                        |
| `start_time`       | string | Earliest event timestamp (derived)    |
| `end_time`         | string | Latest event timestamp (derived)     |
| `events`           | array  | CATE events in this trace             |
| `atna_events`      | array  | ATNA events in this trace (optional)  |

### ATNA Integration

Hospital adds `patient_id_hash` and `provider_id_hash` to ATNA events when they occur during an active CATE session. Platform correlates by matching these hashes.

---

## 3. Event

One event per AI interaction. Two variants by `model_type`.

### Required (all events)

| Field              | Type   | Description                               |
| ------------------ | ------ | ----------------------------------------- |
| `id`               | string | Unique event ID                           |
| `timestamp`        | string | ISO 8601                                  |
| `model_type`       | string | `trad_ml` or `llm`                         |
| `model_id`         | string | Model identifier                          |
| `vendor_id`        | string | Vendor/system                             |
| `patient_id_hash`  | string | Supplied by caller; vendor passes through  |
| `provider_id_hash` | string | Supplied by caller; vendor passes through |

### Trad ML only

| Field                | Type   | Description                                                 |
| -------------------- | ------ | ----------------------------------------------------------- |
| `task_type`          | string | diagnosis, risk_prediction, treatment_recommendation, other |
| `output_label`       | string | Predicted label                                             |
| `output_probability` | number | 0.0–1.0 (optional)                                          |

### LLM only

| Field                | Type   | Description                                       |
| -------------------- | ------ | ------------------------------------------------- |
| `interaction_type`   | string | summarization, drafting, qa, documentation, other |
| `output_token_count` | number | Optional                                          |

---

## 4. Identity (Non-Remappable Hashing)

**Computed by the hospital only.** Vendors never compute hashes.

**Patient:** `patient_id_hash = HMAC-SHA256(tenant_secret, patient_id + encounter_id)`

**Provider:** `provider_id_hash = HMAC-SHA256(tenant_secret, npi_or_provider_id)`

**Tenant secret** is held by the hospital; never shared with vendors or aggregation platform.

---

## 5. Enums

- `model_type`: `trad_ml`, `llm`
- `trad_ml_task_type`: `diagnosis`, `risk_prediction`, `treatment_recommendation`, `other`
- `llm_interaction_type`: `summarization`, `drafting`, `qa`, `documentation`, `other`
