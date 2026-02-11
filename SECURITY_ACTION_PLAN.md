# Security Action Plan - Critical Issues

**Project**: Shopping Agent
**Date**: 2026-02-10
**Status**: URGENT - 3 Critical Security Issues Identified

---

## Priority 1: Fix CSP Policy (SECURITY-001)

**Risk Level**: CRITICAL (Allows XSS attacks)
**Estimated Time**: 1 hour
**File**: `apps/backend/security/headers.py`

### Current Code (UNSAFE):
```python
csp_directives = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # ❌ UNSAFE
    "style-src 'self' 'unsafe-inline'",                 # ❌ UNSAFE
    # ...
]
```

### Fixed Code:
```python
import secrets

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, is_production: bool = False):
        super().__init__(app)
        self.is_production = is_production

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Generate nonce for this request
        nonce = secrets.token_urlsafe(16)

        # Store nonce in request state for templates to use
        request.state.csp_nonce = nonce

        # Strict CSP with nonce-based inline scripts
        csp_directives = [
            "default-src 'self'",
            f"script-src 'self' 'nonce-{nonce}'",  # ✓ SAFE
            f"style-src 'self' 'nonce-{nonce}'",   # ✓ SAFE
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]

        if self.is_production:
            csp_directives.append("upgrade-insecure-requests")

        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        # ... rest of headers
        return response
```

### Testing:
```bash
# Test CSP is working:
curl -I https://your-backend.railway.app/health | grep -i content-security-policy

# Should NOT contain 'unsafe-inline' or 'unsafe-eval'
```

---

## Priority 2: Enable CSRF in All Environments (SECURITY-002)

**Risk Level**: HIGH (CSRF attacks possible)
**Estimated Time**: 30 minutes
**File**: `apps/backend/main.py`

### Current Code (UNSAFE):
```python
# Only enables CSRF in production
if CSRF_SECRET and IS_PRODUCTION:
    app.add_middleware(CSRFProtectionMiddleware)
```

### Fixed Code:
```python
# Enable CSRF in all environments where secret is configured
IS_PRODUCTION = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("ENVIRONMENT") == "production")

# Set CSRF secret from environment (required for CSRF protection)
CSRF_SECRET = os.getenv("CSRF_SECRET_KEY")

if CSRF_SECRET:
    set_csrf_secret(CSRF_SECRET)
    app.add_middleware(CSRFProtectionMiddleware)
    print(f"[SECURITY] CSRF protection enabled (production={IS_PRODUCTION})")
else:
    print("[SECURITY] WARNING: CSRF_SECRET_KEY not set - CSRF protection disabled")
    if IS_PRODUCTION:
        # Make CSRF mandatory in production
        raise RuntimeError(
            "CSRF_SECRET_KEY is REQUIRED in production. "
            "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
```

### Environment Setup:
```bash
# Generate CSRF secret
python -c "import secrets; print(secrets.token_urlsafe(48))"

# Add to Railway environment variables:
# CSRF_SECRET_KEY=<generated-secret>

# Add to local .env:
echo "CSRF_SECRET_KEY=<generated-secret>" >> apps/backend/.env
```

### Testing:
```bash
# Test CSRF protection is working:
# 1. Try POST without CSRF token (should fail)
curl -X POST https://your-backend.railway.app/rows \
  -H "Content-Type: application/json" \
  -d '{"title": "test"}'

# Should return 403 Forbidden: "CSRF token missing from cookie"

# 2. Try POST with valid session but no CSRF header (should fail)
curl -X POST https://your-backend.railway.app/rows \
  -H "Cookie: sa_session=<valid-session>" \
  -H "Content-Type: application/json" \
  -d '{"title": "test"}'

# Should return 403 Forbidden: "CSRF token missing from header"
```

---

## Priority 3: Secure Session Cookies (SECURITY-003)

**Risk Level**: MEDIUM (Session hijacking risk)
**Estimated Time**: 15 minutes
**File**: `apps/backend/routes/auth.py`

