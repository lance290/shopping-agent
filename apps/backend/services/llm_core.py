"""
Core LLM call functions — Gemini direct, OpenRouter, JSON extraction.
Shared by llm.py, llm_pop.py, and other services.
"""

import json
import logging
import os
import re
import time
import uuid
from typing import Optional, List, Any

import httpx

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")  # Direct Gemini REST API
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-3-flash-preview")  # Primary LLM path

# Circuit breaker: skip OpenRouter for N seconds after a 402/payment error
_openrouter_backoff_until: float = 0.0
_OPENROUTER_BACKOFF_SECS = 600  # 10 minutes


def _get_gemini_api_key() -> str:
    return os.getenv("GOOGLE_GENERATIVE_AI_API_KEY") or os.getenv("GEMINI_API_KEY") or ""


def _get_openrouter_api_key() -> str:
    return os.getenv("OPENROUTER_API_KEY") or ""


async def _call_gemini_direct(prompt: str, timeout: float = 30.0, image_urls: Optional[List[str]] = None) -> str:
    """Call Gemini REST API directly."""
    api_key = _get_gemini_api_key()
    if not api_key:
        raise ValueError("No Gemini API key")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

    parts = [{"text": prompt}]
    
    if image_urls:
        import base64
        import mimetypes
        
        async with httpx.AsyncClient() as dl_client:
            for img_url in image_urls:
                try:
                    resp = await dl_client.get(img_url, timeout=10.0)
                    resp.raise_for_status()
                    b64_data = base64.b64encode(resp.content).decode("utf-8")
                    mime_type = mimetypes.guess_type(img_url)[0] or "image/jpeg"
                    
                    parts.append({
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": b64_data
                        }
                    })
                except Exception as e:
                    logger.warning(f"[LLM] Failed to download image {img_url} for Gemini fallback: {e}")

    payload = {
        "contents": [{"parts": parts}],
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


async def _call_openrouter(prompt: str, timeout: float = 30.0, image_urls: Optional[List[str]] = None) -> str:
    """Call OpenRouter API (OpenAI-compatible)."""
    api_key = _get_openrouter_api_key()
    if not api_key:
        raise ValueError("No OpenRouter API key (OPENROUTER_API_KEY)")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    content: Any = prompt
    if image_urls:
        multimodal_content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for image_url in image_urls:
            if not image_url:
                continue
            multimodal_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                }
            )
        content = multimodal_content

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": content}],
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


async def call_gemini(prompt: str, timeout: float = 30.0, image_urls: Optional[List[str]] = None) -> str:
    """Call LLM: try OpenRouter first, fall back to Gemini direct. Circuit-breaker on 402."""
    global _openrouter_backoff_until
    t0 = time.monotonic()

    # Primary: OpenRouter (skip if circuit breaker is active)
    if _get_openrouter_api_key() and time.monotonic() >= _openrouter_backoff_until:
        try:
            result = await _call_openrouter(prompt, timeout, image_urls=image_urls)
            elapsed = time.monotonic() - t0
            logger.info(f"[LLM] OpenRouter responded in {elapsed:.1f}s")
            return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 402:
                _openrouter_backoff_until = time.monotonic() + _OPENROUTER_BACKOFF_SECS
                logger.error(f"[LLM] OpenRouter 402 — OUT OF CREDITS. Skipping for {_OPENROUTER_BACKOFF_SECS}s.")
            else:
                logger.warning(f"[LLM] OpenRouter HTTP {e.response.status_code}, falling back to Gemini direct")
        except Exception as e:
            logger.warning(f"[LLM] OpenRouter failed ({e}), falling back to Gemini direct")
    elif _get_openrouter_api_key():
        remaining = int(_openrouter_backoff_until - time.monotonic())
        logger.info(f"[LLM] OpenRouter circuit breaker active ({remaining}s remaining), using Gemini direct")

    # Fallback: Gemini direct API
    if _get_gemini_api_key():
        try:
            result = await _call_gemini_direct(prompt, timeout, image_urls=image_urls)
            elapsed = time.monotonic() - t0
            logger.info(f"[LLM] Gemini direct responded in {elapsed:.1f}s")
            return result
        except Exception as e:
            logger.error(f"[LLM] Gemini direct also failed: {e}")
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


