# Identity & Permissions Model

**Status:** Draft  
**Created:** 2026-01-31  
**Last Updated:** 2026-01-31

---

## 1. Overview

BuyAnything.ai supports multiple user types with different access patterns. This document defines the identity model, authentication methods, and permission matrix.

---

## 2. User Roles

### 2.1 Role Definitions

| Role | Description | Primary Actions |
|------|-------------|-----------------|
| **Buyer** | Creates RFPs, searches, selects, purchases | Full workspace control |
| **Collaborator** | Invited to review and vote | View, like, comment |
| **Seller** | Responds to RFPs with quotes | Submit quotes, view own quotes |
| **Admin** | Platform operator | All actions, user management |

### 2.2 Role Assignment

```typescript
interface User {
  id: string;
  email: string;
  name?: string;
  role: "buyer" | "seller" | "admin";
  created_at: Date;
}

interface ProjectMembership {
  user_id: string;
  project_id: number;
  role: "owner" | "collaborator";
  invited_at: Date;
  accepted_at?: Date;
}
```

---

## 3. Authentication Methods

### 3.1 Primary: Email Magic Link

**Flow:**
1. User enters email on login page
2. System sends magic link to email
3. User clicks link → authenticated session created
4. Session stored in HTTP-only cookie

**Implementation:**
```typescript
// POST /auth/magic-link
{
  "email": "buyer@example.com"
}

// Email contains:
// https://buyanything.ai/auth/verify?token=abc123&redirect=/projects
```

**Security:**
- Token expires in 15 minutes
- Single-use (invalidated after click)
- Rate limited: 3 requests per email per hour

### 3.2 OAuth (Google)

**Flow:**
1. User clicks "Sign in with Google"
2. OAuth redirect → Google consent
3. Callback with auth code
4. Exchange for tokens, create/link user

**Implementation:**
- Use `@clerk/nextjs` or similar
- Store OAuth provider ID for linking

### 3.3 Quote Magic Link (Sellers)

**Special case:** Sellers can submit quotes without creating an account.

**Flow:**
1. Seller receives outreach email with magic link
2. Link contains row context + seller token
3. Seller fills quote form
4. On submit: quote saved, optional account creation prompt

**Token Structure:**
```typescript
interface QuoteMagicLink {
  token: string;           // Unique identifier
  row_id: number;          // Target row
  seller_email: string;    // Pre-filled
  expires_at: Date;        // 7 days from creation
  used: boolean;
}
```

### 3.4 Share Link Access

**Flow:**
1. Buyer creates share link for project/row
2. Link contains access token
3. Viewer clicks link → read-only access
4. Optional: prompt to sign in for full features

**Access Levels:**
```typescript
type ShareLinkAccess = "view" | "comment" | "collaborate";
```

---

## 4. Permission Matrix

### 4.1 Project-Level Permissions

| Action | Owner | Collaborator | Viewer (share link) | Anonymous |
|--------|-------|--------------|---------------------|-----------|
| View project | ✅ | ✅ | ✅ | ❌ |
| Create row | ✅ | ❌ | ❌ | ❌ |
| Edit row | ✅ | ❌ | ❌ | ❌ |
| Delete row | ✅ | ❌ | ❌ | ❌ |
| Invite collaborator | ✅ | ❌ | ❌ | ❌ |
| Create share link | ✅ | ❌ | ❌ | ❌ |

### 4.2 Row-Level Permissions

| Action | Owner | Collaborator | Viewer | Seller |
|--------|-------|--------------|--------|--------|
| View row | ✅ | ✅ | ✅ | Own quotes only |
| Search/refresh | ✅ | ❌ | ❌ | ❌ |
| Trigger outreach | ✅ | ❌ | ❌ | ❌ |
| View outreach status | ✅ | ✅ | ❌ | ❌ |

### 4.3 Tile/Bid-Level Permissions

| Action | Owner | Collaborator | Viewer | Seller |
|--------|-------|--------------|--------|--------|
| View tile | ✅ | ✅ | ✅ | Own only |
| Like tile | ✅ | ✅ | ❌ | ❌ |
| Comment on tile | ✅ | ✅ | ❌ | ❌ |
| Select tile | ✅ | ❌ | ❌ | ❌ |
| Checkout | ✅ | ❌ | ❌ | ❌ |

### 4.4 Quote Permissions

| Action | Owner | Collaborator | Seller |
|--------|-------|--------------|--------|
| View quotes | ✅ | ✅ | Own only |
| Accept quote | ✅ | ❌ | ❌ |
| Reject quote | ✅ | ❌ | ❌ |
| Edit quote | ❌ | ❌ | ✅ (before accepted) |
| Withdraw quote | ❌ | ❌ | ✅ |

---

