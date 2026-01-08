---
allowed-tools: "*"
description: Map compliance requirements to technical controls and enforcement mechanisms
---
allowed-tools: "*"

# Security & Compliance Workflow

Use this workflow to translate regulatory requirements into concrete technical controls, documentation, and monitoring. This workflow is auto-triggered by `/bootup` when compliance requirements are detected.

---
allowed-tools: "*"

## Step 0: Load Compliance Context
// turbo
1. Load bootstrap answers from `.cfoi/branches/<branch>/bootstrap.json`
2. Parse compliance requirements (SOC 2, HIPAA, PCI DSS, CASA, FedRAMP, ISO 27001, GDPR)
3. Parse payment processors (Stripe, Braintree, PayPal, Square, Adyen)
4. Parse email/calendar access levels
5. Display: "🔒 Processing compliance requirements: [list detected requirements]"

---
allowed-tools: "*"

## Step 1: Compliance Deep Dive
For each detected requirement, ask targeted questions:

### 1A. SOC 2 (Type I/II)
- **Scope**: Which systems are in scope? (all production, specific services, data processing)
- **Trust Services**: Security, Availability, Processing Integrity, Confidentiality, Privacy?
- **Review Period**: How often for Type II reviews? (quarterly, semi-annual)
- **Evidence Requirements**: Screenshots, logs, configuration exports?

### 1B. HIPAA (Healthcare)
- **PHI Types**: What protected health information? (diagnoses, treatment, payment)
- **Covered Entities**: Are you a covered entity or business associate?
- **BAA Requirements**: Need Business Associate Agreements with vendors?
- **Data Minimization**: Must collect minimum necessary PHI?

### 1C. PCI DSS (Payments)
- **Card Data**: Will you store, process, or transmit cardholder data?
- **Scope Reduction**: Can you use tokenization to reduce scope?
- **Network Segmentation**: Separate card data environment?
- **Security Standards**: Required security scanning, penetration testing?

### 1D. CASA (Cybersecurity)
- **Tier Level**: Which CASA tier? (Tier 1-4, determines requirements)
- **System Classification**: Impact level of system? (Low, Moderate, High)
- **Continuous Monitoring**: Real-time security monitoring required?
- **Incident Response**: Required response time for security incidents?

### 1E. FedRAMP (Government)
- **Authorization Level**: Low, Moderate, or High impact?
- **Cloud Provider**: Using FedRAMP authorized cloud? (GCP GovCloud, AWS GovCloud)
- **Data Classification**: FISMA impact level?
- **Continuous Monitoring**: 30-day or 90-day assessment cycles?

### 1F. GDPR (EU Data)
- **Data Subjects**: What personal data collected? (name, email, location, behavior)
- **Legal Basis**: Consent, contract, legal obligation?
- **Data Processing**: Automated decision making, profiling?
- **Cross-Border**: Transfer outside EU? Standard Contractual Clauses needed?

---
allowed-tools: "*"

## Step 2: Technical Control Mapping
// turbo
Map each requirement to specific technical controls:

### 2A. Data Protection Controls
**For HIPAA/GDPR/PHI:**
- Encryption at rest (AES-256) and in transit (TLS 1.2+)
- Data masking for development environments
- Access logging for all PHI access
- Data retention and deletion policies
- Right to erasure (GDPR) mechanisms

**For PCI DSS:**
- Tokenization integration (Stripe recommended)
- No card data storage in application databases
- Secure key management
- Network segmentation documentation
- Quarterly vulnerability scanning

### 2B. Access Control Controls
**For SOC 2/CASA/FedRAMP:**
- RBAC implementation with least privilege
- MFA enforcement for admin accounts
- Session timeout configuration
- Password complexity requirements
- Account lockout policies

### 2C. Audit & Logging Controls
**For all compliance frameworks:**
- Immutable audit logs (write-once storage)
- Log retention periods (1-7 years depending on regulation)
- Change management logging
- Admin action logging
- Failed authentication tracking

### 2D. Infrastructure Controls
**For FedRAMP/CASA:**
- Cloud provider compliance documentation
- Network security groups/firewall rules
- Backup and disaster recovery procedures
- Incident response playbooks
- Security monitoring configuration

### 2E. ML/AI-Specific Security Controls
**For ML/AI workloads (if detected in bootstrap):**

**Model Security:**
- Model poisoning prevention (training data validation)
- Adversarial input detection (input sanitization)
- Model extraction protection (rate limiting, watermarking)
- Prompt injection defenses (for LLMs - input filtering, output validation)
- Model versioning and audit trails (who deployed what model when)

**Data Privacy in ML:**
- Training data anonymization (PII removal, differential privacy)
- PII detection in prompts and outputs (real-time scanning)
- Data retention policies for model training (GDPR compliance)
- Right-to-explanation (model explainability for GDPR/HIPAA)
- Federated learning for sensitive data (healthcare, finance)

**Inference Security:**
- Rate limiting for expensive GPU calls (cost control, DoS prevention)
- Input validation and sanitization (prevent injection attacks)
- Output filtering (toxicity detection, bias mitigation, PII redaction)
- API key management for model access (rotation, scoping)
- Request/response logging with PII masking

