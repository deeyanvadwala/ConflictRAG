"""One small wrapper around the LLM providers.

    from llm import complete
    text = complete("prompt")            # uses llm_provider from config.yaml
    text = complete("prompt", provider="ollama")

All calls use plain HTTP (requests), so no provider SDK is needed.
API keys are read from .env and are never printed.

To list the Gemini models your key can use:
    python llm.py --list-models
"""
import os
import sys
import time

import requests
from dotenv import load_dotenv

from chunking import CFG

load_dotenv()  # reads .env in the current folder into environment variables

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
RETRY_STATUS = {429, 500, 502, 503, 504}  # rate limit or temporary server error


class LLMError(RuntimeError):
    pass


def _key(name):
    key = os.environ.get(name)
    if not key:
        raise LLMError(f"{name} is not set. Add it to .env (never commit that file).")
    return key


def _post(url, headers, body, timeout=120):
    """POST with a few retries on rate limits. Error messages never include headers (keys)."""
    for attempt in range(4):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=timeout)
        except requests.RequestException as e:
            raise LLMError(f"network error: {type(e).__name__}") from None
        if r.status_code in RETRY_STATUS and attempt < 3:
            wait = 10 * 2 ** attempt
            print(f"[llm] HTTP {r.status_code}, retrying in {wait}s...", file=sys.stderr)
            time.sleep(wait)
            continue
        if not r.ok:
            raise LLMError(f"HTTP {r.status_code}: {r.text[:500]}")
        return r.json()


def _gemini(prompt, model):
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": CFG["temperature"],
            "maxOutputTokens": CFG["max_output_tokens"],
            "seed": CFG["seed"],
        },
    }
    headers = {"x-goog-api-key": _key("GEMINI_API_KEY")}  # key in a header, not the URL
    data = _post(f"{GEMINI_URL}/models/{model}:generateContent", headers, body)
    cands = data.get("candidates") or []
    if not cands:
        raise LLMError(f"no answer returned; promptFeedback={data.get('promptFeedback')}")
    parts = cands[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    finish = cands[0].get("finishReason")
    if finish != "STOP":
        print(f"[llm] warning: finishReason={finish} (answer may be cut off or blocked)", file=sys.stderr)
    return text


def _ollama(prompt, model):
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": CFG["temperature"],
            "num_predict": CFG["max_output_tokens"],
            "seed": CFG["seed"],
        },
    }
    try:
        return _post(f"{CFG['ollama_url']}/api/generate", {}, body, timeout=600)["response"]
    except LLMError as e:
        raise LLMError(f"{e}. Is Ollama running and has `ollama pull {model}` been done?") from None


def _anthropic(prompt, model):
    # Paid API: not used under the $0 budget. Kept so the wrapper matches the plan.
    body = {
        "model": model,
        "max_tokens": CFG["max_output_tokens"],
        "temperature": CFG["temperature"],
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {"x-api-key": _key("ANTHROPIC_API_KEY"), "anthropic-version": "2023-06-01"}
    data = _post(ANTHROPIC_URL, headers, body)
    return "".join(b.get("text", "") for b in data["content"] if b["type"] == "text")


PROVIDERS = {"gemini": _gemini, "ollama": _ollama, "anthropic": _anthropic}


def complete(prompt, provider=None, model=None):
    """Send one prompt, return the model's text."""
    provider = provider or CFG["llm_provider"]
    if provider not in PROVIDERS:
        raise LLMError(f"unknown provider {provider!r}; choose from {list(PROVIDERS)}")
    model = model or CFG["llm_models"][provider]
    if not model or model == "SET_ME":
        raise LLMError(f"set llm_models.{provider} in config.yaml (see: python llm.py --list-models)")
    return PROVIDERS[provider](prompt, model)


def list_gemini_models():
    r = requests.get(f"{GEMINI_URL}/models", headers={"x-goog-api-key": _key("GEMINI_API_KEY")},
                     params={"pageSize": 1000}, timeout=30)
    if not r.ok:
        raise LLMError(f"HTTP {r.status_code}: {r.text[:500]}")
    for m in r.json().get("models", []):
        if "generateContent" in m.get("supportedGenerationMethods", []):
            print(m["name"].removeprefix("models/"))


if __name__ == "__main__":
    if sys.argv[1:] == ["--list-models"]:
        list_gemini_models()
    else:
        print('usage: python llm.py --list-models   (or import complete() from llm)')
