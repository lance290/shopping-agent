# Clerk SMS Authentication Migration Architecture

## Executive Summary

This document outlines the migration from the current custom email-based authentication (6-digit codes via Resend) to **Clerk SMS authentication** for the Shopping Agent application. The architecture leverages Clerk's native SMS capabilities and provides a phased migration strategy to minimize disruption.

**Current Stack:**
- Frontend: Next.js 15 (App Router)
- BFF: Fastify proxy layer
- Backend: FastAPI with PostgreSQL (SQLModel)
- Auth: Custom email codes via Resend API

**Target Stack:**
- Frontend: Next.js 15 with Clerk SDK
- BFF: Fastify (minimal changes, proxy Clerk tokens)
- Backend: FastAPI with Clerk JWT verification
- Auth: Clerk SMS (phone number-based)

---

## Table of Contents

1. [Architecture Decision Records](#architecture-decision-records)
2. [Clerk Integration Architecture](#clerk-integration-architecture)
3. [Implementation Plan](#implementation-plan)
4. [Clerk SMS Configuration](#clerk-sms-configuration)
5. [Code Migration Strategy](#code-migration-strategy)
6. [User Experience Flow](#user-experience-flow)
7. [Security Considerations](#security-considerations)
8. [Migration Timeline](#migration-timeline)
9. [Cost Analysis](#cost-analysis)
10. [Rollback Plan](#rollback-plan)

---

## Architecture Decision Records

### ADR-001: Use Clerk SMS Instead of Custom SMS

**Status:** Proposed

**Context:**
- Current system uses custom email authentication with Resend
- Requirement is to migrate to SMS-based authentication
- Two options: Build custom SMS (Twilio) or use Clerk SMS

**Decision:** Use Clerk's built-in SMS authentication

**Rationale:**
1. **Security:** Clerk provides enterprise-grade security (SOC 2, HIPAA compliant)
2. **Built-in features:** MFA, session management, rate limiting, fraud detection
3. **Maintenance:** Eliminates need to build/maintain custom SMS flow
4. **Time-to-market:** Faster implementation (days vs weeks)
5. **International support:** Clerk handles phone number validation and international SMS
6. **Compliance:** GDPR, CCPA compliant out of the box

**Trade-offs:**
- **Vendor lock-in:** Moving to Clerk creates dependency (mitigated by JWT standard)
- **Cost:** ~$25/month + SMS costs vs DIY (justified by reduced engineering time)
- **Customization:** Less control over exact UX (acceptable for MVP)

**Consequences:**
- Must migrate existing users from email to phone
- Need to update all auth flows in frontend, BFF, and backend
- Database schema changes required

---

### ADR-002: Keep Dual Authentication During Migration

**Status:** Proposed

**Context:**
- Cannot force all users to re-authenticate immediately
- Need gradual migration path

**Decision:** Support both authentication systems during migration period

**Rationale:**
1. **Zero downtime:** Existing sessions remain valid
2. **User choice:** Users can opt-in to SMS auth
3. **Rollback capability:** Can revert if issues arise
4. **Testing in production:** Can test with subset of users

**Implementation:**
- Dual auth verification in backend
- Feature flag to enable/disable Clerk
- Migration prompt for existing users

---

### ADR-003: Backend JWT Verification Strategy

**Status:** Proposed

**Context:**
- Backend currently validates custom session tokens
- Clerk uses JWT tokens with public key verification

**Decision:** Verify Clerk JWTs in backend using Clerk's public JWKS

**Rationale:**
1. **Standard protocol:** JWT is industry standard
2. **No shared secrets:** Public key verification is more secure
3. **Clerk SDK support:** Python SDK handles verification
4. **Stateless:** No need to call Clerk API on every request

**Implementation:**
```python
from clerk_backend_api import Clerk

clerk = Clerk(bearer_auth=os.getenv("CLERK_SECRET_KEY"))

async def verify_clerk_token(token: str) -> Optional[dict]:
    try:
        # Clerk SDK verifies JWT signature using JWKS
        token_info = await clerk.jwt_templates.verify_token(token)
        return token_info
    except Exception:
        return None
```

---

## Clerk Integration Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                  │
│  ┌────────────────────────────────────────────────────┐    │
│  │  ClerkProvider (wraps entire app)                  │    │
│  │    ├─ SignIn component (phone number input)       │    │
│  │    ├─ useAuth() hook                              │    │
│  │    └─ useSession() hook                           │    │
│  └────────────────────────────────────────────────────┘    │
│           │ Clerk session token                             │
│           ▼                                                  │
└───────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│                      BFF (Fastify)                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Proxy layer                                       │    │
│  │    ├─ Forward Authorization header                │    │
│  │    ├─ No token verification (trust frontend)      │    │
│  │    └─ Optional: Add Clerk middleware for admin    │    │
│  └────────────────────────────────────────────────────┘    │
│           │ Authorization: Bearer <clerk_jwt>               │
│           ▼                                                  │
└───────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                        │
│  ┌────────────────────────────────────────────────────┐    │
│  │  JWT Verification Layer                            │    │
│  │    ├─ verify_clerk_jwt() dependency               │    │
│  │    ├─ Extract user_id from JWT claims             │    │
│  │    └─ Fallback: Legacy session token (migration)  │    │
│  └────────────────────────────────────────────────────┘    │
│           │                                                  │
│           ▼                                                  │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Database (PostgreSQL)                             │    │
│  │    ├─ user table (add clerk_user_id column)       │    │
│  │    ├─ auth_session (keep for migration period)    │    │
│  │    └─ audit_log (track auth method)               │    │
│  └────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────┘

External Services:
┌──────────────┐
│  Clerk API   │  - SMS delivery (via Twilio)
│              │  - User management
│              │  - Session management
└──────────────┘
```

### Data Flow: SMS Login

```
1. User enters phone number
   Frontend → Clerk.signIn.create({ identifier: "+1234567890" })

2. Clerk sends SMS code
   Clerk → Twilio → User's phone

3. User enters SMS code
   Frontend → Clerk.signIn.attemptFirstFactor({ strategy: "phone_code", code: "123456" })

4. Clerk returns session
   Clerk → Frontend (sets __session cookie + JWT)

5. Frontend makes API request
   Frontend → BFF (Authorization: Bearer <clerk_jwt>)

6. BFF proxies to backend
   BFF → Backend (Authorization: Bearer <clerk_jwt>)

7. Backend verifies JWT
   Backend → Clerk JWKS endpoint (public key)
   Backend → Extracts user_id from JWT claims
   Backend → Maps Clerk user_id to internal User record

8. Backend returns data
   Backend → BFF → Frontend
```

### Authentication State Management

**Frontend (Next.js):**
- Clerk manages session state automatically via cookies
- `useAuth()` hook provides `userId`, `isLoaded`, `isSignedIn`
- `useSession()` hook provides full session object
- No manual session token storage needed

**BFF (Fastify):**
- Passes through `Authorization` header unchanged
- No session storage or verification
- Optional: Can use Clerk middleware for admin routes

**Backend (FastAPI):**
- Verifies JWT on every protected request
- Caches JWKS public keys for performance
- Extracts `clerk_user_id` from JWT `sub` claim
- Maps to internal `User` model via `clerk_user_id` column

---

## Implementation Plan

### Phase 1: Setup Clerk (Day 1)

#### 1.1 Create Clerk Application

```bash
# 1. Sign up at https://dashboard.clerk.com
# 2. Create new application: "Shopping Agent"
# 3. Enable SMS authentication:
#    - Go to User & Authentication → Email, Phone, Username
#    - Disable email
#    - Enable phone number
#    - Set SMS as primary authentication
# 4. Configure phone number settings:
#    - Require phone number verification
#    - Enable international phone numbers
# 5. Copy API keys
```

**Required Environment Variables:**

```bash
# Frontend (.env.local)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxx
CLERK_SECRET_KEY=sk_test_xxx
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/login
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/

# Backend (.env)
CLERK_SECRET_KEY=sk_test_xxx
CLERK_PUBLISHABLE_KEY=pk_test_xxx  # For webhook verification

# BFF (.env) - optional, only if adding Clerk middleware
CLERK_SECRET_KEY=sk_test_xxx
```

#### 1.2 Install Dependencies

**Frontend:**
```bash
cd apps/frontend
pnpm add @clerk/nextjs
```

**Backend:**
```bash
cd apps/backend
pip install clerk-backend-api python-jose[cryptography] jwcrypto
# Add to requirements.txt:
# clerk-backend-api>=0.1.0
# python-jose[cryptography]>=3.3.0
# jwcrypto>=1.5.0
```

**BFF (optional):**
```bash
cd apps/bff
pnpm add @clerk/clerk-sdk-node
```

### Phase 2: Frontend Integration (Day 1-2)

#### 2.1 Wrap App with ClerkProvider

**File:** `/Volumes/PivotNorth/Shopping Agent/apps/frontend/app/layout.tsx`

```tsx
import { ClerkProvider } from '@clerk/nextjs';
import './globals.css';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body>{children}</body>
      </html>
    </ClerkProvider>
  );
}
```

#### 2.2 Replace Login Page with Clerk SignIn

**File:** `/Volumes/PivotNorth/Shopping Agent/apps/frontend/app/login/page.tsx`

**Option A: Use Clerk's Pre-built Component (Recommended for MVP)**

```tsx
import { SignIn } from '@clerk/nextjs';

export default function LoginPage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50">
      <SignIn
        appearance={{
          elements: {
            rootBox: "mx-auto",
            card: "shadow-md",
          },
        }}
        routing="path"
        path="/login"
        signUpUrl="/signup"
      />
    </main>
  );
}
```

**Option B: Custom Phone Input (More Control)**

```tsx
'use client';

import { useSignIn } from '@clerk/nextjs';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const { isLoaded, signIn, setActive } = useSignIn();
  const [phoneNumber, setPhoneNumber] = useState('');
  const [code, setCode] = useState('');
  const [step, setStep] = useState<'phone' | 'code'>('phone');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSendCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLoaded) return;
    setError('');
    setLoading(true);

    try {
      // Create sign-in with phone number
      await signIn.create({
        identifier: phoneNumber,
      });

      // Send SMS code
      await signIn.prepareFirstFactor({
        strategy: 'phone_code',
        phoneNumberId: signIn.supportedFirstFactors.find(
          (f) => f.strategy === 'phone_code'
        )?.phoneNumberId,
      });

      setStep('code');
    } catch (err: any) {
      setError(err.errors?.[0]?.message || 'Failed to send code');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLoaded) return;
    setError('');
    setLoading(true);

    try {
      const result = await signIn.attemptFirstFactor({
        strategy: 'phone_code',
        code,
      });

      if (result.status === 'complete') {
        await setActive({ session: result.createdSessionId });
        router.push('/');
      }
    } catch (err: any) {
      setError(err.errors?.[0]?.message || 'Invalid code');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md p-8 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold text-center mb-6 text-gray-900">
          Sign In
        </h1>

        {step === 'phone' ? (
          <form onSubmit={handleSendCode} className="space-y-4">
            <div>
              <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-1">
                Phone number
              </label>
              <input
                id="phone"
                type="tel"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                required
                disabled={loading}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                placeholder="+1 (555) 123-4567"
              />
            </div>

            {error && <p className="text-red-600 text-sm">{error}</p>}

            <button
              type="submit"
              disabled={loading || !phoneNumber}
              className="w-full py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Sending...' : 'Send verification code'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleVerifyCode} className="space-y-4">
            <p className="text-sm text-gray-600 mb-4">
              We sent a verification code to <strong>{phoneNumber}</strong>
            </p>

            <div>
              <label htmlFor="code" className="block text-sm font-medium text-gray-700 mb-1">
                Verification code
              </label>
              <input
                id="code"
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                required
                disabled={loading}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 text-center text-2xl tracking-widest text-gray-900"
                placeholder="000000"
              />
            </div>

            {error && <p className="text-red-600 text-sm">{error}</p>}

            <button
              type="submit"
              disabled={loading || code.length !== 6}
              className="w-full py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Verifying...' : 'Verify'}
            </button>

            <button
              type="button"
              onClick={() => {
                setStep('phone');
                setCode('');
                setError('');
              }}
              className="w-full py-2 px-4 text-gray-600 hover:text-gray-800 text-sm"
            >
              Use a different phone number
            </button>
          </form>
        )}
      </div>
    </main>
  );
}
```

#### 2.3 Update Middleware for Clerk

**File:** `/Volumes/PivotNorth/Shopping Agent/apps/frontend/middleware.ts`

```typescript
import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';

const isPublicRoute = createRouteMatcher(['/login(.*)', '/api/public(.*)']);

export default clerkMiddleware((auth, request) => {
  if (!isPublicRoute(request)) {
    auth().protect();
  }
});

export const config = {
  matcher: [
    // Skip Next.js internals and static files
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes
    '/(api|trpc)(.*)',
  ],
};
```

#### 2.4 Update API Routes to Use Clerk Tokens

**File:** `/Volumes/PivotNorth/Shopping Agent/apps/frontend/app/api/auth/constants.ts`

```typescript
export const BFF_URL = process.env.BFF_URL || 'http://localhost:8080';
export const COOKIE_NAME = 'sa_session'; // Keep for migration period
export const USE_CLERK = process.env.NEXT_PUBLIC_USE_CLERK === 'true'; // Feature flag
```

**Update all API routes to pass Clerk token:**

Example: `/Volumes/PivotNorth/Shopping Agent/apps/frontend/app/api/rows/route.ts` (new file)

```typescript
import { auth } from '@clerk/nextjs/server';
import { NextResponse } from 'next/server';

const BFF_URL = process.env.BFF_URL || 'http://localhost:8080';

export async function GET() {
  const { getToken } = auth();
  const token = await getToken();

  if (!token) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const response = await fetch(`${BFF_URL}/api/rows`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to fetch rows' }, { status: 500 });
  }
}
```

**Note:** The current architecture proxies through Next.js API routes to BFF. With Clerk, you can optionally call BFF directly from client using `useAuth()`:

```typescript
'use client';

import { useAuth } from '@clerk/nextjs';

export function useApi() {
  const { getToken } = useAuth();

  const fetchRows = async () => {
    const token = await getToken();
    const response = await fetch(`${process.env.NEXT_PUBLIC_BFF_URL}/api/rows`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.json();
  };

  return { fetchRows };
}
```

### Phase 3: Backend Integration (Day 2-3)

#### 3.1 Add Database Migration

**File:** `/Volumes/PivotNorth/Shopping Agent/apps/backend/alembic/versions/XXX_add_clerk_user_id.py`

```python
"""Add clerk_user_id to User table

Revision ID: XXX
Revises: YYY
Create Date: 2026-01-20
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add clerk_user_id column (nullable during migration)
    op.add_column('user', sa.Column('clerk_user_id', sa.String(), nullable=True))
    op.create_index('ix_user_clerk_user_id', 'user', ['clerk_user_id'], unique=True)

    # Add phone_number column
    op.add_column('user', sa.Column('phone_number', sa.String(), nullable=True))

    # Add auth_method column to track migration
    op.add_column('user', sa.Column('auth_method', sa.String(), nullable=False, server_default='email'))

def downgrade():
    op.drop_index('ix_user_clerk_user_id', table_name='user')
    op.drop_column('user', 'clerk_user_id')
    op.drop_column('user', 'phone_number')
    op.drop_column('user', 'auth_method')
```

**Update models.py:**

```python
class User(SQLModel, table=True):
    """Registered users."""
    __tablename__ = "user"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    phone_number: Optional[str] = Field(default=None, index=True)
    clerk_user_id: Optional[str] = Field(default=None, index=True, unique=True)
    auth_method: str = Field(default="email")  # "email", "phone_clerk", "dual"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_admin: bool = Field(default=False)
```

Run migration:
```bash
cd apps/backend
alembic revision --autogenerate -m "add_clerk_user_id"
alembic upgrade head
```

#### 3.2 Add Clerk JWT Verification

**File:** `/Volumes/PivotNorth/Shopping Agent/apps/backend/clerk_auth.py` (new file)

```python
"""Clerk JWT verification for FastAPI."""
import os
from typing import Optional
from fastapi import HTTPException, Header
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
import jwt
from jwt import PyJWKClient
from models import User

CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY", "")
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")

# Extract domain from publishable key (pk_test_xxx -> clerk.xxx.lcl.dev)
# For production: use your actual Clerk domain
CLERK_DOMAIN = os.getenv("CLERK_DOMAIN", "")
if not CLERK_DOMAIN and CLERK_PUBLISHABLE_KEY:
    # Auto-detect from publishable key
    if CLERK_PUBLISHABLE_KEY.startswith("pk_test_"):
        CLERK_DOMAIN = "https://clerk.your-domain.lcl.dev"  # Replace with actual
    else:
        CLERK_DOMAIN = "https://clerk.your-domain.com"

JWKS_URL = f"{CLERK_DOMAIN}/.well-known/jwks.json"

# Cache JWKS client
jwks_client = None
if CLERK_DOMAIN:
    jwks_client = PyJWKClient(JWKS_URL)


async def verify_clerk_jwt(token: str) -> Optional[dict]:
    """Verify Clerk JWT and return claims."""
    if not jwks_client:
        return None

    try:
        # Get signing key from JWKS
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # Verify JWT
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_exp": True, "verify_aud": False},
        )

        return claims
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception as e:
        print(f"[CLERK] JWT verification error: {e}")
        return None


async def get_or_create_user_from_clerk(
    clerk_user_id: str,
    phone_number: Optional[str],
    session: AsyncSession
) -> User:
    """Get or create user from Clerk JWT claims."""
    # Try to find existing user by clerk_user_id
    result = await session.exec(
        select(User).where(User.clerk_user_id == clerk_user_id)
    )
    user = result.first()

    if user:
        return user

    # Create new user
    # Generate email from phone if not provided (Clerk doesn't require email for phone auth)
    email = f"phone_{phone_number}@clerk.auto" if phone_number else f"clerk_{clerk_user_id}@clerk.auto"

    user = User(
        email=email,
        phone_number=phone_number,
        clerk_user_id=clerk_user_id,
        auth_method="phone_clerk"
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user
```

#### 3.3 Create Dual-Auth Dependency

**File:** `/Volumes/PivotNorth/Shopping Agent/apps/backend/auth_dependencies.py` (new file)

```python
"""Unified authentication dependencies supporting both legacy and Clerk auth."""
from typing import Optional
from fastapi import HTTPException, Header, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from database import get_session
from models import AuthSession, User
from clerk_auth import verify_clerk_jwt, get_or_create_user_from_clerk

USE_CLERK = os.getenv("USE_CLERK", "true").lower() == "true"


async def get_current_user(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
) -> Optional[User]:
    """
    Unified auth: Try Clerk JWT first, fallback to legacy session token.
    Returns None if not authenticated.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization[7:]

    # Try Clerk JWT verification first
    if USE_CLERK:
        clerk_claims = await verify_clerk_jwt(token)
        if clerk_claims:
            clerk_user_id = clerk_claims.get("sub")
            phone_number = clerk_claims.get("phone_number")

            user = await get_or_create_user_from_clerk(
                clerk_user_id=clerk_user_id,
                phone_number=phone_number,
                session=session
            )
            return user

    # Fallback to legacy session token
    from models import hash_token
    token_hash = hash_token(token)

    result = await session.exec(
        select(AuthSession)
        .where(AuthSession.session_token_hash == token_hash, AuthSession.revoked_at == None)
    )
    auth_session = result.first()

    if not auth_session:
        return None

    user = await session.get(User, auth_session.user_id)
    return user


async def require_auth(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
) -> User:
    """Require authentication (raises 401 if not authenticated)."""
    user = await get_current_user(authorization, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def require_admin(
    user: User = Depends(require_auth)
) -> User:
    """Require admin role."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
```

#### 3.4 Update FastAPI Endpoints

**File:** `/Volumes/PivotNorth/Shopping Agent/apps/backend/main.py`

Replace all `get_current_session()` calls with new dependencies:

```python
from auth_dependencies import require_auth, require_admin, get_current_user

# Example: Update create_row endpoint
@app.post("/rows", response_model=Row)
async def create_row(
    row: RowCreate,
    user: User = Depends(require_auth),  # Changed from get_current_session
    session: AsyncSession = Depends(get_session)
):
    # No need to check auth_session - user is already authenticated
    db_row = Row(
        title=row.title,
        status=row.status,
        budget_max=row.budget_max,
        currency=row.currency,
        user_id=user.id,  # Use user.id directly
        choice_factors=row.choice_factors,
        choice_answers=row.choice_answers
    )
    session.add(db_row)
    await session.commit()
    await session.refresh(db_row)

    # Create RequestSpec...
    return db_row


# Update all protected endpoints similarly
@app.get("/rows", response_model=List[RowReadWithBids])
async def read_rows(
    user: User = Depends(require_auth),
    include_archived: bool = Query(False),
    session: AsyncSession = Depends(get_session)
):
    result = await session.exec(
        select(Row)
        .where(Row.user_id == user.id)
        .options(selectinload(Row.bids).selectinload(Bid.seller))
    )
    rows = result.all()
    return rows
```

**Keep legacy auth endpoints for migration period:**

```python
# Keep existing /auth/start, /auth/verify, /auth/me, /auth/logout
# Mark as deprecated in docs
@app.post("/auth/start", response_model=AuthStartResponse, deprecated=True)
async def auth_start(...):
    """Legacy email authentication. Use Clerk for new signups."""
    # Existing implementation
    pass
```

### Phase 4: BFF Updates (Day 3)

The BFF currently just proxies requests. Minimal changes needed:

**Option A: No Changes (Recommended)**
- BFF passes through `Authorization` header unchanged
- Backend handles all verification

**Option B: Add Clerk Middleware (Optional, for admin routes)**

**File:** `/Volumes/PivotNorth/Shopping Agent/apps/bff/src/clerk.ts` (new file)

```typescript
import { createClerkClient } from '@clerk/clerk-sdk-node';

const clerkClient = createClerkClient({
  secretKey: process.env.CLERK_SECRET_KEY,
});

export async function verifyClerkToken(token: string): Promise<any> {
  try {
    const claims = await clerkClient.verifyToken(token);
    return claims;
  } catch (error) {
    return null;
  }
}
```

**Use in BFF routes (optional):**

```typescript
import { verifyClerkToken } from './clerk';

fastify.get('/api/admin/users', async (request, reply) => {
  const authHeader = request.headers.authorization;
  if (!authHeader?.startsWith('Bearer ')) {
    return reply.status(401).send({ error: 'Unauthorized' });
  }

  const token = authHeader.slice(7);
  const claims = await verifyClerkToken(token);

  if (!claims) {
    return reply.status(401).send({ error: 'Invalid token' });
  }

  // Forward to backend...
});
```

---

## Clerk SMS Configuration

### Dashboard Setup

1. **Navigate to Clerk Dashboard** → [https://dashboard.clerk.com](https://dashboard.clerk.com)

2. **Create Application**
   - Click "Add application"
   - Name: "Shopping Agent"
   - Select "Phone number" as primary authentication

3. **Configure Phone Authentication**
   - Go to **User & Authentication** → **Email, Phone, Username**
   - **Disable** email address
   - **Enable** phone number
   - **Require** phone number verification
   - Set phone number as **required** field

4. **SMS Provider Configuration**
   - Go to **User & Authentication** → **Multi-factor**
   - Enable **SMS code** verification
   - Clerk uses **Twilio** as default SMS provider
   - For production: Connect your own Twilio account for better rates
     - Go to **Configure** → **SMS**
     - Enter Twilio Account SID and Auth Token
     - This gives you wholesale SMS rates (~$0.0075/SMS vs Clerk's markup)

5. **Phone Number Validation**
   - Go to **User & Authentication** → **Restrictions**
   - **International numbers**: Enabled (default)
   - **Country restrictions**: Optional (e.g., US + Canada only)
   - **Block disposable numbers**: Enabled (recommended)
   - **Block VOIP numbers**: Enabled (recommended)

6. **Rate Limiting**
   - Go to **User & Authentication** → **Attack Protection**
   - Enable **Rate limiting**
   - SMS code attempts: 3 per 10 minutes (default)
   - Sign-in attempts: 10 per hour (default)
   - Lockout duration: 15 minutes (default)

7. **Session Management**
   - Go to **User & Authentication** → **Sessions**
   - Session lifetime: 7 days (default)
   - Idle timeout: 30 minutes (recommended for shopping app)
   - Multi-session: Enabled (allow login from multiple devices)

8. **Webhooks (Optional but Recommended)**
   - Go to **Webhooks**
   - Add endpoint: `https://your-backend.com/webhooks/clerk`
   - Subscribe to events:
     - `user.created` - Sync user to your DB
     - `user.updated` - Update phone number
     - `session.created` - Audit log
     - `session.ended` - Audit log

### SMS Provider Details

**Default (Clerk-managed Twilio):**
- No setup required
- Clerk handles all SMS delivery
- Cost: Included in Clerk pricing + markup on SMS
- Typical cost: ~$0.01-0.015 per SMS (US)
- International: ~$0.02-0.10 per SMS

**Custom Twilio (Recommended for Production):**
- Lower SMS costs (~$0.0075 per SMS for US)
- More control over sender ID
- Setup:
  1. Create Twilio account: [https://www.twilio.com/try-twilio](https://www.twilio.com/try-twilio)
  2. Get Account SID and Auth Token
  3. Buy phone number (~$1/month)
  4. Add to Clerk dashboard
  5. Verify webhook signature

**International Support:**
- Clerk automatically detects country from phone number
- Supports 200+ countries
- SMS costs vary by country
- Consider adding country selector in UI for better UX

### Testing SMS

**Development (Test Mode):**
- Clerk provides magic codes for testing
- Any phone number works in test mode
- Test code: `424242` (always works)
- No SMS actually sent
- Free (no SMS charges)

**Staging/Production:**
- Use real phone numbers
- Actual SMS sent via Twilio
- SMS costs apply
- Test with your own number first

---

## Code Migration Strategy

### Migration Phases

#### Phase 1: Parallel Authentication (Week 1)

**Goal:** Support both auth systems simultaneously

**Changes:**
1. Add `clerk_user_id` column to User table
2. Deploy backend with dual auth support
3. Keep all existing auth endpoints
4. Feature flag: `USE_CLERK=true` (backend), `NEXT_PUBLIC_USE_CLERK=false` (frontend)

**Testing:**
- Existing users continue using email auth
- New test users use Clerk SMS
- Both flows work independently

#### Phase 2: Soft Launch (Week 2)

**Goal:** Enable Clerk for new users, prompt existing users

**Changes:**
1. Set `NEXT_PUBLIC_USE_CLERK=true` for frontend
2. Add migration prompt for existing users
3. Monitor error rates and user feedback

**Migration Prompt:**

```tsx
// Add to dashboard for users without clerk_user_id
function MigrationBanner() {
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
      <h3 className="font-semibold text-blue-900 mb-2">
        Upgrade to phone authentication
      </h3>
      <p className="text-blue-800 text-sm mb-3">
        For better security, we now support phone number login with SMS codes.
      </p>
      <button className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
        Add phone number
      </button>
    </div>
  );
}
```

**Backend endpoint to link accounts:**

```python
@app.post("/auth/link-clerk")
async def link_clerk_account(
    request: LinkClerkRequest,
    user: User = Depends(require_auth),  # Must be logged in with legacy auth
    session: AsyncSession = Depends(get_session)
):
    """Link existing email account to Clerk phone auth."""
    # Verify Clerk token
    clerk_claims = await verify_clerk_jwt(request.clerk_token)
    if not clerk_claims:
        raise HTTPException(status_code=400, detail="Invalid Clerk token")

    # Update user record
    user.clerk_user_id = clerk_claims["sub"]
    user.phone_number = clerk_claims.get("phone_number")
    user.auth_method = "dual"  # Support both during transition

    session.add(user)
    await session.commit()

    return {"status": "linked"}
```

#### Phase 3: Deprecation (Week 3-4)

**Goal:** Migrate remaining users, deprecate legacy auth

**Changes:**
1. Show warning to users still on email auth
2. Set deadline for migration (e.g., 30 days)
3. Disable new email auth signups
4. Send migration emails

**Deprecation Warning:**

```tsx
function DeprecationWarning() {
  return (
    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
      <h3 className="font-semibold text-yellow-900 mb-2">
        Action required: Switch to phone authentication
      </h3>
      <p className="text-yellow-800 text-sm mb-3">
        Email authentication will be disabled on <strong>February 20, 2026</strong>.
        Please add your phone number to continue using the app.
      </p>
      <button className="bg-yellow-600 text-white px-4 py-2 rounded hover:bg-yellow-700">
        Migrate now
      </button>
    </div>
  );
}
```

#### Phase 4: Cleanup (Week 5+)

**Goal:** Remove legacy auth system

**Changes:**
1. Remove legacy auth endpoints (`/auth/start`, `/auth/verify`)
2. Drop `auth_login_code` and `auth_session` tables
3. Remove `email` column requirement (keep for audit)
4. Update `auth_method` to always be `phone_clerk`
5. Remove Resend API dependency

**Database cleanup migration:**

```python
def upgrade():
    # Drop legacy auth tables
    op.drop_table('auth_session')
    op.drop_table('auth_login_code')

    # Make clerk_user_id required
    op.alter_column('user', 'clerk_user_id', nullable=False)

    # Email becomes optional (historical data)
    op.alter_column('user', 'email', nullable=True)

def downgrade():
    # Cannot restore dropped tables
    raise Exception("This migration is not reversible")
```

### Data Migration Considerations

**User Identification:**
- Legacy: Users identified by `email`
- Clerk: Users identified by `phone_number` and `clerk_user_id`
- Challenge: Same user might have different email/phone

**Approach:**
1. **Require manual linking** (safest)
   - User logs in with email → prompted to add phone
   - Backend links accounts only after both auths verified

2. **Email-to-phone matching** (risky)
   - If Clerk provides email, try to match existing user
   - Only if email is verified in Clerk
   - Add audit log for matches

**Recommended:** Manual linking with grace period

### Handling Existing Sessions

**During Migration:**
- Legacy session cookies remain valid
- Clerk sessions use different cookie (`__session`)
- No conflict between the two

**After Migration:**
- Clear legacy cookies on next login
- Revoke all legacy sessions in database

```python
@app.post("/auth/migrate-session")
async def migrate_session(
    user: User = Depends(require_auth),
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """Migrate from legacy session to Clerk (called after user links accounts)."""
    if not authorization:
        return {"status": "no_legacy_session"}

    # Revoke legacy session
    token = authorization[7:]
    token_hash = hash_token(token)

    result = await session.exec(
        select(AuthSession).where(AuthSession.session_token_hash == token_hash)
    )
    auth_session = result.first()

    if auth_session:
        auth_session.revoked_at = datetime.utcnow()
        session.add(auth_session)
        await session.commit()

    return {"status": "migrated"}
```

---

## User Experience Flow

### New User Flow (Clerk SMS)

```
1. User visits /login
   ↓
2. Sees phone number input form
   ↓
3. Enters phone: "+1 (555) 123-4567"
   ↓
4. Clicks "Send verification code"
   ↓
5. Clerk sends SMS with 6-digit code
   ↓
6. User receives SMS: "Your code is 123456"
   ↓
7. User enters code in app
   ↓
8. Clerk verifies code
   ↓
9. Clerk creates user account (first time)
   ↓
10. Clerk sets session cookie + JWT
   ↓
11. Frontend redirects to /
   ↓
12. Backend receives JWT, creates User record
   ↓
13. User is logged in
```

**UX Improvements:**

1. **Auto-focus code input** after sending SMS
2. **Resend code** button (30-second cooldown)
3. **Countdown timer** showing code expiration (10 minutes)
4. **Error messages:**
   - "Phone number is invalid"
   - "Code has expired. Please request a new one."
   - "Too many attempts. Try again in 15 minutes."
5. **International phone input** with country selector

**Example Component:**

```tsx
import { PhoneInput } from 'react-international-phone-input';

function PhoneNumberInput({ value, onChange, disabled }) {
  return (
    <PhoneInput
      value={value}
      onChange={onChange}
      disabled={disabled}
      defaultCountry="US"
      enableSearch
      disableDialCodeAndPrefix={false}
      containerClassName="w-full"
      inputClassName="w-full px-3 py-2 border border-gray-300 rounded-md"
    />
  );
}
```

### Existing User Migration Flow

```
1. User logs in with email (legacy)
   ↓
2. Dashboard shows migration banner
   ↓
3. User clicks "Add phone number"
   ↓
4. Modal opens with phone input
   ↓
5. User enters phone number
   ↓
6. Clerk sends SMS code
   ↓
7. User enters code
   ↓
8. Frontend calls /auth/link-clerk with both tokens
   ↓
9. Backend verifies both, links accounts
   ↓
10. Success message: "Phone authentication enabled"
   ↓
11. Next login: User can use either email or phone
   ↓
12. After grace period: Email auth disabled
```

### Error Handling

**Common Errors:**

1. **Invalid phone number**
   - Message: "Please enter a valid phone number"
   - Clerk validates format automatically

2. **Phone already in use**
   - Message: "This phone number is already registered"
   - Allow account recovery flow

3. **SMS delivery failed**
   - Message: "Unable to send SMS. Please check your number and try again."
   - Log error to Clerk dashboard

4. **Code expired**
   - Message: "Verification code has expired. Please request a new one."
   - Show "Resend code" button

5. **Too many attempts**
   - Message: "Too many verification attempts. Please wait 15 minutes."
   - Show countdown timer
   - Suggest alternate auth method (if available)

6. **Network error**
   - Message: "Network error. Please check your connection."
   - Show retry button

**Rate Limiting UI:**

```tsx
function RateLimitMessage({ lockedUntil }: { lockedUntil: Date }) {
  const [timeLeft, setTimeLeft] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      const seconds = Math.max(0, Math.floor((lockedUntil.getTime() - Date.now()) / 1000));
      setTimeLeft(seconds);
      if (seconds === 0) {
        clearInterval(interval);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [lockedUntil]);

  const minutes = Math.floor(timeLeft / 60);
  const seconds = timeLeft % 60;

  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
      <p className="text-red-800 text-sm">
        Too many attempts. Please try again in{' '}
        <strong>
          {minutes}:{seconds.toString().padStart(2, '0')}
        </strong>
      </p>
    </div>
  );
}
```

### Fallback Options

**During Migration Period:**
- Users can choose "Sign in with email" or "Sign in with phone"
- Account linking available in settings

**After Migration:**
- Primary: Phone SMS
- Fallback: Email magic link (optional, via Clerk)
- Recovery: Admin-assisted account recovery

**Recommended:** Add email as backup authentication method in Clerk:
1. Enable both phone and email in Clerk settings
2. Require phone for signup
3. Allow adding email as backup in user settings
4. Use email for password reset / account recovery

---

## Security Considerations

### JWT Security

**Clerk JWT Structure:**
```json
{
  "iss": "https://clerk.your-domain.com",
  "sub": "user_2abc123xyz",
  "iat": 1705776000,
  "exp": 1705779600,
  "azp": "https://your-app.com",
  "phone_number": "+15551234567",
  "phone_number_verified": true
}
```

**Security Features:**
1. **RS256 signature** - Verified using Clerk's public key (JWKS)
2. **Short expiration** - Tokens expire in 1 hour (configurable)
3. **Automatic rotation** - Frontend automatically refreshes tokens
4. **Revocation** - Can revoke sessions in Clerk dashboard

**Best Practices:**
- Never log JWT tokens (contains PII)
- Verify token on every request (or use middleware)
- Check `exp` claim (expiration)
- Validate `iss` (issuer) matches your Clerk domain
- Cache JWKS keys (refresh every 24 hours)

### SMS Security Risks

**Attack Vectors:**

1. **SIM Swapping**
   - Attacker convinces carrier to transfer number
   - Mitigation: Clerk detects suspicious sign-ins, requires additional verification
   - Recommendation: Add optional 2FA (authenticator app)

2. **SMS Interception**
   - Attacker intercepts SMS via SS7 vulnerability
   - Mitigation: Use short-lived codes (10 minutes)
   - Recommendation: Consider adding device fingerprinting

3. **Phone Number Recycling**
   - Carrier reassigns old number to new person
   - Mitigation: Clerk tracks number changes, flags suspicious activity
   - Recommendation: Require email for important actions (delete account, change payment)

4. **Toll Fraud**
   - Attacker uses premium-rate numbers
   - Mitigation: Clerk blocks known premium numbers
   - Recommendation: Enable country restrictions

**Additional Security Layers:**

```python
# Example: Require email verification for sensitive actions
@app.delete("/account")
async def delete_account(
    user: User = Depends(require_auth),
    email_verification_code: str = Body(...),
    session: AsyncSession = Depends(get_session)
):
    """Delete account (requires email verification even with SMS auth)."""
    # Verify user's email code
    if not verify_email_code(user.email, email_verification_code):
        raise HTTPException(status_code=403, detail="Email verification required")

    # Proceed with deletion...
```

### Rate Limiting

**Clerk's Built-in Rate Limits:**
- 3 SMS code attempts per 10 minutes (per phone number)
- 10 sign-in attempts per hour (per IP)
- 100 sign-in attempts per day (per phone number)

**Additional Backend Rate Limiting:**

```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.post("/rows")
@limiter.limit("100/hour")
async def create_row(
    row: RowCreate,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session)
):
    # Rate limited to 100 rows per hour per user
    pass
```

### Compliance

**GDPR:**
- Phone numbers are PII - require consent
- Support data export (Clerk provides API)
- Support account deletion
- Clerk is GDPR compliant (EU data residency available)

**CCPA:**
- Allow users to download their data
- Allow users to delete their data
- Clerk provides compliance tools

**SOC 2:**
- Clerk is SOC 2 Type II certified
- Audit logs automatically tracked
- Session management compliant

**HIPAA (if applicable):**
- Clerk offers HIPAA compliance (enterprise plan)
- Requires BAA (Business Associate Agreement)
- Additional security controls required

---

## Migration Timeline

### Week 1: Setup and Testing

**Day 1-2: Clerk Setup**
- [ ] Create Clerk application
- [ ] Configure SMS authentication
- [ ] Add environment variables
- [ ] Install dependencies (frontend, backend)

**Day 3-4: Frontend Integration**
- [ ] Wrap app with ClerkProvider
- [ ] Create custom phone login page
- [ ] Update middleware
- [ ] Test login flow in development

**Day 5-7: Backend Integration**
- [ ] Add database migration (clerk_user_id column)
- [ ] Implement JWT verification
- [ ] Update auth dependencies
- [ ] Test dual auth with existing endpoints

### Week 2: Staging Deployment

**Day 8-9: Deploy to Staging**
- [ ] Deploy backend with dual auth
- [ ] Deploy frontend with Clerk enabled
- [ ] Test migration flow
- [ ] Load test SMS delivery

**Day 10-12: QA Testing**
- [ ] Test new user signup (phone)
- [ ] Test existing user login (email)
- [ ] Test account linking flow
- [ ] Test error cases
- [ ] Test rate limiting
- [ ] Test international phone numbers

**Day 13-14: Documentation**
- [ ] Update user documentation
- [ ] Create admin migration guide
- [ ] Document rollback procedure
- [ ] Prepare user communications

### Week 3: Production Rollout

**Day 15: Soft Launch**
- [ ] Deploy backend to production (dual auth)
- [ ] Enable Clerk for 10% of new signups (A/B test)
- [ ] Monitor error rates
- [ ] Monitor SMS delivery rates

**Day 16-17: Gradual Rollout**
- [ ] Increase to 50% of new signups
- [ ] Show migration prompt to existing users
- [ ] Monitor user feedback
- [ ] Fix any issues

**Day 18-21: Full Rollout**
- [ ] Enable Clerk for 100% of users
- [ ] Send migration emails to remaining users
- [ ] Monitor adoption rate
- [ ] Provide support for migration issues

### Week 4: Deprecation

**Day 22-28: Legacy Auth Deprecation**
- [ ] Show deprecation warnings on email login
- [ ] Disable new email signups
- [ ] Set deadline for migration (e.g., 30 days)
- [ ] Send reminder emails

### Week 5+: Cleanup

**After Grace Period:**
- [ ] Disable legacy auth endpoints
- [ ] Drop auth_login_code table
- [ ] Drop auth_session table
- [ ] Remove Resend API dependency
- [ ] Update documentation

---

## Cost Analysis

### Current Costs (Email Auth)

**Resend API:**
- Free tier: 100 emails/day
- Paid: $20/month for 50K emails
- Typical cost: $0.0004 per email

**Infrastructure:**
- Database storage: Minimal (session + code tables)
- No additional services

**Engineering:**
- Maintenance: ~2 hours/month
- Security updates: ~4 hours/quarter

**Total Current Monthly Cost:** ~$20 + engineering time

### Clerk Costs (SMS Auth)

**Clerk Pricing:**
- Free tier: 10,000 monthly active users (MAU)
- Pro: $25/month up to 10K MAU, then $0.02/MAU
- Enterprise: Custom pricing

**SMS Costs (Clerk-managed Twilio):**
- US SMS: ~$0.01-0.015 per message
- International: ~$0.02-0.10 per message
- Average: ~$0.012 per SMS

**Example Calculation (1,000 users):**
- Clerk: $25/month (under 10K MAU)
- SMS codes: 1,000 signups × 1.5 attempts × $0.012 = $18/month
- Total: ~$43/month

**Example Calculation (10,000 users):**
- Clerk: $25/month (at 10K MAU limit)
- SMS codes: 10,000 signups × 1.5 attempts × $0.012 = $180/month
- Total: ~$205/month

**Custom Twilio (Recommended for >5K users):**
- Twilio: $0.0075 per SMS (US)
- Phone number: $1.15/month
- 10,000 signups × 1.5 attempts × $0.0075 = $112.50/month
- Total: $25 (Clerk) + $112.50 (SMS) + $1.15 (number) = ~$138.65/month

### Cost Comparison

| Users/Month | Current (Email) | Clerk (Managed) | Clerk (Custom Twilio) | Savings |
|-------------|-----------------|-----------------|----------------------|---------|
| 1,000       | $20             | $43             | $36                  | -$16    |
| 5,000       | $20             | $115            | $81                  | -$61    |
| 10,000      | $20             | $205            | $139                 | -$119   |
| 50,000      | $40             | $905            | $606                 | -$566   |

**Value Add (Not in $ calculation):**
- Reduced security risk (Clerk handles security)
- Reduced engineering time (no maintenance)
- Better UX (Clerk's pre-built components)
- Compliance support (SOC 2, GDPR, HIPAA)
- Fraud detection built-in
- International support out-of-box

**ROI Calculation:**
- Engineering time saved: ~2 hours/month × $150/hour = $300/month
- Security risk reduction: Priceless
- Net savings: ~$180/month even at 10K users

**Recommendation:** Clerk is cost-effective for all scenarios when engineering time is factored in.

---

## Rollback Plan

### Rollback Triggers

**Immediate Rollback (Critical Issues):**
- SMS delivery failure rate >10%
- Authentication failure rate >5%
- Database corruption
- Clerk service outage >1 hour
- Security vulnerability discovered

**Gradual Rollback (Performance Issues):**
- User complaints >20% of cohort
- Adoption rate <50% after 2 weeks
- SMS costs exceed budget by >50%
- Integration issues with downstream systems

### Rollback Procedure

#### Phase 1: Immediate Mitigation (15 minutes)

1. **Disable Clerk on Frontend**
   ```bash
   # Set feature flag
   export NEXT_PUBLIC_USE_CLERK=false

   # Redeploy frontend
   cd apps/frontend
   pnpm build
   vercel deploy --prod
   ```

2. **Backend: Prioritize Legacy Auth**
   ```python
   # In auth_dependencies.py
   USE_CLERK = False  # Force disable

   # Redeploy backend
   git commit -am "Disable Clerk (rollback)"
   git push production main
   ```

3. **Notify Users**
   - Show banner: "We're experiencing technical difficulties. Please use email login."
   - Send email to affected users

#### Phase 2: Data Integrity Check (1 hour)

1. **Verify Database State**
   ```sql
   -- Check for orphaned Clerk users
   SELECT COUNT(*) FROM user WHERE clerk_user_id IS NOT NULL AND email IS NULL;

   -- Verify legacy sessions still work
   SELECT COUNT(*) FROM auth_session WHERE revoked_at IS NULL;
   ```

2. **Restore Access**
   ```python
   # If users lost access, create emergency sessions
   @app.post("/auth/emergency-access")
   async def emergency_access(email: EmailStr, session: AsyncSession = Depends(get_session)):
       # Send magic link (no password required)
       user = await session.exec(select(User).where(User.email == email)).first()
       if user:
           token = generate_session_token()
           # Create session and email link
   ```

#### Phase 3: Full Rollback (4 hours)

1. **Remove Clerk Integration**
   ```bash
   # Frontend
   cd apps/frontend
   git revert <clerk_integration_commit>
   pnpm install
   pnpm build
   vercel deploy --prod

   # Backend
   cd apps/backend
   git revert <clerk_integration_commit>
   alembic downgrade -1  # Rollback migration
   railway up
   ```

2. **Clean Up Clerk Users**
   ```sql
   -- Mark Clerk users for manual review
   UPDATE user
   SET auth_method = 'clerk_rollback'
   WHERE clerk_user_id IS NOT NULL;

   -- Preserve data for 90 days, then delete
   ```

3. **Communicate with Users**
   - Email all affected users
   - Offer manual account recovery
   - Explain what happened (transparency)

### Data Preservation

**During Rollback:**
- DO NOT delete `clerk_user_id` column
- DO NOT delete Clerk users from Clerk dashboard
- Keep audit logs for 90 days minimum

**After Rollback:**
- Export Clerk user data (phone numbers)
- Store in secure location
- Allow users to claim accounts manually

### Testing Rollback

**Before Launch:**
- Practice rollback on staging
- Document exact commands
- Time each phase
- Assign roles (who does what)

**Rollback Checklist:**

```markdown
## Rollback Checklist

- [ ] Disable Clerk feature flag (frontend)
- [ ] Disable Clerk verification (backend)
- [ ] Verify legacy auth works
- [ ] Check database integrity
- [ ] Test user login flow
- [ ] Send user communications
- [ ] Update status page
- [ ] Post-mortem within 24 hours
- [ ] Plan remediation
```

---

## Appendix

### Useful Clerk APIs

**Verify Token (Python):**
```python
from clerk_backend_api import Clerk

clerk = Clerk(bearer_auth=os.getenv("CLERK_SECRET_KEY"))

# Verify JWT
token_info = await clerk.jwt_templates.verify_token(token)

# Get user details
user = await clerk.users.get(user_id=token_info["sub"])

# List sessions
sessions = await clerk.sessions.list(user_id=user.id)

# Revoke session
await clerk.sessions.revoke(session_id=session.id)
```

**Create User (Webhook Handler):**
```python
from fastapi import Request
import svix

@app.post("/webhooks/clerk")
async def clerk_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    # Verify webhook signature
    webhook = svix.Webhook(os.getenv("CLERK_WEBHOOK_SECRET"))
    payload = await request.body()
    headers = dict(request.headers)

    try:
        event = webhook.verify(payload, headers)
    except svix.errors.WebhookVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle event
    if event["type"] == "user.created":
        data = event["data"]
        user = User(
            clerk_user_id=data["id"],
            phone_number=data["phone_numbers"][0]["phone_number"] if data["phone_numbers"] else None,
            auth_method="phone_clerk"
        )
        session.add(user)
        await session.commit()

    return {"status": "ok"}
```

### Environment Variables Reference

**Frontend (.env.local):**
```bash
# Clerk
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxx
CLERK_SECRET_KEY=sk_test_xxx
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/login
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/

# Feature Flags
NEXT_PUBLIC_USE_CLERK=true

# BFF
NEXT_PUBLIC_BFF_URL=http://localhost:8080
BFF_URL=http://localhost:8080
```

**Backend (.env):**
```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5435/shopping_agent

# Clerk
CLERK_SECRET_KEY=sk_test_xxx
CLERK_PUBLISHABLE_KEY=pk_test_xxx
CLERK_DOMAIN=https://clerk.your-domain.com
CLERK_WEBHOOK_SECRET=whsec_xxx

# Feature Flags
USE_CLERK=true

# Legacy (Keep during migration)
RESEND_API_KEY=re_xxx
FROM_EMAIL=Agent Shopper <shopper@info.xcor-cto.com>
```

**BFF (.env):**
```bash
# Backend
BACKEND_URL=http://localhost:8000

# Clerk (Optional)
CLERK_SECRET_KEY=sk_test_xxx

# CORS
CORS_ORIGIN=http://localhost:3000
```

### Database Schema Changes

**Migration: Add Clerk Support**
```sql
-- Add columns to user table
ALTER TABLE user ADD COLUMN clerk_user_id VARCHAR(255) UNIQUE;
ALTER TABLE user ADD COLUMN phone_number VARCHAR(50);
ALTER TABLE user ADD COLUMN auth_method VARCHAR(20) DEFAULT 'email';

CREATE INDEX ix_user_clerk_user_id ON user(clerk_user_id);
CREATE INDEX ix_user_phone_number ON user(phone_number);

-- Add audit column
ALTER TABLE audit_log ADD COLUMN auth_provider VARCHAR(50);

-- No changes to existing tables during migration
-- Keep auth_session and auth_login_code for rollback capability
```

**Migration: Cleanup (After Migration)**
```sql
-- Make clerk_user_id required
ALTER TABLE user ALTER COLUMN clerk_user_id SET NOT NULL;

-- Make email optional (now just metadata)
ALTER TABLE user ALTER COLUMN email DROP NOT NULL;

-- Drop legacy auth tables
DROP TABLE auth_session;
DROP TABLE auth_login_code;
```

### Monitoring and Alerts

**Key Metrics:**

1. **Authentication Success Rate**
   - Target: >98%
   - Alert: <95%
   - Query: `(successful_logins / total_login_attempts) * 100`

2. **SMS Delivery Rate**
   - Target: >99%
   - Alert: <95%
   - Check Clerk dashboard

3. **Average Login Time**
   - Target: <30 seconds
   - Alert: >60 seconds
   - Track from "Send code" to "Logged in"

4. **Migration Adoption Rate**
   - Target: >50% after 2 weeks
   - Track: `users_with_clerk_id / total_users`

5. **Cost Per Authentication**
   - Target: <$0.02
   - Track: `total_sms_cost / total_authentications`

**Alerts to Set Up:**

```yaml
# Example: DataDog / PagerDuty alert
alert:
  name: "Clerk Auth Failure Rate High"
  query: "auth_failure_rate > 5%"
  window: "5 minutes"
  notify: ["on-call-engineer@company.com"]
  severity: "critical"

alert:
  name: "SMS Delivery Failure"
  query: "sms_delivery_rate < 95%"
  window: "15 minutes"
  notify: ["on-call-engineer@company.com", "clerk-support@clerk.com"]
  severity: "high"
```

### Support Resources

**Clerk Support:**
- Dashboard: [https://dashboard.clerk.com](https://dashboard.clerk.com)
- Docs: [https://clerk.com/docs](https://clerk.com/docs)
- Discord: [https://clerk.com/discord](https://clerk.com/discord)
- Email: support@clerk.com
- Status: [https://status.clerk.com](https://status.clerk.com)

**SMS Provider (Twilio):**
- Console: [https://console.twilio.com](https://console.twilio.com)
- Docs: [https://www.twilio.com/docs](https://www.twilio.com/docs)
- Support: [https://support.twilio.com](https://support.twilio.com)

### Related Documentation

- [Clerk Next.js Quickstart](https://clerk.com/docs/quickstarts/nextjs)
- [Clerk Backend API (Python)](https://github.com/clerk/clerk-sdk-python)
- [JWT Verification](https://clerk.com/docs/backend-requests/handling/manual-jwt)
- [Webhooks](https://clerk.com/docs/integrations/webhooks/overview)
- [Phone Number Authentication](https://clerk.com/docs/authentication/configuration/phone-number)

---

## Summary

This architecture provides a complete migration path from custom email authentication to Clerk SMS authentication. Key highlights:

1. **Phased Approach**: Dual authentication during migration minimizes risk
2. **Clerk Native SMS**: Leverages Clerk's built-in SMS capabilities (no custom SMS integration needed)
3. **JWT-based**: Modern, stateless authentication using industry standards
4. **Minimal BFF Changes**: Proxy layer requires no significant updates
5. **User-Centric**: Gradual migration with account linking preserves user experience
6. **Rollback Ready**: Comprehensive rollback plan for risk mitigation
7. **Cost-Effective**: Despite higher per-auth cost, engineering time savings justify expense

**Next Steps:**
1. Review and approve architecture
2. Create Clerk account and configure SMS
3. Begin Phase 1 implementation (setup and testing)
4. Follow migration timeline
5. Monitor metrics post-launch

**Questions or Concerns:**
- Reach out to Clerk support for SMS provider optimization
- Test international phone numbers in staging before production
- Consider adding email as backup auth method for account recovery
- Plan user communication strategy early (especially for deprecation)
