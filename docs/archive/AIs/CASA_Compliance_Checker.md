# AI System Instructions for CASA Compliance Checking

## Purpose

These instructions guide AI systems in reviewing code changes to ensure compliance with CASA (Comprehensive Application Security Assessment) requirements after coding sessions. The AI must systematically check for violations across all 70 CASA requirements and flag potential compliance issues.

## Pre-Check Setup

Before reviewing code, the AI must:

1. Load the complete CASA compliance requirements (70 items)
2. Understand the CWE (Common Weakness Enumeration) mappings
3. Identify which code modules map to which CASA sections
4. Prepare to check against all applicable requirements

## CASA Compliance Categories

### 1. Architecture, Design and Threat Modeling (Requirements 1.x)

**Critical Checks:**

- ❌ **1.1.4**: Missing documentation of trust boundaries, components, and data flows
- ❌ **1.14.6**: Use of deprecated technologies (Flash, ActiveX, Silverlight, NACL, Java applets)
- ❌ **1.4.1**: Client-side access control enforcement instead of server-side
- ❌ **1.8.1**: Unclassified or unidentified sensitive data
- ❌ **1.8.2**: Missing protection requirements for data classification levels

### 2. Authentication (Requirements 2.x)

**Critical Checks:**

- ❌ **2.1.1**: Passwords less than 12 characters
- ❌ **2.3.1**: Weak initial passwords or activation codes
- ❌ **2.4.1**: Passwords not properly salted and hashed
- ❌ **2.5.4**: Presence of default accounts (root, admin, sa)
- ❌ **2.6.1**: Reusable lookup secrets
- ❌ **2.7.2**: Out-of-band authentication tokens not expiring after 10 minutes
- ❌ **2.7.6**: Weak entropy in authentication codes (<20 bits)

### 3. Session Management (Requirements 3.x)

**Critical Checks:**

- ❌ **3.3.1**: Session tokens not invalidated on logout/expiration
- ❌ **3.3.3**: No option to terminate other sessions after password change
- ❌ **3.4.1**: Missing 'Secure' attribute on session cookies
- ❌ **3.4.2**: Missing 'HttpOnly' attribute on session cookies
- ❌ **3.4.3**: Missing 'SameSite' attribute for CSRF protection
- ❌ **3.5.2**: Use of static API keys instead of session tokens
- ❌ **3.5.3**: Unprotected stateless tokens (missing signatures/encryption)
- ❌ **3.7.1**: Sensitive operations without re-authentication

### 4. Access Control (Requirements 4.x)

**Critical Checks:**

- ❌ **4.1.1**: Client-side access control that can be bypassed
- ❌ **4.1.2**: User-manipulable access control attributes
- ❌ **4.1.3**: Violation of least privilege principle
- ❌ **4.1.5**: Access controls that don't fail securely
- ❌ **4.2.1**: IDOR vulnerabilities in CRUD operations
- ❌ **4.2.2**: Missing CSRF protection
- ❌ **4.3.1**: Admin interfaces without MFA
- ❌ **4.3.2**: Directory browsing enabled or metadata exposure (.git, .DS_Store)

### 5. Validation, Sanitization and Encoding (Requirements 5.x)

**Critical Checks:**

- ❌ **5.1.1**: No defense against HTTP parameter pollution
- ❌ **5.1.5**: Unvalidated URL redirects
- ❌ **5.2.3**: Unprotected SMTP/IMAP injection
- ❌ **5.2.4**: Use of eval() or dynamic code execution
- ❌ **5.2.5**: Template injection vulnerabilities
- ❌ **5.2.6**: SSRF vulnerabilities
- ❌ **5.2.7**: Unsanitized SVG content
- ❌ **5.3.1**: Incorrect output encoding for context
- ❌ **5.3.3**: Missing XSS protection
- ❌ **5.3.4**: SQL injection vulnerabilities
- ❌ **5.3.6**: JSON injection vulnerabilities
- ❌ **5.3.7**: LDAP injection vulnerabilities
- ❌ **5.3.8**: OS command injection
- ❌ **5.3.9**: LFI/RFI vulnerabilities
- ❌ **5.3.10**: XPath/XML injection
- ❌ **5.5.2**: XXE vulnerabilities in XML parsers

### 6. Stored Cryptography (Requirements 6.x)

**Critical Checks:**

- ❌ **6.1.1**: Unencrypted PII or regulated data at rest
- ❌ **6.2.1**: Padding Oracle vulnerabilities
- ❌ **6.2.3**: Insecure cipher configurations or IVs
- ❌ **6.2.4**: Non-upgradeable cryptographic algorithms
- ❌ **6.2.7**: Unauthenticated encrypted data
- ❌ **6.2.8**: Timing attacks in cryptographic operations
- ❌ **6.3.2**: Predictable GUIDs (not using v4 + CSPRNG)
- ❌ **6.4.2**: Key material exposed to application

### 7. Error Handling and Logging (Requirements 7.x)

**Critical Checks:**

- ❌ **7.1.1**: Logging credentials, payment details, or unhashed session tokens

