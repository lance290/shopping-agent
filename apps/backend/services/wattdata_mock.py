"""
DEPRECATED — this file is a backward-compatible shim.
All vendor data now lives in services/vendors.py.
"""
# Re-export everything from the new module so stale imports still work
from services.vendors import *  # noqa: F401,F403
from services.vendors import (  # explicit re-exports for type checkers
    Vendor,
    ChecklistItem,
    VENDORS,
    VENDORS as MOCK_VENDORS,  # backward compat alias
    CHARTER_CHECKLIST,
    CHARTER_EMAIL_TEMPLATE,
    CATEGORY_ALIASES,
    normalize_category,
    get_vendors,
    get_vendor_suggestions,
    is_service_category,
    get_vendors_as_results,
    search_vendors,
    search_checklist,
    get_checklist_summary,
    get_email_template,
    get_vendor_detail,
)
