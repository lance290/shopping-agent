# Services package
from .wattdata_mock import get_vendors, get_vendor_suggestions, Vendor
from .email import (
    send_outreach_email,
    send_handoff_buyer_email,
    send_handoff_seller_email,
    EmailResult,
)

__all__ = [
    "get_vendors", 
    "get_vendor_suggestions", 
    "Vendor",
    "send_outreach_email",
    "send_handoff_buyer_email",
    "send_handoff_seller_email",
    "EmailResult",
]
