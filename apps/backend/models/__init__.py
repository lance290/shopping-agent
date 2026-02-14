"""
Backward-compatible model exports.

This module maintains the original flat import structure for backward compatibility
while models are organized into domain modules:
- auth.py: Authentication and user models
- rows.py: Row, Project, and RequestSpec models
- bids.py: Bid and Seller models
- social.py: Comments, likes, shares, and clickouts
- marketplace.py: Merchant, quotes, and contracts
- admin.py: Bug reports, notifications, and preferences
"""

# Auth models
from models.auth import (
    User,
    AuthLoginCode,
    AuthSession,
    AuditLog,
    hash_token,
    generate_verification_code,
    generate_session_token,
    generate_magic_link_token,
)

# Row models
from models.rows import (
    RowBase,
    RequestSpecBase,
    RowCreate,
    ProjectBase,
    ProjectCreate,
    Project,
    Row,
    RequestSpec,
)

# Bid models
from models.bids import (
    Seller,
    Bid,
    BidWithProvenance,
)

# Social models
from models.social import (
    Comment,
    ShareLink,
    ClickoutEvent,
    PurchaseEvent,
)

# Marketplace models
from models.marketplace import (
    VendorProfile,
    SellerQuote,
    OutreachEvent,
    DealHandoff,
    Merchant,
    Contract,
    SellerBookmark,
)

# Admin models
from models.admin import (
    BugReport,
    Notification,
    UserSignal,
    UserPreference,
)

__all__ = [
    # Auth
    "User",
    "AuthLoginCode",
    "AuthSession",
    "AuditLog",
    "hash_token",
    "generate_verification_code",
    "generate_session_token",
    "generate_magic_link_token",
    # Rows
    "RowBase",
    "RequestSpecBase",
    "RowCreate",
    "ProjectBase",
    "ProjectCreate",
    "Project",
    "Row",
    "RequestSpec",
    # Bids
    "Seller",
    "Bid",
    "BidWithProvenance",
    # Social
    "Comment",
    "ShareLink",
    "ClickoutEvent",
    "PurchaseEvent",
    # Marketplace
    "VendorProfile",
    "SellerQuote",
    "OutreachEvent",
    "DealHandoff",
    "Merchant",
    "Contract",
    "SellerBookmark",
    # Admin
    "BugReport",
    "Notification",
    "UserSignal",
    "UserPreference",
]