### Current Code:
```python
response.set_cookie(
    key="sa_session",
    value=token,
    httponly=True,
    secure=os.getenv("ENVIRONMENT") == "production",  # Only secure in prod
    samesite="lax",  # Too permissive
    max_age=30 * 24 * 60 * 60,
)
```

### Fixed Code:
```python
is_production = os.getenv("ENVIRONMENT") == "production"

response.set_cookie(
    key="sa_session",
    value=token,
    httponly=True,
    secure=is_production or bool(os.getenv("FORCE_SECURE_COOKIES")),  # ✓ Configurable
    samesite="strict" if is_production else "lax",  # ✓ Stricter in production
    max_age=30 * 24 * 60 * 60,
    domain=os.getenv("COOKIE_DOMAIN") if is_production else None,  # ✓ Explicit domain
    path="/",
)
```

### Environment Setup:
```bash
# Add to Railway production environment:
# COOKIE_DOMAIN=.your-domain.com  (with leading dot for subdomains)

# For local development with HTTPS (optional):
# FORCE_SECURE_COOKIES=true
```

### Testing:
```bash
# Test cookie attributes:
curl -i https://your-backend.railway.app/auth/verify \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"phone": "+1234567890", "code": "123456"}' \
  | grep -i set-cookie

# Should show:
# Set-Cookie: sa_session=...; HttpOnly; Secure; SameSite=Strict; Domain=.your-domain.com
```

---

## Verification Checklist

After deploying fixes, verify:

- [ ] CSP header does NOT contain `unsafe-inline` or `unsafe-eval`
- [ ] CSRF protection is active in all environments (dev, staging, prod)
- [ ] Session cookies have `Secure` flag in production
- [ ] Session cookies have `SameSite=Strict` in production
- [ ] CSRF_SECRET_KEY is set in Railway environment variables
- [ ] No errors in Railway logs after deployment
- [ ] Frontend still works (test login, create row, search)
- [ ] POST requests without CSRF token are rejected (403)

---

## Deployment Order

1. **Test locally first**:
   ```bash
   cd apps/backend
   # Add CSRF_SECRET_KEY to .env
   echo "CSRF_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(48))')" >> .env

   # Start backend
   ./start.sh

   # Test endpoints work with new security
   ```

2. **Deploy to staging/preview**:
   - Add `CSRF_SECRET_KEY` to Railway environment variables
   - Deploy changes
   - Run smoke tests

3. **Deploy to production**:
   - Verify staging is working
   - Deploy to production
   - Monitor logs for errors
   - Run full test suite

---

## Rollback Plan

If issues occur after deployment:

1. **Quick rollback**:
   ```bash
   git revert <commit-hash>
   git push
   ```

2. **Disable CSRF temporarily** (NOT RECOMMENDED):
   ```bash
   # In Railway dashboard, set:
   # CSRF_SECRET_KEY=  (empty)
   ```

3. **Monitor logs**:
   ```bash
   # Check Railway logs for errors
   # Look for CSRF rejection messages
   # Check for auth failures
   ```

---

## Additional Security Improvements (Not Urgent)

### Use Better Session Secret
```python
# Current: Uses token directly
session_token_hash=hash_token(token)

# Better: Use HMAC with secret
def hash_token_with_secret(token: str) -> str:
    secret = os.getenv("SESSION_SECRET_KEY", "")
    return hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()
```

### Add Rate Limiting to More Endpoints
```python
# Currently only on /auth/start
# Should add to:
# - /rows (create)
# - /search
# - /chat
```

### Add Security Headers to Frontend
```typescript
// In Next.js config:
async headers() {
  return [
    {
      source: '/:path*',
      headers: [
        { key: 'X-Frame-Options', value: 'DENY' },
        { key: 'X-Content-Type-Options', value: 'nosniff' },
        { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
      ],
    },
  ];
}
```

---

**Next Review**: After deployment, schedule security audit in 30 days to verify fixes are working and identify any new issues.

**Contact**: Security team should be notified of these critical findings and deployment timeline.