# ---------------------------------------------------------------------------
# Gemini function-calling (tool-calling) support
# ---------------------------------------------------------------------------

def _messages_to_gemini_contents(messages: List[dict]) -> List[dict]:
    """Convert OpenAI-style messages to Gemini REST API contents format."""
    contents: List[dict] = []
    for msg in messages:
        role = msg.get("role", "user")
        if role == "system":
            contents.append({
                "role": "user",
                "parts": [{"text": msg["content"]}],
            })
            contents.append({
                "role": "model",
                "parts": [{"text": "Understood."}],
            })
        elif role == "user":
            contents.append({
                "role": "user",
                "parts": [{"text": msg["content"]}],
            })
        elif role in ("assistant", "model"):
            parts = msg.get("parts")
            if parts:
                contents.append({"role": "model", "parts": parts})
            else:
                contents.append({
                    "role": "model",
                    "parts": [{"text": msg.get("content", "")}],
                })
        elif role == "tool":
            contents.append({
                "role": "user",
                "parts": [{
                    "functionResponse": {
                        "name": msg["tool_name"],
                        "response": {"result": msg["content"]},
                    },
                }],
            })
    return contents


def _parse_gemini_tool_response(data: dict) -> "GeminiToolResponse":
    """Parse Gemini REST API response into structured tool calls."""
    from sourcing.tools import GeminiToolResponse, ToolCall

    candidates = data.get("candidates", [])
    if not candidates:
        return GeminiToolResponse(text=None, tool_calls=[])

    parts = candidates[0].get("content", {}).get("parts", [])
    text_parts: List[str] = []
    tool_calls: List[ToolCall] = []

    for part in parts:
        if "text" in part:
            text_parts.append(part["text"])
        elif "functionCall" in part:
            fc = part["functionCall"]
            tool_calls.append(ToolCall(
                id=str(uuid.uuid4()),
                name=fc.get("name", ""),
                params=fc.get("args", {}),
            ))

    return GeminiToolResponse(
        text="\n".join(text_parts) if text_parts else None,
        tool_calls=tool_calls,
        raw_parts=parts,
    )


async def call_gemini_with_tools(
    messages: List[dict],
    tools: List[dict],
    timeout: float = 15.0,
) -> "GeminiToolResponse":
    """Call Gemini REST API with function-calling enabled.

    Uses the same httpx + API-key pattern as ``call_gemini()``.
    Falls back to Gemini direct only (no OpenRouter) because OpenRouter
    doesn't reliably proxy Gemini function-calling.
    """
    from sourcing.tools import GeminiToolResponse

    api_key = _get_gemini_api_key()
    if not api_key:
        raise ValueError("No Gemini API key for tool-calling")

    model = GEMINI_MODEL
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"models/{model}:generateContent"
    )

    function_declarations = [
        {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["parameters"],
        }
        for t in tools
    ]

    contents = _messages_to_gemini_contents(messages)

    payload: dict[str, Any] = {
        "contents": contents,
        "tools": [{"functionDeclarations": function_declarations}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 4096,
        },
    }

    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                params={"key": api_key},
                json=payload,
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()

        elapsed = time.monotonic() - t0
        logger.info("[LLM] Gemini tool-calling responded in %.1fs", elapsed)
        return _parse_gemini_tool_response(data)

    except Exception as e:
        elapsed = time.monotonic() - t0
        logger.error("[LLM] Gemini tool-calling failed after %.1fs: %s", elapsed, e)
        return GeminiToolResponse(text=None, tool_calls=[])
