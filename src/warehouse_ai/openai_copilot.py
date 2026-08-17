from __future__ import annotations

import os
from typing import Any, Dict


def explain_with_openai(question: str, evidence: Dict[str, Any]) -> str:
    """Optionally explain deterministic evidence with OpenAI; unavailable configuration is explicit."""
    if not os.getenv('OPENAI_API_KEY'):
        return 'OPENAI_API_KEY is not configured. Use the deterministic evidence response in the dashboard.'
    try:
        from openai import OpenAI
    except ImportError:
        return 'The OpenAI client is not installed. Install the optional openai dependency to enable narrative explanations.'
    client = OpenAI()
    response = client.responses.create(model=os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'), input=[
        {'role': 'system', 'content': 'Use only the supplied evidence. If it is insufficient, say so. Do not calculate or invent warehouse metrics.'},
        {'role': 'user', 'content': f'Question: {question}\nEvidence: {evidence}'},
    ])
    return response.output_text