### 8. Data Protection (Requirements 8.x)

**Critical Checks:**

- ❌ **8.1.1**: Sensitive data cached in load balancers/caches
- ❌ **8.2.2**: Sensitive data in browser storage
- ❌ **8.3.1**: Sensitive data in URL parameters
- ❌ **8.3.5**: Missing audit trails for sensitive data access

### 9. Malicious Code (Requirements 10.x)

**Critical Checks:**

- ❌ **10.3.2**: Loading code from untrusted sources
- ❌ **10.3.3**: Subdomain takeover vulnerabilities

### 10. Business Logic (Requirements 11.x)

**Critical Checks:**

- ❌ **11.1.4**: Missing anti-automation controls

### 11. Files and Resources (Requirements 12.x)

**Critical Checks:**

- ❌ **12.4.1**: Untrusted files stored in web root
- ❌ **12.4.2**: Missing antivirus scanning for uploads

### 12. API and Web Service (Requirements 13.x)

**Critical Checks:**

- ❌ **13.1.3**: API keys/tokens exposed in URLs
- ❌ **13.1.4**: Missing authorization at URI and resource levels
- ❌ **13.2.1**: Inappropriate HTTP methods enabled (DELETE/PUT)

### 13. Configuration (Requirements 14.x)

**Critical Checks:**

- ❌ **14.1.1**: Insecure build/deployment processes
- ❌ **14.1.4**: Non-automated deployment/recovery
- ❌ **14.1.5**: Unverifiable configuration integrity
- ❌ **14.3.2**: Debug mode enabled in production
- ❌ **14.5.2**: Origin header used for access control

## Compliance Check Output Format

```markdown
## CASA Compliance Review Report

Date: [Current Date]
Reviewer: [AI System Name]
Code Review Scope: [Files/Modules Reviewed]

### Compliance Status: [PASS/FAIL/CONDITIONAL]

### Critical Violations Found: [Count]

[For each violation, provide:]

- **CASA Requirement**: [ID] - [Description]
- **CWE**: [CWE Number]
- **Location**: [File:Line]
- **Issue**: [Specific violation description]
- **Risk**: [HIGH/MEDIUM/LOW]
- **Fix**: [Specific remediation steps]

### Warning-Level Issues: [Count]

[Same format as above]

### Compliance Summary by Category:

- [ ] Architecture & Design (1.x): [Status]
- [ ] Authentication (2.x): [Status]
- [ ] Session Management (3.x): [Status]
- [ ] Access Control (4.x): [Status]
- [ ] Input/Output Security (5.x): [Status]
- [ ] Cryptography (6.x): [Status]
- [ ] Logging (7.x): [Status]
- [ ] Data Protection (8.x): [Status]
- [ ] Malicious Code (10.x): [Status]
- [ ] Business Logic (11.x): [Status]
- [ ] File Handling (12.x): [Status]
- [ ] API Security (13.x): [Status]
- [ ] Configuration (14.x): [Status]

### Recommended Actions:

1. [Prioritized list of remediation steps]
2. [Include specific code examples where helpful]
```

## AI Behavioral Instructions

### Scanning Strategy

1. **Map Code to Requirements**: Identify which CASA requirements apply to each code component
2. **Risk-Based Priority**: Check high-risk areas first (authentication, crypto, access control)
3. **Context Awareness**: Understand if code is for production vs. development
4. **Pattern Recognition**: Look for common anti-patterns that violate CASA

### Detection Rules

- **Direct Violations**: Code that explicitly violates a requirement
- **Missing Controls**: Absence of required security controls
- **Weak Implementations**: Controls present but insufficient
- **Configuration Issues**: Insecure settings or defaults

### Severity Classification

- **CRITICAL**: Violations of authentication, crypto, or access control requirements
- **HIGH**: Input validation, session management, or data protection issues
- **MEDIUM**: Configuration or logging issues
- **LOW**: Best practice violations without immediate security impact

## Automated Checks

### Code Pattern Detection

```python
# Example patterns to detect:
VIOLATIONS = {
    "2.1.1": r"password.*length.*<\s*12",
    "2.5.4": r"(username|user).*=.*(admin|root|sa)",
    "3.4.1": r"cookie.*(?!.*secure)",
    "5.3.4": r"query.*\+.*user_input|f-string.*SELECT",
    "6.1.1": r"(pii|ssn|credit_card).*(?!.*encrypt)",
    # Add more patterns...
}
```

### Integration Points

1. **Pre-commit Hook**: Block commits with critical violations
2. **CI/CD Pipeline**: Run full compliance check on merge requests
3. **IDE Integration**: Real-time compliance hints while coding
4. **Reporting**: Generate compliance reports for audit trails

## Continuous Improvement

- Track false positive/negative rates
- Update detection patterns based on new vulnerabilities
- Maintain mapping between code changes and CASA requirements
- Regular updates when CASA framework changes

---

**Note**: This framework is based on CASA requirements similar to OWASP ASVS. Each requirement includes a CWE mapping for additional context on the vulnerability class.
