"""
Nexus - LLM Provider Abstraction
Supports Gemini (Google) and WatsonX (IBM) for DPR generation.
Set environment variables to choose provider:
  - GEMINI_API_KEY     → uses Gemini 2.5 Flash
  - WATSONX_API_KEY    → uses IBM Granite via WatsonX
  - WATSONX_PROJECT_ID → required for WatsonX
  - WATSONX_URL        → WatsonX endpoint (default: us-south)
"""
import os, json, re, sys

def get_llm_provider():
    """Auto-detect which LLM provider is configured."""
    if os.environ.get("WATSONX_API_KEY"):
        return "watsonx"
    elif os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return "gemini"
    else:
        print("ERROR: No LLM provider configured.")
        print("  Set one of:")
        print("    $env:GEMINI_API_KEY='...'")
        print("    $env:WATSONX_API_KEY='...' + $env:WATSONX_PROJECT_ID='...'")
        sys.exit(1)


def call_llm(prompt, provider=None):
    """
    Call the configured LLM with a prompt. Returns text response.
    Supports: gemini, watsonx
    """
    if provider is None:
        provider = get_llm_provider()

    if provider == "gemini":
        return _call_gemini(prompt)
    elif provider == "watsonx":
        return _call_watsonx(prompt)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


# ── Gemini ─────────────────────────────────────────────────
def _call_gemini(prompt):
    """Call Google Gemini 2.5 Flash."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")

    from google import genai
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text.strip()


# ── IBM WatsonX ────────────────────────────────────────────
def _call_watsonx(prompt):
    """Call IBM WatsonX with Granite model."""
    api_key = os.environ.get("WATSONX_API_KEY")
    project_id = os.environ.get("WATSONX_PROJECT_ID")
    url = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

    if not api_key:
        raise ValueError("WATSONX_API_KEY not set")
    if not project_id:
        raise ValueError("WATSONX_PROJECT_ID not set")

    from ibm_watsonx_ai import Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference

    credentials = Credentials(url=url, api_key=api_key)

    # Use IBM Granite 3.3 (latest code-capable model)
    model = ModelInference(
        model_id="ibm/granite-3-3-8b-instruct",
        credentials=credentials,
        project_id=project_id,
        params={
            "max_new_tokens": 8000,
            "temperature": 0.2,
            "top_p": 0.9,
            "repetition_penalty": 1.05,
        },
    )

    response = model.generate_text(prompt=prompt)
    return response.strip()


def parse_json_response(text):
    """Clean and parse JSON from LLM response."""
    # Strip markdown code fences
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s*```\s*$', '', text, flags=re.MULTILINE)
    text = text.strip()
    return json.loads(text)
