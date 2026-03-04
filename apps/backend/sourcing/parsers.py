import re as _re
from typing import Optional, Tuple

def _parse_numeric(raw) -> Optional[float]:
    """Extract a float from a value that may contain $, commas, or freeform text."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).strip()
    nums = _re.findall(r"[\d]+(?:\.[\d]+)?", s.replace(",", ""))
    if nums:
        return float(nums[0])
    return None

def _parse_price_value(raw) -> Tuple[Optional[float], Optional[float]]:
    """Parse a string value that may encode a range, gt, or lt constraint."""
    if raw is None:
        return None, None
    if isinstance(raw, (int, float)):
        return None, None
    s = str(raw).strip()
    m = _re.match(r"^\$?([\d,.]+)\s*[-–]\s*\$?([\d,.]+)", s)
    if m:
        return float(m.group(1).replace(",", "")), float(m.group(2).replace(",", ""))
    m = _re.match(r"^[>≥]\s*\$?([\d,.]+)", s)
    if m:
        return float(m.group(1).replace(",", "")), None
    m = _re.match(r"^[<≤]\s*\$?([\d,.]+)", s)
    if m:
        return None, float(m.group(1).replace(",", ""))
    return None, None
