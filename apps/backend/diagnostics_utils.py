import json
from typing import Any, Dict, Optional

REDACT_KEYS = {
    'authorization', 'token', 'cookie', 'password', 'secret', 'api_key', 'apikey',
    'access_token', 'refresh_token', 'session_id'
}

MAX_STRING_LENGTH = 1000
MAX_DEPTH = 5

def _redact_value(key: str, value: Any) -> Any:
    if isinstance(value, str):
        if any(k in key.lower() for k in REDACT_KEYS):
            return '[REDACTED]'
        if len(value) > MAX_STRING_LENGTH:
            return value[:MAX_STRING_LENGTH] + '...[TRUNCATED]'
    return value

def _process_object(obj: Any, depth: int = 0) -> Any:
    if depth > MAX_DEPTH:
        return '[MAX_DEPTH_REACHED]'
    
    if isinstance(obj, dict):
        return {
            k: _process_object(_redact_value(k, v), depth + 1)
            for k, v in obj.items()
        }
    elif isinstance(obj, list):
        return [_process_object(item, depth + 1) for item in obj]
    else:
        return obj

def _parse_diagnostics(raw: Any) -> Any:
    """Parse diagnostics that may be a dict (from JSONB) or a JSON string."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        return json.loads(raw)
    return raw

def validate_and_redact_diagnostics(diagnostics_json) -> Optional[str]:
    """
    Validates that the input is valid JSON, redacts sensitive keys,
    truncates long strings, and returns the sanitized JSON string.
    Returns None if input is invalid or None.
    """
    if not diagnostics_json:
        return None
    
    try:
        # 1. Parse (handles both dict and string)
        data = _parse_diagnostics(diagnostics_json)
        
        # 2. Redact and Truncate
        sanitized = _process_object(data)
        
        # 3. Re-serialize
        return json.dumps(sanitized)
    except Exception as e:
        print(f"[DIAGNOSTICS] Failed to process diagnostics: {e}")
        return None

def generate_diagnostics_summary(diagnostics_json) -> str:
    """
    Generates a markdown summary of the diagnostics.
    Accepts both JSON strings and pre-parsed dicts (from JSONB columns).
    """
    if not diagnostics_json:
        return "No diagnostics available."

    try:
        data = _parse_diagnostics(diagnostics_json)
        if not isinstance(data, dict):
            return "No diagnostics available."
        summary = []
        
        # User Agent & URL
        summary.append(f"- **URL**: {data.get('url', 'unknown')}")
        summary.append(f"- **User Agent**: {data.get('userAgent', 'unknown')}")
        
        # Top Console Errors
        logs = data.get('logs', [])
        errors = [l for l in logs if l.get('level') == 'error']
        if errors:
            summary.append(f"\n**Top Console Errors ({len(errors)})**:")
            for err in errors[:3]: # Top 3
                msg = err.get('message', '')[:200]
                summary.append(f"- `{msg}`")
        
        # Failed Network Requests
        network = data.get('network', [])
        failures = [n for n in network if n.get('level') == 'error']
        if failures:
            summary.append(f"\n**Recent Network Failures ({len(failures)})**:")
            for fail in failures[:3]: # Top 3
                details = fail.get('details', {})
                url = details.get('url', 'unknown')
                status = details.get('status', 'unknown')
                summary.append(f"- `{status} {url}`")
                
        return "\n".join(summary)
    except Exception:
        return "Failed to generate diagnostics summary."
