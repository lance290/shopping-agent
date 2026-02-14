"""
Safe JSON parsing and serialization utilities for the backend.

These utilities provide consistent error handling and logging for JSON operations
throughout the application, reducing code duplication and improving reliability.
"""

import json
import logging
from typing import Any, Optional, TypeVar, Callable

logger = logging.getLogger(__name__)

T = TypeVar('T')


def safe_json_loads(
    s: Optional[str],
    default: Optional[T] = None,
    *,
    logger_name: str = "json",
) -> Any:
    """
    Safely load JSON from a string with a fallback value.

    Args:
        s: JSON string to parse
        default: Default value if parsing fails (default: None)
        logger_name: Logger name for error messages (default: "json")

    Returns:
        Parsed JSON or default value

    Examples:
        >>> safe_json_loads('{"key": "value"}', {})
        {'key': 'value'}
        >>> safe_json_loads(None, [])
        []
        >>> safe_json_loads('invalid', {})
        {}
    """
    if not s or not isinstance(s, str) or not s.strip():
        return default

    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        logger.warning(f"[{logger_name}] Failed to parse JSON: {e}")
        return default
    except Exception as e:
        logger.error(f"[{logger_name}] Unexpected error parsing JSON: {e}")
        return default


def safe_json_dumps(
    obj: Any,
    default: str = "{}",
    *,
    logger_name: str = "json",
    **kwargs: Any,
) -> str:
    """
    Safely serialize an object to JSON string.

    Args:
        obj: Object to serialize
        default: Default string if serialization fails (default: "{}")
        logger_name: Logger name for error messages (default: "json")
        **kwargs: Additional arguments passed to json.dumps

    Returns:
        JSON string or default value

    Examples:
        >>> safe_json_dumps({"key": "value"})
        '{"key": "value"}'
        >>> safe_json_dumps(set([1, 2]), "[]")
        '[]'
    """
    try:
        return json.dumps(obj, **kwargs)
    except (TypeError, ValueError) as e:
        logger.warning(f"[{logger_name}] Failed to serialize to JSON: {e}")
        return default
    except Exception as e:
        logger.error(f"[{logger_name}] Unexpected error serializing to JSON: {e}")
        return default


def safe_json_loads_with_validator(
    s: Optional[str],
    validator: Callable[[Any], bool],
    default: T,
    *,
    logger_name: str = "json",
) -> Any:
    """
    Safely load JSON with validation.

    Args:
        s: JSON string to parse
        validator: Function to validate the parsed result
        default: Default value if parsing or validation fails
        logger_name: Logger name for error messages (default: "json")

    Returns:
        Validated parsed JSON or default value

    Examples:
        >>> def is_dict_with_id(obj):
        ...     return isinstance(obj, dict) and 'id' in obj
        >>> safe_json_loads_with_validator('{"id": 1}', is_dict_with_id, {})
        {'id': 1}
        >>> safe_json_loads_with_validator('{"no_id": 1}', is_dict_with_id, {})
        {}
    """
    if not s or not isinstance(s, str) or not s.strip():
        return default

    try:
        parsed = json.loads(s)
        if validator(parsed):
            return parsed
        logger.warning(f"[{logger_name}] Parsed JSON failed validation")
        return default
    except json.JSONDecodeError as e:
        logger.warning(f"[{logger_name}] Failed to parse JSON: {e}")
        return default
    except Exception as e:
        logger.error(f"[{logger_name}] Unexpected error: {e}")
        return default


# Common validators

def is_dict(obj: Any) -> bool:
    """Validate that object is a dictionary."""
    return isinstance(obj, dict)


def is_list(obj: Any) -> bool:
    """Validate that object is a list."""
    return isinstance(obj, list)


def is_dict_or_empty(obj: Any) -> bool:
    """Validate that object is a dictionary or None."""
    return obj is None or isinstance(obj, dict)


def is_list_or_empty(obj: Any) -> bool:
    """Validate that object is a list or None."""
    return obj is None or isinstance(obj, list)


# Domain-specific parsers

def parse_choice_factors(s: Optional[str]) -> list:
    """
    Parse choice factors JSON with validation.

    Args:
        s: JSON string containing choice factors

    Returns:
        List of choice factor dictionaries or empty list
    """
    def validator(obj: Any) -> bool:
        if not isinstance(obj, list):
            return False
        return all(
            isinstance(item, dict) and
            'name' in item and
            'type' in item and
            isinstance(item['name'], str) and
            isinstance(item['type'], str)
            for item in obj
        )

    return safe_json_loads_with_validator(s, validator, [], logger_name="choice_factors")


def parse_choice_answers(s: Optional[str]) -> dict:
    """
    Parse choice answers JSON with validation.

    Args:
        s: JSON string containing choice answers

    Returns:
        Dictionary of choice answers or empty dict
    """
    return safe_json_loads_with_validator(s, is_dict, {}, logger_name="choice_answers")


def parse_chat_history(s: Optional[str]) -> list:
    """
    Parse chat history JSON with validation.

    Args:
        s: JSON string containing chat messages

    Returns:
        List of chat message dictionaries or empty list
    """
    def validator(obj: Any) -> bool:
        if not isinstance(obj, list):
            return False
        return all(
            isinstance(msg, dict) and
            'role' in msg and
            'content' in msg and
            isinstance(msg['role'], str) and
            isinstance(msg['content'], str)
            for msg in obj
        )

    return safe_json_loads_with_validator(s, validator, [], logger_name="chat_history")
