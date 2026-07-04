# llm_client.py
# Wraps Ollama's REST API for both text and vision (image) inference.
# All inference is 100% local — no internet required.

from __future__ import annotations

import json
from typing import Optional

import requests

import config
from config import (
    OLLAMA_BASE_URL,
    OLLAMA_TIMEOUT,
    SYSTEM_PROMPT,
    GLOBAL_SUMMARY_PROMPT,
)


# ── Connection check ───────────────────────────────────────────────────────

def check_ollama_running() -> bool:
    """Returns True if Ollama server is reachable."""
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return r.status_code == 200
    except requests.ConnectionError:
        return False


def list_available_models() -> list[str]:
    """Returns model names currently pulled in Ollama."""
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        data = r.json()
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def get_text_model() -> str:
    """
    Always reads the model name fresh from config.
    Ensures we never accidentally route to a cloud/wrong model.
    """
    return config.OLLAMA_MODEL


def get_vision_model() -> str:
    """Always reads the vision model name fresh from config."""
    return config.OLLAMA_VISION_MODEL


# ── Core LLM call ──────────────────────────────────────────────────────────

def _call_ollama(
    model:   str,
    prompt:  str,
    system:  str = "",
    images:  Optional[list[str]] = None,
) -> str:
    """
    Low-level POST to /api/generate.
    Explicitly sets the model on every call to prevent Ollama
    from routing to a cloud model or wrong local model.
    Returns the full response text or raises on error.
    """
    # Safety check — never send an empty model name
    if not model or model.strip() == "":
        raise ValueError("Model name is empty. Check config.py OLLAMA_MODEL setting.")

    payload: dict = {
        "model":  model.strip(),
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 1024,
        },
    }
    if system:
        payload["system"] = system
    if images:
        payload["images"] = images

    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json=payload,
        timeout=OLLAMA_TIMEOUT,
    )
    response.raise_for_status()

    result = response.json()

    # Warn if Ollama returned a different model than requested
    returned_model = result.get("model", "")
    if returned_model and returned_model != model.strip():
        print(f"  ⚠ Warning: requested '{model}' but Ollama used '{returned_model}'")

    return result.get("response", "")


# ── JSON extraction helper ─────────────────────────────────────────────────

def _extract_json(raw: str) -> dict:
    """
    Strips markdown fences and parses JSON.
    Falls back gracefully if the model returns garbage.
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    start = cleaned.find("{")
    end   = cleaned.rfind("}") + 1
    if start != -1 and end > start:
        cleaned = cleaned[start:end]

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {}


# ── Public summarization calls ─────────────────────────────────────────────

def summarize_text_file(content: str, user_prompt: str) -> dict:
    """
    Ask the local LLM to summarize a text file.
    Returns a dict matching FileSummary's LLM fields.
    """
    model = get_text_model()
    prompt = f"User task: {user_prompt}\n\nFile content:\n{content}"
    raw = _call_ollama(
        model=model,
        prompt=prompt,
        system=SYSTEM_PROMPT,
    )
    return _extract_json(raw)


def summarize_image_file(image_b64: str, user_prompt: str) -> dict:
    """
    Ask the local vision model to describe a JPEG/PNG.
    Returns a dict matching FileSummary's LLM fields.
    """
    model = get_vision_model()
    vision_system = (
        "You are an image analyst. Describe what you see in the image relevant to the user's task. "
        "Then respond ONLY with valid JSON:\n"
        '{"data_summary": "string", "key_points": ["string",...], '
        '"entities": "string", "word_count": 0}'
    )
    prompt = (
        f"User task: {user_prompt}\n\n"
        "Analyse this image and extract all relevant information you can see."
    )
    raw = _call_ollama(
        model=model,
        prompt=prompt,
        system=vision_system,
        images=[image_b64],
    )
    return _extract_json(raw)


def build_global_summary(file_summaries: list[dict], user_prompt: str, n: int) -> dict:
    """
    Combine per-file summaries into a single global synthesis.
    Returns a dict matching GlobalSummary fields.
    """
    model = get_text_model()
    summaries_text = json.dumps(file_summaries, indent=2)
    prompt = GLOBAL_SUMMARY_PROMPT.format(n=n, summaries=summaries_text)
    prompt = f"User task: {user_prompt}\n\n{prompt}"
    raw = _call_ollama(
        model=model,
        prompt=prompt,
        system="You are a senior analyst. Respond only with valid JSON.",
    )
    return _extract_json(raw)