## 5. Session Management

### 5.1 Session Structure

```typescript
interface Session {
  id: string;
  user_id: string;
  created_at: Date;
  expires_at: Date;
  last_activity: Date;
  ip_address: string;
  user_agent: string;
}
```

### 5.2 Session Policies

| Policy | Value |
|--------|-------|
| Session duration | 30 days |
| Inactivity timeout | 7 days |
| Max concurrent sessions | 5 |
| Session refresh | On activity, extend 7 days |

### 5.3 Cookie Configuration

```typescript
const sessionCookie = {
  name: "ba_session",
  httpOnly: true,
  secure: true,          // HTTPS only
  sameSite: "lax",
  maxAge: 30 * 24 * 60 * 60  // 30 days in seconds
};
```

---

## 6. Authorization Middleware

### 6.1 Backend (FastAPI)

```python
# apps/backend/auth/middleware.py

async def require_auth(request: Request) -> User:
    """Require authenticated user."""
    session = await get_session_from_cookie(request)
    if not session:
        raise HTTPException(401, "Authentication required")
    return await get_user(session.user_id)

async def require_project_access(
    request: Request,
    project_id: int,
    min_role: str = "viewer"
) -> ProjectMembership:
    """Require access to specific project."""
    user = await require_auth(request)
    membership = await get_membership(user.id, project_id)
    
    if not membership:
        # Check if share link access
        share_token = request.query_params.get("share")
        if share_token:
            access = await verify_share_link(share_token, project_id)
            if access:
                return ProjectMembership(role="viewer", ...)
        raise HTTPException(403, "Access denied")
    
    if not has_sufficient_role(membership.role, min_role):
        raise HTTPException(403, "Insufficient permissions")
    
    return membership
```

### 6.2 BFF (TypeScript)

```typescript
// apps/bff/src/auth/middleware.ts

export async function requireAuth(
  request: FastifyRequest,
  reply: FastifyReply
): Promise<User> {
  const session = await getSessionFromCookie(request);
  if (!session) {
    reply.code(401).send({ error: "Authentication required" });
    throw new Error("Unauthorized");
  }
  return getUser(session.userId);
}

export function requireRole(...roles: string[]) {
  return async (request: FastifyRequest, reply: FastifyReply) => {
    const user = await requireAuth(request, reply);
    if (!roles.includes(user.role)) {
      reply.code(403).send({ error: "Insufficient permissions" });
      throw new Error("Forbidden");
    }
    request.user = user;
  };
}
```

---

## 7. Database Schema

### 7.1 Users Table (existing)

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    role VARCHAR(20) DEFAULT 'buyer',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 7.2 Sessions Table

```sql
CREATE TABLE sessions (
    id VARCHAR(64) PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);
```

### 7.3 Magic Links Table

```sql
CREATE TABLE magic_links (
    token VARCHAR(64) PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL,  -- 'login', 'quote'
    context JSONB,              -- Additional data (row_id for quotes)
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP
);

CREATE INDEX idx_magic_links_email ON magic_links(email);
```

### 7.4 Project Memberships Table

```sql
CREATE TABLE project_memberships (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    project_id INTEGER REFERENCES projects(id),
    role VARCHAR(20) NOT NULL,  -- 'owner', 'collaborator'
    invited_by INTEGER REFERENCES users(id),
    invited_at TIMESTAMP DEFAULT NOW(),
    accepted_at TIMESTAMP,
    UNIQUE(user_id, project_id)
);
```

---

## 8. API Endpoints

### 8.1 Authentication

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/magic-link` | Request magic link |
| GET | `/auth/verify` | Verify magic link token |
| POST | `/auth/oauth/google` | OAuth callback |
| POST | `/auth/logout` | End session |
| GET | `/auth/me` | Get current user |

### 8.2 Invitations

| Method | Path | Description |
|--------|------|-------------|
| POST | `/projects/{id}/invite` | Invite collaborator |
| GET | `/invitations` | List pending invitations |
| POST | `/invitations/{id}/accept` | Accept invitation |
| POST | `/invitations/{id}/decline` | Decline invitation |

---

## 9. Security Considerations

### 9.1 Token Generation

```python
import secrets

def generate_token(length: int = 32) -> str:
    """Generate cryptographically secure token."""
    return secrets.token_urlsafe(length)
```

### 9.2 Rate Limiting

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/auth/magic-link` | 3 per email | 1 hour |
| `/auth/verify` | 10 per IP | 1 minute |
| `/auth/oauth/*` | 10 per IP | 1 minute |

### 9.3 Audit Logging

```python
logger.info(
    "Authentication event",
    extra={
        "event": "login_success",
        "user_id": user.id,
        "method": "magic_link",
        "ip_address": request.client.host
    }
)
```
