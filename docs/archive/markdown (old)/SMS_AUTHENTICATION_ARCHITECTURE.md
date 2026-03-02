# SMS-Based Authentication System Architecture

## Executive Summary

This document outlines the architectural design for replacing the current email-based authentication system with SMS-based authentication in the Shopping Agent application. The design maintains security best practices, includes comprehensive fraud prevention, and provides a clear migration path.

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Architecture Overview](#2-architecture-overview)
3. [System Components](#3-system-components)
4. [Database Schema Changes](#4-database-schema-changes)
5. [API Design](#5-api-design)
6. [SMS Provider Evaluation](#6-sms-provider-evaluation)
7. [Security Considerations](#7-security-considerations)
8. [Implementation Plan](#8-implementation-plan)
9. [Cost Analysis](#9-cost-analysis)
10. [Rollback Strategy](#10-rollback-strategy)

---

## 1. Current State Analysis

### 1.1 Existing Email Authentication Flow

```
┌─────────────┐
│   User      │
│  (Browser)  │
└──────┬──────┘
       │
       │ POST /api/auth/start
       │ { email: "user@example.com" }
       ▼
┌─────────────────────────┐
│  Frontend (Next.js)     │
│  /app/api/auth/start    │
└──────┬──────────────────┘
       │
       │ Proxy to BFF
       ▼
┌─────────────────────────┐
│  Backend (FastAPI)      │
│  POST /auth/start       │
└──────┬──────────────────┘
       │
       ├─► Generate 6-digit code
       ├─► Hash and store in AuthLoginCode
       ├─► Send via Resend API
       └─► Return { status: "sent" }

       (User receives email, enters code)

       │ POST /api/auth/verify
       │ { email: "user@example.com", code: "123456" }
       ▼
┌─────────────────────────┐
│  Backend (FastAPI)      │
│  POST /auth/verify      │
└──────┬──────────────────┘
       │
       ├─► Validate code hash
       ├─► Check rate limits (5 attempts)
       ├─► Create/find User
       ├─► Generate session token
       ├─► Store in AuthSession
       └─► Return { session_token: "..." }
```

### 1.2 Current Security Features

- **Rate Limiting**: 5 attempts per email, 60-second window
- **Lockout Mechanism**: 45-minute lockout after 5 failed attempts
- **Code Hashing**: SHA-256 hashing of verification codes
- **Session Management**: Cryptographically secure tokens (32-byte urlsafe)
- **Token Expiry**: Codes invalidated on use or new request
- **Audit Logging**: All auth events logged

### 1.3 Current Database Schema (Relevant Tables)

```sql
-- User table
user (
  id: int (PK),
  email: str (unique, indexed),
  created_at: datetime,
  is_admin: bool
)

-- AuthLoginCode table
auth_login_code (
  id: int (PK),
  email: str (indexed),
  code_hash: str,
  is_active: bool,
  attempt_count: int,
  locked_until: datetime,
  created_at: datetime
)

-- AuthSession table
auth_session (
  id: int (PK),
  email: str (indexed),
  user_id: int (FK -> user.id),
  session_token_hash: str (indexed),
  created_at: datetime,
  revoked_at: datetime
)
```

---

## 2. Architecture Overview

### 2.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND TIER                           │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  Next.js Login Page                                  │      │
│  │  - Phone number input with international format      │      │
│  │  - Country code selector (react-phone-number-input)  │      │
│  │  - SMS code verification input                       │      │
│  │  - Resend code functionality                         │      │
│  └────────────────────┬─────────────────────────────────┘      │
│                       │                                         │
└───────────────────────┼─────────────────────────────────────────┘
                        │
                        │ HTTPS (POST /api/auth/start-sms)
                        │       (POST /api/auth/verify-sms)
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BFF (Next.js API Routes)                   │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  - Request validation                                │      │
│  │  - Phone number format validation                    │      │
│  │  - Proxy to backend                                  │      │
│  │  - Cookie management                                 │      │
│  └────────────────────┬─────────────────────────────────┘      │
│                       │                                         │
└───────────────────────┼─────────────────────────────────────────┘
                        │
                        │ HTTP (Internal network)
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND TIER (FastAPI)                      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  Auth Endpoints                                      │      │
│  │  - POST /auth/start-sms                              │      │
│  │  - POST /auth/verify-sms                             │      │
│  │                                                       │      │
│  │  Security Layer                                      │      │
│  │  - Rate limiting (per phone number, per IP)          │      │
│  │  - Fraud detection (velocity checks, pattern match)  │      │
│  │  - Phone number validation & normalization           │      │
│  │  - Code generation & hashing                         │      │
│  │  - Lockout management                                │      │
│  └────────────┬─────────────────────┬─────────────────┬─┘      │
│               │                     │                 │         │
│               ▼                     ▼                 ▼         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐   │
│  │  SMS Service    │  │  Database       │  │  Audit Log   │   │
│  │  Abstraction    │  │  (PostgreSQL)   │  │  Service     │   │
│  └────────┬────────┘  └─────────────────┘  └──────────────┘   │
└───────────┼─────────────────────────────────────────────────────┘
            │
            │ SMS Provider API
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SMS PROVIDER TIER                          │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  Primary: Twilio                                     │      │
│  │  - Programmable SMS API                              │      │
│  │  - Global coverage                                   │      │
│  │  - Delivery receipts                                 │      │
│  │  - Phone number validation API                       │      │
│  └──────────────────────────────────────────────────────┘      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  Fallback: AWS SNS                                   │      │
│  │  - Used if Twilio fails                              │      │
│  │  - Lower cost, slightly lower deliverability         │      │
│  └──────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow - SMS Authentication

```
User Initiates Login
       │
       ▼
┌──────────────────────────────────────────────────────┐
│ 1. Phone Number Entry                                │
│    - User enters phone: +1 (555) 123-4567           │
│    - Frontend normalizes to E.164: +15551234567     │
│    - Validates format using libphonenumber          │
└────────────┬─────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────┐
│ 2. Request Verification Code                         │
│    POST /api/auth/start-sms                          │
│    {                                                 │
│      phone_number: "+15551234567",                  │
│      country_code: "US"                             │
│    }                                                 │
└────────────┬─────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────┐
│ 3. Backend Validation & Rate Limiting                │
│    - Validate E.164 format                           │
│    - Check rate limits:                              │
│      * 5 requests/phone/hour                        │
│      * 20 requests/IP/hour                          │
│    - Check fraud patterns:                           │
│      * Velocity (new phones per IP)                 │
│      * Known bad actors list                        │
│    - Check existing lockout status                   │
└────────────┬─────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────┐
│ 4. Code Generation & Storage                         │
│    - Generate 6-digit code: "847293"                 │
│    - Hash code: SHA-256(code)                        │
│    - Store in auth_sms_code table:                   │
│      * phone_number_hash (for privacy)              │
│      * code_hash                                     │
│      * expires_at (now + 10 minutes)                │
│      * attempt_count: 0                              │
│    - Invalidate previous active codes                │
└────────────┬─────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────┐
│ 5. Send SMS via Provider                             │
│    Primary: Twilio API                               │
│    - POST to Twilio Messaging API                    │
│    - Message: "Your verification code is: 847293"    │
│    - Store message_sid for tracking                  │
│                                                       │
│    Fallback: If Twilio fails                         │
│    - Retry with AWS SNS                              │
│    - Log provider switch event                       │
└────────────┬─────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────┐
│ 6. User Receives SMS & Enters Code                   │
│    - SMS delivered to phone                          │
│    - User enters: "847293"                           │
└────────────┬─────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────┐
│ 7. Code Verification                                 │
│    POST /api/auth/verify-sms                         │
│    {                                                 │
│      phone_number: "+15551234567",                  │
│      code: "847293"                                 │
│    }                                                 │
└────────────┬─────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────┐
│ 8. Backend Validation                                │
│    - Find active code for phone_number_hash          │
│    - Check if expired (> 10 minutes old)             │
│    - Check if locked (attempt_count >= 5)            │
│    - Verify code_hash matches                        │
│    - Increment attempt_count on failure              │
│    - Lock if attempt_count >= 5                      │
└────────────┬─────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────┐
│ 9. Session Creation (on success)                     │
│    - Find or create User by phone_number             │
│    - Generate session token (32-byte)                │
│    - Store in auth_session:                          │
│      * user_id                                       │
│      * session_token_hash                            │
│      * phone_number                                  │
│    - Invalidate SMS code (is_active = false)         │
│    - Return session_token to frontend                │
└────────────┬─────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────┐
│ 10. Frontend Cookie Storage                          │
│     - Store session_token in httpOnly cookie         │
│     - Redirect to dashboard                          │
└──────────────────────────────────────────────────────┘
```

---

## 3. System Components

### 3.1 Frontend Components

#### 3.1.1 Phone Number Input Component

**File**: `/apps/frontend/app/login/page.tsx`

**Features**:
- International phone number input with country selector
- Real-time format validation using `libphonenumber-js`
- Auto-formatting as user types
- Country code detection from browser locale
- Support for 190+ countries

**Dependencies**:
```json
{
  "react-phone-number-input": "^3.3.9",
  "libphonenumber-js": "^1.10.51"
}
```

**UI Flow**:
```
┌─────────────────────────────────────┐
│  Sign In                            │
├─────────────────────────────────────┤
│                                     │
│  Phone Number                       │
│  ┌────────────────────────────┐    │
│  │ +1  (555) 123-4567         │    │
│  └────────────────────────────┘    │
│                                     │
│  [Send verification code]           │
│                                     │
└─────────────────────────────────────┘

After code sent:

┌─────────────────────────────────────┐
│  Sign In                            │
├─────────────────────────────────────┤
│                                     │
│  We sent a code to                  │
│  +1 (555) 123-4567                 │
│                                     │
│  Verification Code                  │
│  ┌────────────────────────────┐    │
│  │   8 4 7 2 9 3              │    │
│  └────────────────────────────┘    │
│                                     │
│  [Verify]                           │
│                                     │
│  Didn't receive it?                 │
│  [Resend code]                      │
│                                     │
│  [Use a different number]           │
│                                     │
└─────────────────────────────────────┘
```

#### 3.1.2 Code Verification Component

- 6-digit input with auto-focus on each digit
- Auto-submit when all 6 digits entered
- Resend functionality with cooldown (60 seconds)
- Error display for invalid codes
- Lockout notification

### 3.2 Backend Components

#### 3.2.1 SMS Service Abstraction Layer

**File**: `/apps/backend/sms_service.py`

```python
# Abstract interface for SMS providers
class SMSProvider(Protocol):
    async def send_sms(
        self,
        phone_number: str,
        message: str
    ) -> SMSResult

    async def validate_phone(
        self,
        phone_number: str
    ) -> PhoneValidationResult

# Concrete implementations
class TwilioProvider(SMSProvider)
class AWSSNSProvider(SMSProvider)

# Service with fallback
class SMSService:
    def __init__(
        self,
        primary: SMSProvider,
        fallback: Optional[SMSProvider]
    )

    async def send_verification_code(
        self,
        phone_number: str,
        code: str
    ) -> bool
```

#### 3.2.2 Phone Number Validation Service

**File**: `/apps/backend/phone_validation.py`

```python
from phonenumbers import (
    parse,
    is_valid_number,
    format_number,
    PhoneNumberFormat
)

class PhoneValidator:
    @staticmethod
    def normalize_phone(phone: str, region: str = None) -> str:
        """Convert to E.164 format: +15551234567"""

    @staticmethod
    def validate_phone(phone: str) -> ValidationResult:
        """Check if valid, get type (mobile/fixed), region"""

    @staticmethod
    def hash_phone(phone: str) -> str:
        """SHA-256 hash for privacy in database"""
```

#### 3.2.3 Fraud Detection Service

**File**: `/apps/backend/fraud_detection.py`

```python
class FraudDetector:
    async def check_phone_velocity(
        self,
        ip_address: str
    ) -> VelocityCheckResult:
        """Check how many different phones used from this IP"""

    async def check_phone_reputation(
        self,
        phone_number: str
    ) -> ReputationResult:
        """Check against known fraud database"""

    async def check_unusual_patterns(
        self,
        phone_number: str,
        user_agent: str
    ) -> PatternResult:
        """Detect bots, automated systems"""
```

---

## 4. Database Schema Changes

### 4.1 New Tables

#### 4.1.1 `auth_sms_code` Table

```sql
CREATE TABLE auth_sms_code (
    id SERIAL PRIMARY KEY,

    -- Phone number (hashed for privacy)
    phone_number_hash VARCHAR(64) NOT NULL,

    -- Verification code (hashed)
    code_hash VARCHAR(64) NOT NULL,

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    attempt_count INTEGER DEFAULT 0,
    locked_until TIMESTAMP NULL,
    expires_at TIMESTAMP NOT NULL,

    -- SMS provider tracking
    provider VARCHAR(50) DEFAULT 'twilio',
    message_sid VARCHAR(255) NULL,  -- Twilio message ID
    delivery_status VARCHAR(50) NULL,  -- delivered, failed, pending

    -- Audit fields
    created_at TIMESTAMP DEFAULT NOW(),
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,

    -- Indexes
    INDEX idx_phone_hash (phone_number_hash),
    INDEX idx_active (is_active),
    INDEX idx_created (created_at)
);
```

#### 4.1.2 `fraud_detection_log` Table

```sql
CREATE TABLE fraud_detection_log (
    id SERIAL PRIMARY KEY,

    -- What was checked
    check_type VARCHAR(50) NOT NULL,  -- velocity, reputation, pattern
    phone_number_hash VARCHAR(64) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,

    -- Result
    is_suspicious BOOLEAN DEFAULT FALSE,
    risk_score INTEGER DEFAULT 0,  -- 0-100
    reason TEXT NULL,

    -- Action taken
    action VARCHAR(50) NULL,  -- allowed, blocked, flagged

    -- Timestamp
    created_at TIMESTAMP DEFAULT NOW(),

    -- Indexes
    INDEX idx_phone_hash (phone_number_hash),
    INDEX idx_ip (ip_address),
    INDEX idx_created (created_at),
    INDEX idx_suspicious (is_suspicious)
);
```

### 4.2 Modified Tables

#### 4.2.1 `user` Table - Add Phone Number

```sql
ALTER TABLE user ADD COLUMN phone_number VARCHAR(20) UNIQUE NULL;
ALTER TABLE user ADD COLUMN phone_number_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE user ADD COLUMN phone_added_at TIMESTAMP NULL;

-- Create index
CREATE INDEX idx_user_phone ON user(phone_number);

-- Update constraint: email OR phone_number required
-- (handled in application logic initially)
```

#### 4.2.2 `auth_session` Table - Add Phone Number

```sql
ALTER TABLE auth_session ADD COLUMN phone_number VARCHAR(20) NULL;

-- Create index
CREATE INDEX idx_session_phone ON auth_session(phone_number);
```

### 4.3 Migration Strategy

#### Migration File: `add_sms_authentication.py`

```python
"""Add SMS authentication support

Revision ID: abc123def456
Revises: bfa9d8fedf7a
Create Date: 2024-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Create auth_sms_code table
    op.create_table(
        'auth_sms_code',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('phone_number_hash', sa.String(64), nullable=False),
        sa.Column('code_hash', sa.String(64), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('attempt_count', sa.Integer(), default=0),
        sa.Column('locked_until', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('provider', sa.String(50), default='twilio'),
        sa.Column('message_sid', sa.String(255), nullable=True),
        sa.Column('delivery_status', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('idx_phone_hash', 'auth_sms_code', ['phone_number_hash'])
    op.create_index('idx_active', 'auth_sms_code', ['is_active'])
    op.create_index('idx_created', 'auth_sms_code', ['created_at'])

    # Create fraud_detection_log table
    op.create_table(
        'fraud_detection_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('check_type', sa.String(50), nullable=False),
        sa.Column('phone_number_hash', sa.String(64), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('is_suspicious', sa.Boolean(), default=False),
        sa.Column('risk_score', sa.Integer(), default=0),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('action', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('idx_fraud_phone_hash', 'fraud_detection_log', ['phone_number_hash'])
    op.create_index('idx_fraud_ip', 'fraud_detection_log', ['ip_address'])
    op.create_index('idx_fraud_created', 'fraud_detection_log', ['created_at'])
    op.create_index('idx_fraud_suspicious', 'fraud_detection_log', ['is_suspicious'])

    # Modify user table
    op.add_column('user', sa.Column('phone_number', sa.String(20), nullable=True))
    op.add_column('user', sa.Column('phone_number_verified', sa.Boolean(), default=False))
    op.add_column('user', sa.Column('phone_added_at', sa.DateTime(), nullable=True))
    op.create_index('idx_user_phone', 'user', ['phone_number'])
    op.create_unique_constraint('uq_user_phone', 'user', ['phone_number'])

    # Modify auth_session table
    op.add_column('auth_session', sa.Column('phone_number', sa.String(20), nullable=True))
    op.create_index('idx_session_phone', 'auth_session', ['phone_number'])

def downgrade():
    # Drop indexes and columns in reverse order
    op.drop_index('idx_session_phone', 'auth_session')
    op.drop_column('auth_session', 'phone_number')

    op.drop_constraint('uq_user_phone', 'user')
    op.drop_index('idx_user_phone', 'user')
    op.drop_column('user', 'phone_added_at')
    op.drop_column('user', 'phone_number_verified')
    op.drop_column('user', 'phone_number')

    op.drop_table('fraud_detection_log')
    op.drop_table('auth_sms_code')
```

---

## 5. API Design

### 5.1 New Endpoints

#### 5.1.1 POST `/auth/start-sms`

**Purpose**: Initiate SMS authentication by sending verification code

**Request**:
```json
{
  "phone_number": "+15551234567",
  "country_code": "US"  // Optional, for validation context
}
```

**Response (Success - 200)**:
```json
{
  "status": "sent",
  "expires_in": 600,  // seconds (10 minutes)
  "resend_available_in": 60  // seconds
}
```

**Response (Rate Limited - 429)**:
```json
{
  "status": "rate_limited",
  "locked_until": "2024-01-20T15:30:00Z",
  "reason": "Too many attempts"
}
```

**Response (Fraud Detected - 403)**:
```json
{
  "status": "blocked",
  "reason": "Suspicious activity detected"
}
```

**Backend Logic**:
```python
@app.post("/auth/start-sms")
async def auth_start_sms(
    request: AuthStartSMSRequest,
    req: Request,
    session: AsyncSession = Depends(get_session)
):
    # 1. Normalize phone number to E.164
    phone = PhoneValidator.normalize_phone(request.phone_number)

    # 2. Validate phone number format
    validation = PhoneValidator.validate_phone(phone)
    if not validation.is_valid:
        raise HTTPException(400, detail="Invalid phone number")

    # 3. Hash phone for storage
    phone_hash = PhoneValidator.hash_phone(phone)

    # 4. Rate limiting - phone level
    if not check_rate_limit(f"sms:{phone_hash}", "auth_sms_start"):
        raise HTTPException(429, detail="Too many requests")

    # 5. Rate limiting - IP level
    if not check_rate_limit(f"sms_ip:{req.client.host}", "auth_sms_ip"):
        raise HTTPException(429, detail="Too many requests from this IP")

    # 6. Fraud detection
    fraud_check = await fraud_detector.check_all(
        phone_number=phone,
        ip_address=req.client.host,
        user_agent=req.headers.get("user-agent")
    )
    if fraud_check.is_blocked:
        await log_fraud_detection(session, phone_hash, fraud_check)
        raise HTTPException(403, detail="Access denied")

    # 7. Check existing lockout
    existing = await get_active_sms_code(session, phone_hash)
    if existing and existing.locked_until > datetime.utcnow():
        raise HTTPException(429, detail={
            "locked_until": existing.locked_until.isoformat()
        })

    # 8. Invalidate old codes
    await invalidate_sms_codes(session, phone_hash)

    # 9. Generate new code
    code = generate_verification_code()  # 6-digit

    # 10. Store code
    sms_code = AuthSMSCode(
        phone_number_hash=phone_hash,
        code_hash=hash_token(code),
        expires_at=datetime.utcnow() + timedelta(minutes=10),
        ip_address=req.client.host,
        user_agent=req.headers.get("user-agent")
    )
    session.add(sms_code)
    await session.commit()

    # 11. Send SMS
    result = await sms_service.send_verification_code(phone, code)

    # 12. Update delivery tracking
    sms_code.message_sid = result.message_sid
    sms_code.provider = result.provider
    sms_code.delivery_status = result.status
    await session.commit()

    # 13. Audit log
    await audit_log(
        session=session,
        action="auth.sms_start",
        details={"phone_hash": phone_hash},
        request=req
    )

    return {
        "status": "sent",
        "expires_in": 600,
        "resend_available_in": 60
    }
```

#### 5.1.2 POST `/auth/verify-sms`

**Purpose**: Verify SMS code and create session

**Request**:
```json
{
  "phone_number": "+15551234567",
  "code": "847293"
}
```

**Response (Success - 200)**:
```json
{
  "status": "ok",
  "session_token": "Abc123...Xyz789"
}
```

**Response (Invalid Code - 400)**:
```json
{
  "status": "invalid",
  "attempts_remaining": 3
}
```

**Response (Locked - 429)**:
```json
{
  "status": "locked",
  "locked_until": "2024-01-20T16:00:00Z"
}
```

**Backend Logic**:
```python
@app.post("/auth/verify-sms")
async def auth_verify_sms(
    request: AuthVerifySMSRequest,
    session: AsyncSession = Depends(get_session)
):
    # 1. Normalize and hash phone
    phone = PhoneValidator.normalize_phone(request.phone_number)
    phone_hash = PhoneValidator.hash_phone(phone)

    # 2. Find active code
    sms_code = await get_active_sms_code(session, phone_hash)
    if not sms_code:
        raise HTTPException(400, detail="No active code found")

    # 3. Check expiry
    if sms_code.expires_at < datetime.utcnow():
        sms_code.is_active = False
        await session.commit()
        raise HTTPException(400, detail="Code expired")

    # 4. Check lockout
    if sms_code.locked_until and sms_code.locked_until > datetime.utcnow():
        raise HTTPException(429, detail={
            "locked_until": sms_code.locked_until.isoformat()
        })

    # 5. Verify code
    if hash_token(request.code) != sms_code.code_hash:
        sms_code.attempt_count += 1

        # Lock after 5 attempts
        if sms_code.attempt_count >= 5:
            sms_code.locked_until = datetime.utcnow() + timedelta(minutes=45)
            sms_code.is_active = False
            await session.commit()
            raise HTTPException(429, detail={
                "locked_until": sms_code.locked_until.isoformat()
            })

        await session.commit()
        remaining = 5 - sms_code.attempt_count
        raise HTTPException(400, detail={
            "status": "invalid",
            "attempts_remaining": remaining
        })

    # 6. Code valid - deactivate
    sms_code.is_active = False
    await session.commit()

    # 7. Find or create user
    result = await session.exec(select(User).where(User.phone_number == phone))
    user = result.first()

    if not user:
        user = User(
            phone_number=phone,
            phone_number_verified=True,
            phone_added_at=datetime.utcnow()
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    # 8. Create session
    token = generate_session_token()
    new_session = AuthSession(
        user_id=user.id,
        phone_number=phone,
        session_token_hash=hash_token(token)
    )
    session.add(new_session)
    await session.commit()

    # 9. Audit log
    await audit_log(
        session=session,
        action="auth.sms_verify_success",
        user_id=user.id,
        details={"phone_hash": phone_hash}
    )

    return {
        "status": "ok",
        "session_token": token
    }
```

### 5.2 Modified Endpoints

#### 5.2.1 GET `/auth/me`

**Changes**: Return phone number instead of/in addition to email

**Response**:
```json
{
  "authenticated": true,
  "phone_number": "+15551234567",
  "phone_verified": true,
  "user_id": 123
}
```

---

## 6. SMS Provider Evaluation

### 6.1 Provider Comparison Matrix

| Criteria | Twilio | AWS SNS | Vonage | MessageBird |
|----------|--------|---------|--------|-------------|
| **Global Coverage** | 180+ countries | 200+ countries | 190+ countries | 190+ countries |
| **Reliability** | 99.95% uptime | 99.9% uptime | 99.5% uptime | 99.5% uptime |
| **Cost (US)** | $0.0079/SMS | $0.00645/SMS | $0.0088/SMS | $0.0070/SMS |
| **Cost (International)** | $0.04-0.25/SMS | $0.05-0.50/SMS | $0.04-0.20/SMS | $0.03-0.15/SMS |
| **API Quality** | Excellent | Good | Good | Good |
| **Delivery Receipts** | Yes | Yes | Yes | Yes |
| **Phone Validation API** | Yes ($0.005/lookup) | No | Yes | Yes |
| **Compliance (TCPA, GDPR)** | Excellent | Good | Good | Good |
| **Developer Experience** | Excellent | Good | Good | Good |
| **Support** | 24/7 Premium | AWS Support | Business hours | Email |

### 6.2 Recommended Provider: Twilio (Primary) + AWS SNS (Fallback)

#### 6.2.1 Twilio - Primary Provider

**Pros**:
- Best-in-class reliability (99.95% uptime SLA)
- Excellent API documentation and SDKs
- Superior deliverability rates (95%+ in most regions)
- Phone number validation API (Lookup)
- Real-time delivery receipts
- Strong compliance support (TCPA, GDPR, HIPAA)
- 24/7 support
- Advanced features (retry logic, fallback numbers)

**Cons**:
- Slightly more expensive than alternatives
- Requires verification for some countries
- Rate limits on trial accounts

**Integration**:
```python
from twilio.rest import Client

class TwilioProvider:
    def __init__(self):
        self.client = Client(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN")
        )
        self.from_number = os.getenv("TWILIO_PHONE_NUMBER")

    async def send_sms(self, to_number: str, message: str) -> SMSResult:
        try:
            msg = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )
            return SMSResult(
                success=True,
                message_sid=msg.sid,
                status=msg.status,
                provider="twilio"
            )
        except TwilioException as e:
            return SMSResult(
                success=False,
                error=str(e),
                provider="twilio"
            )

    async def validate_phone(self, phone_number: str) -> PhoneValidationResult:
        try:
            lookup = self.client.lookups.v2.phone_numbers(phone_number).fetch()
            return PhoneValidationResult(
                is_valid=lookup.valid,
                carrier=lookup.carrier.get("name"),
                line_type=lookup.carrier.get("type"),
                country_code=lookup.country_code
            )
        except TwilioException:
            return PhoneValidationResult(is_valid=False)
```

#### 6.2.2 AWS SNS - Fallback Provider

**Pros**:
- Lower cost ($0.00645/SMS in US)
- Seamless integration if already using AWS
- Good global coverage
- No additional account needed if on AWS
- Simple API

**Cons**:
- Lower deliverability than Twilio (90-93%)
- No phone validation API
- Basic delivery receipts
- Less granular error handling

**Integration**:
```python
import boto3

class AWSSNSProvider:
    def __init__(self):
        self.client = boto3.client(
            'sns',
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )

    async def send_sms(self, to_number: str, message: str) -> SMSResult:
        try:
            response = self.client.publish(
                PhoneNumber=to_number,
                Message=message,
                MessageAttributes={
                    'AWS.SNS.SMS.SMSType': {
                        'DataType': 'String',
                        'StringValue': 'Transactional'
                    }
                }
            )
            return SMSResult(
                success=True,
                message_sid=response['MessageId'],
                status='sent',
                provider='aws_sns'
            )
        except Exception as e:
            return SMSResult(
                success=False,
                error=str(e),
                provider='aws_sns'
            )
```

### 6.3 Fallback Strategy

```python
class SMSService:
    def __init__(self):
        self.primary = TwilioProvider()
        self.fallback = AWSSNSProvider()

    async def send_verification_code(
        self,
        phone_number: str,
        code: str
    ) -> SMSResult:
        message = f"Your verification code is: {code}"

        # Try primary provider
        result = await self.primary.send_sms(phone_number, message)

        # If failed, try fallback
        if not result.success:
            logger.warning(f"Twilio failed, using SNS fallback: {result.error}")
            result = await self.fallback.send_sms(phone_number, message)

            if not result.success:
                logger.error(f"Both providers failed for {phone_number}")
                # Alert operations team
                await alert_ops_team("SMS_DELIVERY_FAILURE", result.error)

        return result
```

---

## 7. Security Considerations

### 7.1 Phone Number Security

#### 7.1.1 Privacy Protection

**Phone Number Hashing**:
```python
def hash_phone(phone: str) -> str:
    """
    Hash phone number for storage to prevent:
    - Data breaches exposing real phone numbers
    - Internal staff access to PII
    - Compliance with privacy regulations
    """
    return hashlib.sha256(phone.encode()).hexdigest()
```

**Storage Strategy**:
- `user.phone_number`: Encrypted at rest (database-level encryption)
- `auth_sms_code.phone_number_hash`: SHA-256 hashed (for lookups)
- Never log phone numbers in plaintext
- Mask in admin interfaces: `+1 (555) ***-**67`

#### 7.1.2 Phone Number Validation

**Validation Layers**:
1. **Client-side**: Format checking using `libphonenumber-js`
2. **Server-side**: Full validation using `phonenumbers` (Python)
3. **Provider-level**: Twilio Lookup API (optional, $0.005/lookup)

**Validation Checks**:
```python
class PhoneValidator:
    @staticmethod
    def validate_phone(phone: str) -> ValidationResult:
        try:
            parsed = phonenumbers.parse(phone, None)

            # Check 1: Valid format
            if not phonenumbers.is_valid_number(parsed):
                return ValidationResult(
                    is_valid=False,
                    error="Invalid phone number format"
                )

            # Check 2: Mobile number (not landline)
            number_type = phonenumbers.number_type(parsed)
            if number_type not in [
                phonenumbers.PhoneNumberType.MOBILE,
                phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE
            ]:
                return ValidationResult(
                    is_valid=False,
                    error="Phone number must be mobile"
                )

            # Check 3: Not VOIP/virtual
            # (requires Twilio Lookup for comprehensive check)

            return ValidationResult(
                is_valid=True,
                phone_type=number_type,
                country_code=parsed.country_code,
                national_number=parsed.national_number
            )

        except phonenumbers.NumberParseException:
            return ValidationResult(
                is_valid=False,
                error="Unable to parse phone number"
            )
```

### 7.2 SMS Code Security

#### 7.2.1 Code Generation

```python
def generate_verification_code() -> str:
    """
    Generate cryptographically secure 6-digit code.

    Security considerations:
    - Uses secrets module (not random)
    - 1,000,000 possible combinations
    - Combined with rate limiting (5 attempts) = 200,000:1 odds
    - 10-minute expiry reduces attack window
    """
    return f"{secrets.randbelow(1000000):06d}"
```

#### 7.2.2 Code Storage

```python
def hash_token(code: str) -> str:
    """
    Hash verification code before storage.

    Why hash?
    - Database breach won't expose valid codes
    - Even with database access, can't authenticate
    - Follows password hashing best practices
    """
    return hashlib.sha256(code.encode()).hexdigest()
```

**Note**: We use SHA-256 instead of bcrypt because:
- Codes are single-use and short-lived (10 minutes)
- We need fast verification for good UX
- We have other protections (rate limiting, lockout)

#### 7.2.3 Code Expiry

```python
# Code lifetime: 10 minutes
VERIFICATION_CODE_TTL = timedelta(minutes=10)

# Check on verification
if sms_code.expires_at < datetime.utcnow():
    sms_code.is_active = False
    await session.commit()
    raise HTTPException(400, detail="Code expired. Request a new one.")
```

### 7.3 Rate Limiting

#### 7.3.1 Multi-Layer Rate Limiting

```python
# Configuration
RATE_LIMITS = {
    # Per phone number
    "sms_phone": {
        "max_requests": 5,
        "window_seconds": 3600,  # 1 hour
        "lockout_minutes": 45
    },

    # Per IP address
    "sms_ip": {
        "max_requests": 20,
        "window_seconds": 3600,  # 1 hour
        "lockout_minutes": 60
    },

    # Per IP - different phone numbers (fraud detection)
    "sms_ip_unique_phones": {
        "max_requests": 10,
        "window_seconds": 3600,  # 1 hour
        "lockout_minutes": 120
    },

    # Verification attempts (per code)
    "sms_verify": {
        "max_attempts": 5,
        "lockout_minutes": 45
    },

    # Resend requests
    "sms_resend": {
        "min_interval_seconds": 60  # 1 minute between resends
    }
}
```

#### 7.3.2 Rate Limiter Implementation

```python
class RateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def check_rate_limit(
        self,
        key: str,
        limit_config: dict
    ) -> RateLimitResult:
        """
        Check if request is within rate limits.

        Uses Redis sliding window for accuracy and performance.
        """
        now = time.time()
        window = limit_config["window_seconds"]
        max_requests = limit_config["max_requests"]

        # Use Redis sorted set for sliding window
        pipe = self.redis.pipeline()

        # Remove old entries
        pipe.zremrangebyscore(key, 0, now - window)

        # Add current request
        pipe.zadd(key, {str(now): now})

        # Count requests in window
        pipe.zcard(key)

        # Set expiry
        pipe.expire(key, window)

        results = await pipe.execute()
        count = results[2]

        if count > max_requests:
            return RateLimitResult(
                allowed=False,
                current_count=count,
                limit=max_requests,
                retry_after=window
            )

        return RateLimitResult(
            allowed=True,
            current_count=count,
            limit=max_requests,
            remaining=max_requests - count
        )
```

### 7.4 Fraud Prevention

#### 7.4.1 Velocity Checks

**Phone Number Velocity**:
```python
async def check_phone_velocity(
    ip_address: str,
    session: AsyncSession
) -> VelocityCheckResult:
    """
    Check how many unique phone numbers have been used from this IP.

    Flags:
    - More than 10 unique phones in 1 hour: Suspicious
    - More than 25 unique phones in 24 hours: Highly suspicious
    """
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    result = await session.exec(
        select(func.count(distinct(AuthSMSCode.phone_number_hash)))
        .where(
            AuthSMSCode.ip_address == ip_address,
            AuthSMSCode.created_at > one_hour_ago
        )
    )

    count = result.first()

    risk_score = 0
    if count > 25:
        risk_score = 100
    elif count > 10:
        risk_score = 75
    elif count > 5:
        risk_score = 50

    return VelocityCheckResult(
        is_suspicious=count > 10,
        unique_phones=count,
        risk_score=risk_score
    )
```

**User Agent Pattern Detection**:
```python
async def check_user_agent_patterns(
    user_agent: str,
    session: AsyncSession
) -> PatternCheckResult:
    """
    Detect automated tools and bots.

    Checks:
    - Missing or generic user agents
    - Known bot signatures
    - Suspicious patterns (curl, python-requests, etc.)
    """
    suspicious_patterns = [
        r'python-requests',
        r'curl',
        r'wget',
        r'bot',
        r'crawler',
        r'spider',
        r'postman'
    ]

    if not user_agent or user_agent == "":
        return PatternCheckResult(
            is_suspicious=True,
            reason="Missing user agent",
            risk_score=75
        )

    for pattern in suspicious_patterns:
        if re.search(pattern, user_agent, re.IGNORECASE):
            return PatternCheckResult(
                is_suspicious=True,
                reason=f"Suspicious user agent: {pattern}",
                risk_score=90
            )

    return PatternCheckResult(
        is_suspicious=False,
        risk_score=0
    )
```

#### 7.4.2 Known Fraud Database

```python
class FraudDatabase:
    """
    Maintain a list of known fraudulent phone numbers and IPs.

    Sources:
    - Internal flagging (manual review)
    - Third-party fraud databases (optional)
    - Reported numbers
    """

    async def check_phone_reputation(
        self,
        phone_hash: str
    ) -> ReputationResult:
        # Check internal blocklist
        is_blocked = await self.redis.sismember(
            "fraud:blocked_phones",
            phone_hash
        )

        if is_blocked:
            return ReputationResult(
                is_blocked=True,
                reason="Phone number on blocklist",
                risk_score=100
            )

        # Check flagged list (requires review)
        is_flagged = await self.redis.sismember(
            "fraud:flagged_phones",
            phone_hash
        )

        if is_flagged:
            return ReputationResult(
                is_blocked=False,
                is_flagged=True,
                reason="Phone number flagged for review",
                risk_score=60
            )

        return ReputationResult(
            is_blocked=False,
            risk_score=0
        )
```

#### 7.4.3 CAPTCHA Integration (Future Enhancement)

```python
# For high-risk scenarios, require CAPTCHA before sending SMS

async def auth_start_sms(request: AuthStartSMSRequest, req: Request):
    # ... existing validation ...

    fraud_check = await fraud_detector.check_all(...)

    if fraud_check.risk_score >= 75:
        # Require CAPTCHA verification
        if not request.captcha_token:
            return {
                "status": "captcha_required",
                "captcha_site_key": RECAPTCHA_SITE_KEY
            }

        # Verify CAPTCHA
        captcha_valid = await verify_recaptcha(
            request.captcha_token,
            req.client.host
        )

        if not captcha_valid:
            raise HTTPException(400, detail="Invalid CAPTCHA")

    # ... proceed with SMS send ...
```

### 7.5 International Phone Number Support

#### 7.5.1 Country-Specific Rules

```python
COUNTRY_RULES = {
    "US": {
        "allow_landlines": False,
        "require_validation": True,
        "max_cost_per_sms": 0.01,
        "supported": True
    },
    "GB": {
        "allow_landlines": False,
        "require_validation": True,
        "max_cost_per_sms": 0.05,
        "supported": True
    },
    "CN": {
        "supported": False,  # Requires local infrastructure
        "reason": "Regulatory restrictions"
    },
    # ... more countries
}

async def validate_country_support(phone_number: str) -> CountrySupportResult:
    parsed = phonenumbers.parse(phone_number, None)
    region = phonenumbers.region_code_for_number(parsed)

    rules = COUNTRY_RULES.get(region, {"supported": True})

    if not rules.get("supported", True):
        return CountrySupportResult(
            supported=False,
            reason=rules.get("reason", "Country not supported")
        )

    return CountrySupportResult(supported=True, rules=rules)
```

---

## 8. Implementation Plan

### 8.1 Phase 1: Foundation (Week 1-2)

**Goal**: Set up SMS infrastructure without affecting existing email auth

#### Tasks:

1. **Database Migration**
   - Create `auth_sms_code` table
   - Create `fraud_detection_log` table
   - Add phone fields to `user` and `auth_session`
   - Run migration in dev/staging

2. **SMS Service Setup**
   - Create Twilio account
   - Purchase phone number(s)
   - Configure AWS SNS as fallback
   - Implement `sms_service.py` abstraction layer
   - Add environment variables

3. **Phone Validation Library**
   - Install `phonenumbers` (Python) and `libphonenumber-js` (JS)
   - Implement `phone_validation.py`
   - Add unit tests for validation logic

4. **Testing Infrastructure**
   - Set up Twilio test credentials
   - Create mock SMS provider for tests
   - Add integration tests for SMS sending

**Deliverables**:
- Database tables created
- SMS providers configured
- Phone validation working
- Test coverage > 80%

### 8.2 Phase 2: Backend API (Week 3-4)

**Goal**: Implement SMS authentication endpoints

#### Tasks:

1. **Rate Limiting Enhancement**
   - Upgrade to Redis-based rate limiter (from in-memory)
   - Implement phone-level rate limits
   - Implement IP-level rate limits
   - Add sliding window algorithm

2. **Fraud Detection Module**
   - Implement velocity checks
   - Implement user agent pattern detection
   - Create fraud database (Redis sets)
   - Add logging to `fraud_detection_log`

3. **Auth Endpoints**
   - Implement `POST /auth/start-sms`
   - Implement `POST /auth/verify-sms`
   - Update `GET /auth/me` to return phone
   - Add audit logging for all SMS auth events

4. **Error Handling**
   - Handle SMS delivery failures
   - Implement retry logic
   - Add fallback to secondary provider
   - Create alerts for delivery issues

**Deliverables**:
- SMS auth endpoints working
- Fraud detection active
- Rate limiting in place
- Error handling robust

### 8.3 Phase 3: Frontend (Week 5-6)

**Goal**: Build SMS authentication UI

#### Tasks:

1. **Phone Input Component**
   - Install `react-phone-number-input`
   - Create phone input with country selector
   - Add real-time validation
   - Add auto-formatting

2. **Verification Flow**
   - Create 6-digit code input component
   - Implement auto-submit on complete
   - Add resend functionality with cooldown
   - Add countdown timer for code expiry

3. **Error Handling**
   - Display validation errors
   - Show lockout messages with countdown
   - Handle network errors gracefully
   - Add retry mechanisms

4. **UI Polish**
   - Match existing email auth styling
   - Add loading states
   - Add success/error animations
   - Ensure mobile responsive

**Deliverables**:
- Phone login UI complete
- Smooth user experience
- Mobile-friendly
- Accessibility compliant

### 8.4 Phase 4: Dual Auth Support (Week 7)

**Goal**: Support both email and SMS authentication

#### Tasks:

1. **User Choice UI**
   - Add tab/toggle for email vs. SMS
   - Remember user preference (localStorage)
   - Allow switching between methods

2. **Backend Updates**
   - Update `User` model to support both
   - Allow linking phone to email account
   - Handle users with both email and phone

3. **Migration Path**
   - Allow existing users to add phone
   - Verify phone before switching
   - Account settings page for managing auth methods

**Deliverables**:
- Users can choose email or SMS
- Existing users can add phone
- Smooth migration experience

### 8.5 Phase 5: Testing & Launch (Week 8-9)

**Goal**: Comprehensive testing and production launch

#### Tasks:

1. **Testing**
   - End-to-end tests for full flow
   - Load testing (1000+ SMS/hour)
   - Security testing (penetration test)
   - International number testing
   - Edge case testing

2. **Monitoring & Alerts**
   - Set up SMS delivery monitoring
   - Create alerts for high failure rates
   - Dashboard for auth metrics
   - Cost tracking for SMS spend

3. **Documentation**
   - API documentation
   - User guide
   - Admin runbook
   - Incident response procedures

4. **Gradual Rollout**
   - Beta test with internal users (Week 8)
   - 10% of users (Week 9)
   - 50% of users (Week 9)
   - 100% rollout (Week 10)

**Deliverables**:
- Production-ready system
- Full monitoring in place
- Documentation complete
- Successful rollout

### 8.6 Implementation Checklist

```
Phase 1: Foundation
[ ] Create database migrations
[ ] Run migrations in dev
[ ] Run migrations in staging
[ ] Set up Twilio account
[ ] Purchase Twilio phone number
[ ] Configure AWS SNS
[ ] Implement sms_service.py
[ ] Implement phone_validation.py
[ ] Add environment variables
[ ] Write unit tests
[ ] Test SMS sending in dev

Phase 2: Backend API
[ ] Set up Redis for rate limiting
[ ] Implement Redis-based rate limiter
[ ] Implement fraud detection module
[ ] Create POST /auth/start-sms endpoint
[ ] Create POST /auth/verify-sms endpoint
[ ] Update GET /auth/me endpoint
[ ] Add audit logging
[ ] Implement error handling
[ ] Implement provider fallback
[ ] Write integration tests
[ ] Load test SMS endpoints

Phase 3: Frontend
[ ] Install phone input library
[ ] Create phone input component
[ ] Create verification code input
[ ] Implement resend logic
[ ] Add error handling
[ ] Style to match existing UI
[ ] Test on mobile devices
[ ] Accessibility audit
[ ] Browser compatibility testing

Phase 4: Dual Auth Support
[ ] Add auth method selector
[ ] Update User model
[ ] Implement phone linking
[ ] Create account settings page
[ ] Test migration flows
[ ] Update documentation

Phase 5: Testing & Launch
[ ] End-to-end tests
[ ] Load testing
[ ] Security audit
[ ] International testing
[ ] Set up monitoring
[ ] Create alerts
[ ] Write documentation
[ ] Internal beta test
[ ] Gradual rollout
[ ] Monitor metrics
```

---

## 9. Cost Analysis

### 9.1 SMS Provider Costs

#### 9.1.1 Twilio Pricing (Primary)

**Base Costs**:
- Phone Number: $1.00/month (US toll-free)
- SMS (US): $0.0079/message
- SMS (International): $0.04-$0.25/message (varies by country)
- Phone Lookup: $0.005/lookup (optional)

**Volume Pricing**:
- No volume discounts for SMS
- Enterprise plans available for $1M+ spend

#### 9.1.2 AWS SNS Pricing (Fallback)

**Base Costs**:
- Phone Number: Not required (uses AWS infrastructure)
- SMS (US): $0.00645/message
- SMS (International): $0.05-$0.50/message
- No phone validation API

### 9.2 Cost Per User Authentication

**Scenario 1: US User, Successful First Attempt**
```
Twilio SMS send:           $0.0079
Phone validation (opt):    $0.0050
Total:                     $0.0129 (with lookup)
                           $0.0079 (without lookup)
```

**Scenario 2: US User, Resend Required**
```
First SMS:                 $0.0079
Resend SMS:                $0.0079
Phone validation:          $0.0050 (once)
Total:                     $0.0208
```

**Scenario 3: International User (UK)**
```
Twilio SMS send:           $0.0400
Phone validation:          $0.0050
Total:                     $0.0450
```

### 9.3 Monthly Cost Projection

**Assumptions**:
- 10,000 users
- 80% US, 20% international
- 1.2 SMS per successful login (includes resends)
- 50% use phone lookup

**Calculation**:
```
US users:
  8,000 users × 1.2 SMS × $0.0079 = $75.84
  4,000 lookups × $0.0050 = $20.00

International users:
  2,000 users × 1.2 SMS × $0.04 = $96.00
  1,000 lookups × $0.0050 = $5.00

Monthly total: $196.84
Cost per auth: $0.0197
```

**With Growth**:
| Users | Monthly Cost | Cost/Auth |
|-------|-------------|-----------|
| 10,000 | $197 | $0.020 |
| 50,000 | $984 | $0.020 |
| 100,000 | $1,968 | $0.020 |
| 500,000 | $9,840 | $0.020 |
| 1,000,000 | $19,680 | $0.020 |

### 9.4 Cost Optimization Strategies

**1. Reduce Resend Rate**
- Clear UX to reduce user confusion
- Auto-detect code from SMS (iOS/Android)
- Target: < 10% resend rate
- Savings: ~$20/month per 10k users

**2. Selective Phone Lookup**
- Only validate on first use
- Cache validation results
- Use client-side validation first
- Savings: ~$10/month per 10k users

**3. Region-Specific Providers**
- Use cheaper providers for high-volume regions
- Bulk pricing negotiations
- Target: 10% cost reduction at scale

**4. Code Expiry Tuning**
- Balance security vs. resend rate
- Current: 10 minutes (recommended)
- Could extend to 15 minutes if resends are high

### 9.5 Cost Comparison vs. Email

**Email (Current - Resend API)**:
- 100 emails/day free
- $1/month per 1,000 additional emails
- 10,000 users: ~$10/month
- Cost per auth: $0.001

**SMS (Proposed - Twilio)**:
- No free tier
- $0.0079 per SMS (US)
- 10,000 users: ~$197/month
- Cost per auth: $0.020

**Cost Increase**: ~20x more expensive than email

**Justification**:
- Higher security (harder to compromise phone vs. email)
- Better deliverability (95%+ vs. 80% for email)
- Lower friction (no email client needed)
- Industry standard for financial apps
- Reduced account takeover risk

---

## 10. Rollback Strategy

### 10.1 Rollback Triggers

**Automatic Rollback Conditions**:
1. SMS delivery success rate < 80%
2. Auth endpoint error rate > 5%
3. Average response time > 3 seconds
4. Cost spike > 200% of projection

**Manual Rollback Triggers**:
1. Security incident detected
2. Provider outage > 1 hour
3. User complaints > threshold
4. Regulatory issue identified

### 10.2 Rollback Procedure

#### Phase 1: Immediate Reversion (< 5 minutes)

```bash
# 1. Switch traffic to email auth
kubectl set env deployment/frontend SMS_AUTH_ENABLED=false

# 2. Stop SMS provider calls
kubectl set env deployment/backend SMS_PROVIDER_ENABLED=false

# 3. Update login page to show email only
git revert <sms-ui-commit> --no-commit
git commit -m "Rollback: Disable SMS auth"
git push

# 4. Deploy
kubectl rollout restart deployment/frontend
kubectl rollout restart deployment/backend
```

#### Phase 2: Data Preservation (< 30 minutes)

```sql
-- Backup SMS auth data before cleanup
CREATE TABLE auth_sms_code_backup AS SELECT * FROM auth_sms_code;
CREATE TABLE fraud_detection_log_backup AS SELECT * FROM fraud_detection_log;

-- Do NOT delete user phone numbers (may be needed)
-- Just disable SMS auth flow
```

#### Phase 3: User Communication (< 1 hour)

```
Subject: Temporary Authentication Update

Hi [User],

We've temporarily switched back to email-based authentication
while we resolve a technical issue.

Your account is secure and no action is needed from you.

You can continue to log in using your email address.

Thanks for your patience,
The Shopping Agent Team
```

#### Phase 4: Investigation & Fix (1-7 days)

1. Analyze logs to identify root cause
2. Fix issue in development environment
3. Comprehensive testing
4. Gradual re-rollout (10% → 50% → 100%)

### 10.3 Data Migration Rollback

**Forward Migration** (Email → SMS):
- Users added phone numbers
- Sessions created with phone_number

**Rollback Strategy**:
```python
# Option 1: Keep phone numbers, use email for auth
# - No data loss
# - Users can still use email
# - Phone numbers preserved for future

# Option 2: Full cleanup (not recommended)
# - Remove phone numbers from users
# - Delete SMS codes
# - Risk: lose user preference data
```

**Recommended**: Option 1 - Keep data, switch auth method only

### 10.4 Rollback Testing

**Pre-Launch Rollback Drill**:
```bash
# 1. Deploy SMS auth to staging
# 2. Test full functionality
# 3. Execute rollback procedure
# 4. Verify email auth still works
# 5. Check no data loss
# 6. Measure rollback time (target: < 5 min)
```

---

## 11. Monitoring & Observability

### 11.1 Key Metrics

**SMS Delivery Metrics**:
```
- sms_sent_total (counter)
- sms_delivered_total (counter)
- sms_failed_total (counter)
- sms_delivery_rate (gauge) = delivered / sent
- sms_delivery_time_seconds (histogram)
```

**Authentication Metrics**:
```
- auth_sms_start_total (counter)
- auth_sms_verify_total (counter)
- auth_sms_verify_success_total (counter)
- auth_sms_verify_failed_total (counter)
- auth_sms_lockouts_total (counter)
- auth_sms_resend_total (counter)
```

**Fraud Detection Metrics**:
```
- fraud_checks_total (counter)
- fraud_detections_total (counter)
- fraud_blocks_total (counter)
- fraud_risk_score (histogram)
```

**Cost Metrics**:
```
- sms_cost_total (counter)
- sms_cost_by_country (counter)
- sms_cost_per_auth (gauge)
```

### 11.2 Alerts

**Critical Alerts** (Page on-call):
```yaml
- name: SMSDeliveryRateLow
  condition: sms_delivery_rate < 0.80 for 5m

- name: SMSProviderDown
  condition: sms_failed_total > 50 in 5m

- name: AuthEndpointDown
  condition: up{job="backend"} == 0

- name: FraudSpike
  condition: rate(fraud_detections_total[5m]) > 10
```

**Warning Alerts** (Slack notification):
```yaml
- name: SMSCostSpike
  condition: rate(sms_cost_total[1h]) > 2 × baseline

- name: ResendRateHigh
  condition: sms_resend_total / sms_sent_total > 0.20

- name: LockoutRateHigh
  condition: rate(auth_sms_lockouts_total[1h]) > 10
```

### 11.3 Dashboards

**SMS Authentication Dashboard**:
```
┌─────────────────────────────────────────────────┐
│ SMS Authentication Overview                      │
├─────────────────────────────────────────────────┤
│                                                  │
│ Delivery Rate (24h): ████████░░ 89.3%          │
│ Auth Success Rate:    ███████████ 94.1%        │
│ Avg Response Time:    247ms                     │
│ Cost (Today):         $12.45                    │
│                                                  │
│ ┌───────────────────┐ ┌──────────────────┐     │
│ │ SMS Sent/Hour     │ │ Delivery Status   │     │
│ │                   │ │                   │     │
│ │    ╱╲            │ │ Delivered: 89.3%  │     │
│ │   ╱  ╲           │ │ Failed:     8.1%  │     │
│ │  ╱    ╲___       │ │ Pending:    2.6%  │     │
│ └───────────────────┘ └──────────────────┘     │
│                                                  │
│ ┌───────────────────┐ ┌──────────────────┐     │
│ │ Provider Split    │ │ Fraud Detections  │     │
│ │                   │ │                   │     │
│ │ Twilio:   95.2%   │ │ High Risk: 12     │     │
│ │ AWS SNS:   4.8%   │ │ Medium:    45     │     │
│ └───────────────────┘ └──────────────────┘     │
└─────────────────────────────────────────────────┘
```

---

## 12. Security Audit Checklist

### 12.1 Pre-Launch Security Review

```
Authentication Security:
[ ] Codes are cryptographically generated (secrets module)
[ ] Codes are hashed before storage (SHA-256)
[ ] Codes expire after 10 minutes
[ ] Codes are single-use only
[ ] Rate limiting prevents brute force (5 attempts)
[ ] Lockout mechanism active (45 minutes)
[ ] Session tokens are cryptographically secure (32 bytes)
[ ] Session tokens are hashed before storage

Phone Number Security:
[ ] Phone numbers validated before use
[ ] Phone numbers normalized to E.164
[ ] Phone numbers hashed in logs
[ ] Phone numbers encrypted at rest
[ ] Phone numbers masked in admin UI
[ ] VOIP/virtual numbers blocked (optional)

Fraud Prevention:
[ ] IP-based rate limiting active
[ ] Phone velocity checks implemented
[ ] User agent pattern detection active
[ ] Fraud database in place
[ ] Manual review queue for high-risk
[ ] CAPTCHA ready for deployment

Network Security:
[ ] All SMS API calls over HTTPS
[ ] Twilio credentials in secrets manager
[ ] No credentials in code or logs
[ ] Network policies restrict backend access
[ ] SSL/TLS 1.2+ enforced

Data Privacy:
[ ] GDPR compliance reviewed
[ ] TCPA compliance reviewed (US)
[ ] Data retention policy defined
[ ] User consent flows implemented
[ ] Data export capability available
[ ] Data deletion capability available

Monitoring:
[ ] All auth events logged to audit_log
[ ] PII excluded from logs
[ ] Alerts configured for anomalies
[ ] Incident response plan documented
[ ] Security metrics dashboard created
```

---

## 13. Appendices

### 13.1 File Structure

```
apps/
├── frontend/
│   ├── app/
│   │   ├── login/
│   │   │   └── page.tsx                    # Modified: SMS auth UI
│   │   └── api/
│   │       └── auth/
│   │           ├── start-sms/
│   │           │   └── route.ts            # New: SMS start endpoint
│   │           ├── verify-sms/
│   │           │   └── route.ts            # New: SMS verify endpoint
│   │           ├── start/                   # Existing: Email start
│   │           └── verify/                  # Existing: Email verify
│   └── package.json                         # Add: phone input libraries
│
└── backend/
    ├── main.py                              # Modified: Add SMS endpoints
    ├── models.py                            # Modified: Add SMS models
    ├── database.py                          # Unchanged
    ├── sms_service.py                       # New: SMS provider abstraction
    ├── phone_validation.py                  # New: Phone validation logic
    ├── fraud_detection.py                   # New: Fraud detection
    ├── requirements.txt                     # Add: twilio, boto3, phonenumbers
    └── alembic/
        └── versions/
            └── abc123_add_sms_auth.py       # New: Database migration
```

### 13.2 Environment Variables

```bash
# Twilio Configuration (Primary)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+15551234567

# AWS SNS Configuration (Fallback)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAxxxxxxxxxxxxx
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxx
SMS_FALLBACK_ENABLED=true

# SMS Configuration
SMS_CODE_LENGTH=6
SMS_CODE_TTL_MINUTES=10
SMS_RESEND_COOLDOWN_SECONDS=60
SMS_MAX_ATTEMPTS=5
SMS_LOCKOUT_MINUTES=45

# Rate Limiting
RATE_LIMIT_SMS_PER_PHONE_HOUR=5
RATE_LIMIT_SMS_PER_IP_HOUR=20
RATE_LIMIT_VERIFY_ATTEMPTS=5

# Fraud Detection
FRAUD_DETECTION_ENABLED=true
FRAUD_PHONE_VELOCITY_THRESHOLD=10
FRAUD_RISK_SCORE_BLOCK=100
FRAUD_RISK_SCORE_CAPTCHA=75

# Feature Flags
SMS_AUTH_ENABLED=true
EMAIL_AUTH_ENABLED=true  # Keep both during transition
SMS_PHONE_LOOKUP_ENABLED=false  # Optional, costs extra
```

### 13.3 SMS Message Templates

**Verification Code Message** (US):
```
Your verification code is: {code}

This code expires in 10 minutes.

Shopping Agent
```

**Verification Code Message** (International):
```
Your Shopping Agent code: {code}

Valid for 10 minutes.
```

**Lockout Notification** (Optional):
```
Your account was temporarily locked due to multiple failed login attempts.

Try again in 45 minutes or contact support.

Shopping Agent
```

### 13.4 Database Indexes Summary

```sql
-- auth_sms_code indexes
CREATE INDEX idx_sms_phone_hash ON auth_sms_code(phone_number_hash);
CREATE INDEX idx_sms_active ON auth_sms_code(is_active);
CREATE INDEX idx_sms_created ON auth_sms_code(created_at);
CREATE INDEX idx_sms_expires ON auth_sms_code(expires_at);

-- fraud_detection_log indexes
CREATE INDEX idx_fraud_phone_hash ON fraud_detection_log(phone_number_hash);
CREATE INDEX idx_fraud_ip ON fraud_detection_log(ip_address);
CREATE INDEX idx_fraud_created ON fraud_detection_log(created_at);
CREATE INDEX idx_fraud_suspicious ON fraud_detection_log(is_suspicious);

-- user table indexes (new)
CREATE INDEX idx_user_phone ON user(phone_number);
CREATE UNIQUE INDEX uq_user_phone ON user(phone_number);

-- auth_session table indexes (new)
CREATE INDEX idx_session_phone ON auth_session(phone_number);
```

---

## Conclusion

This architecture provides a secure, scalable, and cost-effective SMS-based authentication system for the Shopping Agent application. The design:

1. **Maintains Security**: Multi-layer rate limiting, fraud detection, and code hashing
2. **Ensures Reliability**: Dual provider setup with automatic fallback
3. **Supports Scale**: Redis-based rate limiting, efficient database indexes
4. **Controls Costs**: ~$0.02 per authentication with optimization strategies
5. **Enables Rollback**: Clean reversion path to email authentication
6. **Provides Observability**: Comprehensive monitoring and alerting

The phased implementation plan allows for gradual rollout with minimal risk, while the dual authentication support ensures a smooth migration for existing users.

**Next Steps**:
1. Review and approve architecture
2. Provision Twilio account
3. Begin Phase 1 implementation (Foundation)
4. Set up monitoring infrastructure
5. Plan rollout schedule

---

**Document Version**: 1.0
**Last Updated**: 2024-01-20
**Author**: System Architecture Team
**Reviewers**: Security Team, Backend Team, Frontend Team
