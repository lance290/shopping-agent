"""
Core LLM call functions — Gemini direct, OpenRouter, JSON extraction.
Shared by llm.py, llm_pop.py, and other services.
"""

import json
import logging
import os
import re

import httpx

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")  # Direct Gemini REST API fallback
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-3-flash-preview")  # Primary LLM path


def _get_gemini_api_key() -> str:
    return os.getenv("GOOGLE_GENERATIVE_AI_API_KEY") or os.getenv("GEMINI_API_KEY") or ""


def _get_openrouter_api_key() -> str:
    return os.getenv("OPENROUTER_API_KEY") or ""


async def _call_gemini_direct(prompt: str, timeout: float = 30.0) -> str:
    """Call Gemini REST API directly."""
    api_key = _get_gemini_api_key()
    if not api_key:
        raise ValueError("No Gemini API key")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 4096,
        },
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            params={"key": api_key},
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()

    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError("Gemini returned no candidates")
    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        raise ValueError("Gemini returned no content parts")
    return parts[0].get("text", "")


async def _call_openrouter(prompt: str, timeout: float = 30.0) -> str:
    """Call OpenRouter API (OpenAI-compatible)."""
    api_key = _get_openrouter_api_key()
    if not api_key:
        raise ValueError("No OpenRouter API key (OPENROUTER_API_KEY)")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 4096,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

    choices = data.get("choices", [])
    if not choices:
        raise ValueError("OpenRouter returned no choices")
    return choices[0].get("message", {}).get("content", "")


async def call_gemini(prompt: str, timeout: float = 30.0) -> str:
    """Call LLM: try OpenRouter first (gemini-3-flash-preview), fall back to Gemini direct."""
    # Primary: OpenRouter (supports gemini-3-flash-preview)
    if _get_openrouter_api_key():
        try:
            return await _call_openrouter(prompt, timeout)
        except Exception as e:
            logger.warning(f"OpenRouter failed, trying Gemini direct: {e}")

    # Fallback: Gemini direct API
    if _get_gemini_api_key():
        try:
            return await _call_gemini_direct(prompt, timeout)
        except Exception as e:
            logger.error(f"Gemini direct also failed: {e}")
            raise

    raise ValueError("No LLM API key configured (OPENROUTER_API_KEY, GEMINI_API_KEY, or GOOGLE_GENERATIVE_AI_API_KEY)")


def _extract_json(text: str) -> dict:
    """Extract JSON object from LLM response, handling markdown fences and prose."""
    cleaned = re.sub(r"```(?:json)?\s*\n?", "", text)
    cleaned = re.sub(r"\n?```", "", cleaned)
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        cleaned = cleaned[first_brace : last_brace + 1]
    return json.loads(cleaned)


def _extract_json_array(text: str) -> list:
    """Extract JSON array from LLM response."""
    cleaned = re.sub(r"```(?:json)?\s*\n?", "", text)
    cleaned = re.sub(r"\n?```", "", cleaned)
    first_bracket = cleaned.find("[")
    last_bracket = cleaned.rfind("]")
    if first_bracket != -1 and last_bracket > first_bracket:
        cleaned = cleaned[first_bracket : last_bracket + 1]
    return json.loads(cleaned)
