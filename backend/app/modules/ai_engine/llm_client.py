"""LLM provider client for optional external API or local Ollama phrasing."""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import settings


def is_llm_configured() -> bool:
    """Return True when an external LLM API or local Ollama provider is configured."""
    provider = (settings.llm_provider or "").strip().lower()
    if provider == "ollama":
        return True
    if provider in ("openai", "openai_compatible") and bool(settings.llm_api_key):
        return True
    return False


def call_llm_chat(system_prompt: str, user_prompt: str, *, timeout_seconds: float = 10.0) -> str | None:
    """Send a chat completion request to the configured LLM provider, returning None if unavailable."""
    provider = (settings.llm_provider or "").strip().lower()
    if not provider:
        return None

    try:
        if provider == "ollama":
            base = (settings.llm_base_url or "http://localhost:11434").rstrip("/")
            model = settings.llm_model or "llama3.1"
            with httpx.Client(timeout=timeout_seconds) as client:
                resp = client.post(
                    f"{base}/api/chat",
                    json={
                        "model": model,
                        "stream": False,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return str(data.get("message", {}).get("content", "")).strip() or None

        if provider in ("openai", "openai_compatible") and settings.llm_api_key:
            base = (settings.llm_base_url or "https://api.openai.com/v1").rstrip("/")
            model = settings.llm_model or "gpt-4o-mini"
            with httpx.Client(timeout=timeout_seconds) as client:
                resp = client.post(
                    f"{base}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                    json={
                        "model": model,
                        "temperature": 0.2,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                choices = data.get("choices") or []
                if choices:
                    return str(choices[0].get("message", {}).get("content", "")).strip() or None
    except Exception:
        return None

    return None


def parse_llm_json_object(raw_text: str | None) -> dict[str, Any] | None:
    """Extract a JSON object from an LLM response string if valid."""
    if not raw_text:
        return None
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            parsed = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return None

    return parsed if isinstance(parsed, dict) else None
