# Secrets Management Guide

This document outlines how to securely manage secrets and sensitive configuration for the Shopping Agent application.

## Table of Contents

1. [Overview](#overview)
2. [Environment Variables](#environment-variables)
3. [Secrets Rotation](#secrets-rotation)
4. [Development vs Production](#development-vs-production)
5. [Security Best Practices](#security-best-practices)
6. [Incident Response](#incident-response)

## Overview

The application uses environment variables for all configuration, including secrets. Secrets are **never** committed to version control.

### What is a Secret?

Secrets include:
- API keys and tokens
- Database credentials
- Session encryption keys
- OAuth client secrets
- Third-party service credentials
- CSRF tokens and signing keys

## Environment Variables

### Required Secrets

#### Database
```bash
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database
```

**Rotation Schedule**: Every 90 days or immediately if compromised

#### Authentication & Sessions
```bash
# CSRF Protection (required for production)
CSRF_SECRET_KEY=<random-64-char-string>
```

**Generation**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**Rotation Schedule**: Every 90 days

#### Email & SMS
```bash
RESEND_API_KEY=<resend-api-key>
TWILIO_ACCOUNT_SID=<twilio-account-sid>
TWILIO_AUTH_TOKEN=<twilio-auth-token>
TWILIO_PHONE_NUMBER=<twilio-phone>
```

**Rotation Schedule**: Every 180 days or immediately if compromised

#### Search & External APIs
```bash
SERPAPI_API_KEY=<serpapi-key>
OPENROUTER_API_KEY=<openrouter-key>
```

**Rotation Schedule**: Every 180 days

#### Storage (S3-compatible)
```bash
BUCKET_ENDPOINT_URL=<s3-endpoint>
BUCKET_NAME=<bucket-name>
BUCKET_ACCESS_KEY_ID=<access-key>
BUCKET_SECRET_ACCESS_KEY=<secret-key>
BUCKET_REGION=<region>
```

**Rotation Schedule**: Every 90 days

### Security Configuration

```bash
# Environment identifier
ENVIRONMENT=production

# SSL/TLS Configuration
DISABLE_SSL_VERIFICATION=false  # Should always be false in production

# Session expiration
SESSION_TTL_DAYS=7  # Session expiration in days

# Rate limiting (optional, defaults provided)
RATE_LIMIT_WINDOW=60  # seconds
LOCKOUT_DURATION=15   # minutes
```

## Secrets Rotation

### Rotation Process

1. **Generate New Secret**
   ```bash
   # For symmetric keys
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

2. **Update Environment Variables**
   - In Railway: Settings → Variables
   - In local: Update `.env` (gitignored)

3. **Deploy Changes**
   - Railway auto-deploys on variable changes
   - For local: Restart services

4. **Verify Functionality**
   - Test authentication
   - Check external API calls
   - Monitor error logs

5. **Revoke Old Secret**
   - Wait 24 hours for session migration
   - Revoke old API keys
   - Update documentation

### Emergency Rotation

If a secret is compromised:

1. **Immediate Actions** (within 1 hour)
   - Generate and deploy new secret
   - Revoke compromised secret
   - Force logout all sessions (if auth secret)
   - Review audit logs for suspicious activity

2. **Investigation** (within 24 hours)
   - Identify how secret was compromised
   - Review access logs
   - Check for unauthorized access
   - Document incident

3. **Prevention** (within 1 week)
   - Update security procedures
   - Implement additional monitoring
   - Train team if needed

## Development vs Production

### Development

- Use `.env.example` as template
- Create local `.env` (gitignored)
- Use test/sandbox API keys when available
- CSRF protection disabled by default

```bash
ENVIRONMENT=development
CSRF_SECRET_KEY=dev-only-not-for-production
DEV_BYPASS_CODE=123456  # For testing auth flow
```

### Production

- All secrets in Railway environment variables
- SSL verification enabled
- CSRF protection required
- Strong session secrets
- Production API keys only

```bash
ENVIRONMENT=production
CSRF_SECRET_KEY=<strong-random-secret>
# DEV_BYPASS_CODE not set
DISABLE_SSL_VERIFICATION=false
```

## Security Best Practices

### DO ✅

- Use environment variables for all secrets
- Generate cryptographically secure random values
- Rotate secrets on schedule
- Use different secrets per environment
- Audit secret access regularly
- Monitor for secret exposure (GitHub, logs)
- Use principle of least privilege

### DON'T ❌

- Commit secrets to version control
- Share secrets in chat/email
- Reuse secrets across environments
- Log secrets (even redacted)
- Store secrets in code comments
- Use weak or predictable secrets
- Disable SSL verification in production

### Generating Strong Secrets

```python
# Python
import secrets

# For API keys (32 bytes = 43 chars base64)
secrets.token_urlsafe(32)

# For CSRF tokens (48 bytes = 64 chars base64)
secrets.token_urlsafe(48)

# For verification codes (6 digits)
f"{secrets.randbelow(1000000):06d}"
```

```bash
# Bash
openssl rand -base64 32  # For keys
openssl rand -hex 32     # For hex tokens
```

## Incident Response

### Signs of Compromise

- Unusual API usage patterns
- Failed authentication attempts
- Unauthorized database access
- API rate limit violations
- Unexpected external requests

### Response Steps

1. **Contain**: Rotate compromised secrets immediately
2. **Investigate**: Review logs and access patterns
3. **Remediate**: Fix vulnerability, update procedures
4. **Document**: Write incident report
5. **Notify**: Inform affected users if necessary

### Contact Information

- Security Lead: [Your security contact]
- On-Call: [Your on-call rotation]
- Incident Email: [Your security email]

## Monitoring

### Automated Checks

- Secret scanner in CI/CD (prevent commits)
- Log analysis for exposed secrets
- API usage anomaly detection
- Failed authentication tracking

### Manual Audits

- **Weekly**: Review authentication logs
- **Monthly**: Audit secret access
- **Quarterly**: Full security review
- **Annually**: Penetration testing

## Compliance

### Data Protection

- Secrets are considered sensitive data
- Subject to encryption at rest
- Transmitted over TLS only
- Access logged and audited

### Retention

- Revoked secrets deleted after 30 days
- Audit logs retained for 1 year
- Incident reports retained indefinitely

## Tools

### Secret Generation

- `secrets` module (Python)
- `openssl` command-line tool
- 1Password generator
- LastPass generator

### Secret Storage

- **Production**: Railway environment variables
- **Development**: `.env` file (gitignored)
- **Team**: 1Password/LastPass (never in code)

### Monitoring

- GitHub secret scanning
- Sentry error tracking
- Custom audit log analysis

## Appendix

### Example .env Template

```bash
# Database
DATABASE_URL=postgresql+asyncpg://localhost:5435/shopping_agent

# Security
CSRF_SECRET_KEY=change-me-in-production
ENVIRONMENT=development

# Authentication
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
RESEND_API_KEY=

# Search APIs
SERPAPI_API_KEY=
OPENROUTER_API_KEY=

# Storage
STORAGE_PROVIDER=disk  # or 'bucket'
UPLOAD_DIR=./uploads

# Development
DEV_BYPASS_CODE=123456
DISABLE_SSL_VERIFICATION=false
```

### Checklist for New Secrets

- [ ] Generated using cryptographically secure method
- [ ] Added to Railway environment variables (production)
- [ ] Added to `.env.example` (template only, no real values)
- [ ] Documented in this guide
- [ ] Rotation schedule defined
- [ ] Access logged and monitored
- [ ] Team members notified if needed

---

**Last Updated**: 2025-01-XX
**Next Review**: Quarterly
