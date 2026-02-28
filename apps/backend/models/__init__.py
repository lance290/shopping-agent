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
    ProjectMember,
    ProjectInvite,
    Row,
    RequestSpec,
)

# Bid models
from models.bids import (
    Vendor,
    Seller,  # backward-compatible alias for Vendor
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
    VendorProfile,  # alias for Vendor
    Merchant,       # alias for Vendor
    SellerQuote,
    OutreachEvent,
    DealHandoff,
    Contract,
    SellerBookmark,
)

# Outreach models
from models.outreach import (
    OutreachCampaign,
    OutreachMessage,
    OutreachQuote,
)

# Deal pipeline models
from models.deals import (
    Deal,
    DealMessage,
)

# Pop V2 models
from models.pop import (
    WalletTransaction,
    Receipt,
    Referral,
    _gen_ref_code,
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
    "ProjectMember",
    "ProjectInvite",
    "Row",
    "RequestSpec",
    # Bids
    "Vendor",
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
    # Outreach
    "OutreachCampaign",
    "OutreachMessage",
    "OutreachQuote",
    # Deal pipeline
    "Deal",
    "DealMessage",
    # Pop V2
    "WalletTransaction",
    "Receipt",
    "Referral",
    "_gen_ref_code",
    # Admin
    "BugReport",
    "Notification",
    "UserSignal",
    "UserPreference",
]
