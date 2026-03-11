"""
Vendor example: Clinical LLM

Shows pulling CATE context from request headers and putting it into the event.
Hospital sends: X-CATE-Trace-ID, X-CATE-Patient-ID-Hash, X-CATE-Provider-ID-Hash
"""

from cate import log_cate_llm

# Simulate request headers (hospital sends these with every API call)
REQUEST_HEADERS = {
    "X-CATE-Trace-ID": "tr_550e8400e29b",
    "X-CATE-Patient-ID-Hash": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456",
    "X-CATE-Provider-ID-Hash": "d4e5f6789012345678901234567890abcdef1234567890abcdef1234567890",
}


def handle_llm_request(headers: dict, interaction_type: str, output_token_count: int) -> dict:
    """
    Vendor handler: pull CATE headers, run LLM, log event.
    """
    # 1. Pull CATE context from headers
    trace_id = headers.get("X-CATE-Trace-ID")
    patient_id_hash = headers.get("X-CATE-Patient-ID-Hash")
    provider_id_hash = headers.get("X-CATE-Provider-ID-Hash")

    # 2. Run LLM (vendor logic)
    # response = llm.generate(prompt)

    # 3. Create event — pass through the header values into the event
    event = log_cate_llm(
        trace_id=trace_id,
        patient_id_hash=patient_id_hash,
        provider_id_hash=provider_id_hash,
        model_id="clinical-llm-1.0",
        vendor_id="docu-ai",
        interaction_type=interaction_type,
        output_token_count=output_token_count,
    )

    return event


if __name__ == "__main__":
    # Example: hospital sends headers, LLM returns summarization
    event = handle_llm_request(
        REQUEST_HEADERS,
        interaction_type="summarization",
        output_token_count=200,
    )
    print(event)
