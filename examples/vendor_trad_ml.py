"""
Vendor example: Traditional ML

Shows pulling CATE context from request headers and putting it into the event.
Hospital sends: X-CATE-Patient-ID-Hash, X-CATE-Provider-ID-Hash
"""

from cate import log_cate_trad_ml

# Simulate request headers (hospital sends these with every API call)
REQUEST_HEADERS = {
    "X-CATE-Patient-ID-Hash": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456",
    "X-CATE-Provider-ID-Hash": "d4e5f6789012345678901234567890abcdef1234567890abcdef1234567890",
}


def handle_prediction_request(headers: dict, model_output: dict) -> dict:
    """
    Vendor handler: pull CATE headers, run model, log event.
    """
    # 1. Pull CATE context from headers
    patient_id_hash = headers.get("X-CATE-Patient-ID-Hash")
    provider_id_hash = headers.get("X-CATE-Provider-ID-Hash")

    # 2. Run model (vendor logic)
    # prediction = model.predict(input_data)

    # 3. Create event — pass through the header values into the event
    event = log_cate_trad_ml(
        patient_id_hash=patient_id_hash,
        provider_id_hash=provider_id_hash,
        model_id="sepsis-v2",
        vendor_id="acme",
        task_type="risk_prediction",
        output_label=model_output["label"],
        output_probability=model_output["probability"],
    )

    return event


if __name__ == "__main__":
    # Example: hospital sends headers, model returns prediction
    model_output = {"label": "high_risk", "probability": 0.87}
    event = handle_prediction_request(REQUEST_HEADERS, model_output)
    print(event)