**ML Compliance:**
- Model audit trails (inference logs, model versions, user attribution)
- Bias and fairness testing (demographic parity, equal opportunity)
- Explainability requirements (SHAP, LIME for GDPR/HIPAA)
- Model versioning for regulatory compliance (FDA, financial regulations)
- A/B testing documentation (consent, data usage)

**Vector Database Security:**
- Embedding access control (who can query which embeddings)
- Semantic search audit logging (track sensitive queries)
- Data isolation in multi-tenant vector stores
- Encryption at rest for embeddings

---
allowed-tools: "*"

## Step 3: Generate Compliance Artifacts
// turbo
Create compliance-specific files and configurations:

### 3A. Documentation Files
Create in `docs/compliance/`:
- `compliance-matrix.md` - Requirements vs controls mapping
- `security-policies.md` - Access control, data handling policies
- `incident-response.md` - Security incident procedures
- `vendor-management.md` - Third-party risk assessments
- `data-classification.md` - Data sensitivity classification guide

### 3B. Configuration Files
- `.env.compliance` - Compliance-specific environment variables
- `infra/security/` - Security-focused infrastructure templates
- `scripts/compliance-checks.sh` - Automated compliance validation
- `monitoring/security-alerts.yml` - Security monitoring rules

### 3C. Code Templates
- Authentication middleware with audit logging
- Data encryption/decryption utilities
- Access control decorators/functions
- Privacy consent management (GDPR)
- Data anonymization for development

---
allowed-tools: "*"

## Step 4: Integration Points
// turbo
Wire compliance into existing workflows:

### 4A. Git Hooks Integration
Update pre-commit hooks to check:
- No hardcoded secrets or API keys
- Proper data handling in new code
- Security headers in web responses
- Encryption for sensitive data storage

### 4B. CI/CD Integration
Add to deployment pipeline:
- Security scanning (Snyk, Semgrep)
- Dependency vulnerability checks
- Infrastructure as code security validation
- Automated compliance checks

### 4C. Monitoring Integration
Set up alerts for:
- Failed authentication spikes
- Unauthorized data access attempts
- Configuration changes to security settings
- Data export/access anomalies

---
allowed-tools: "*"

## Step 5: Validation Checklist
// turbo
Create compliance validation checklist:

### 5A. Pre-Deployment Checklist
- [ ] All sensitive data encrypted at rest
- [ ] TLS 1.2+ enforced for all connections
- [ ] RBAC implemented and tested
- [ ] Audit logging enabled and functioning
- [ ] MFA required for admin access
- [ ] Security scanning passes
- [ ] Data retention policies configured
- [ ] Incident response procedures documented

### 5B. Ongoing Compliance Checklist
- [ ] Quarterly access reviews completed
- [ ] Security patches applied within SLA
- [ ] Backup and recovery tested
- [ ] Penetration testing completed (PCI DSS)
- [ ] Vulnerability scanning results reviewed
- [ ] Compliance training completed by team
- [ ] Third-party vendor assessments updated

---
allowed-tools: "*"

## Step 6: Human Review & Sign-off
// turbo
1. Present generated compliance artifacts for review
2. Verify all requirements have corresponding controls
3. Confirm integration points are properly configured
4. Obtain explicit approval: "✅ Compliance requirements mapped and controls implemented"

---
allowed-tools: "*"

## Specialized Templates

### Payment Processing (PCI DSS)
```javascript
// Stripe integration (recommended for PCI DSS)
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);

// Never store card data - use tokens
async function createPaymentToken(cardDetails) {
  return await stripe.tokens.create({ card: cardDetails });
}

// Process payment without touching card data
async function processPayment(token, amount) {
  const payment = await stripe.charges.create({
    amount: amount,
    currency: 'usd',
    source: token.id,
    description: 'Payment for order'
  });
  return payment;
}
```

### Email Access (OAuth/IMAP)
```javascript
// OAuth-based email access (no password storage)
const { google } = require('googleapis');

async function getGmailClient() {
  const auth = new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET,
    process.env.GOOGLE_REDIRECT_URI
  );
  
  // Use stored refresh token, never store passwords
  auth.setCredentials({ refresh_token: user.refreshToken });
  return google.gmail({ version: 'v1', auth });
}
```

### Data Encryption (HIPAA/GDPR)
```javascript
// AES-256 encryption for sensitive data
const crypto = require('crypto');

function encryptSensitiveData(data, encryptionKey) {
  const iv = crypto.randomBytes(16);
  const cipher = crypto.createCipher('aes-256-cbc', encryptionKey);
  let encrypted = cipher.update(data, 'utf8', 'hex');
  encrypted += cipher.final('hex');
  return { encrypted, iv: iv.toString('hex') };
}
```

---
allowed-tools: "*"

## Post-Implementation

1. Update `.windsurf/constitution.md` with compliance-specific rules
2. Add compliance checks to pre-push hooks
3. Schedule periodic compliance reviews
4. Document any deviations or compensating controls

---
allowed-tools: "*"

**Note**: This workflow creates the foundation for compliance. Actual certification requires external auditors and ongoing maintenance. Consult legal/compliance teams for specific regulatory guidance.
