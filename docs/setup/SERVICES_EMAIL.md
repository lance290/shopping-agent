# Email Provider Setup

Choose one transactional email provider and capture its credentials in `.env`.
The table below compares the options referenced in this repository.

| Provider   | Getting Started                                    | Notes                               |
|------------|----------------------------------------------------|-------------------------------------|
| SendGrid   | <https://app.sendgrid.com/>                        | Free tier, great docs, API first    |
| Mailgun    | <https://app.mailgun.com/>                         | Excellent deliverability, EU zones  |
| AWS SES    | <https://console.aws.amazon.com/ses/>              | Cheapest at scale, requires AWS IAM |
| Resend     | <https://resend.com/>                              | Modern API, great TypeScript SDK    |

---

## 1. SendGrid (Example)

1. Sign up and authenticate a sender domain or single sender.
2. Navigate to **Settings → API Keys** → Create **Full Access** key.
3. Set `.env`:

```bash
SENDGRID_API_KEY=SG.xxxxx
SENDGRID_FROM_EMAIL=noreply@yourdomain.com
SENDGRID_FROM_NAME=Your App
```

Install the SDK:

```bash
npm install @sendgrid/mail
```

---

## 2. Mailgun

1. Create a domain (EU or US region).
2. Verify DNS records (SPF, DKIM).
3. Generate an API key and capture the sending domain.
4. `.env`:

```bash
MAILGUN_API_KEY=key-xxxx
MAILGUN_DOMAIN=mg.yourdomain.com
MAILGUN_FROM=noreply@yourdomain.com
```

Install:

```bash
npm install mailgun.js form-data
```

---

## 3. AWS SES

1. Verify domain or email in SES.
2. Create an IAM user with `AmazonSESFullAccess`.
3. Generate access keys and store them securely.
4. `.env`:

```bash
AWS_SES_REGION=us-east-1
AWS_SES_ACCESS_KEY_ID=AKIA...
AWS_SES_SECRET_ACCESS_KEY=...
AWS_SES_FROM_EMAIL=noreply@yourdomain.com
```

Install:

```bash
npm install @aws-sdk/client-ses
```

---

## 4. Resend

1. Sign up at <https://resend.com/>.
2. Verify your domain (TXT + DKIM records).
3. Create an API key.
4. `.env`:

```bash
RESEND_API_KEY=re_xxxxx
RESEND_FROM_EMAIL=noreply@yourdomain.com
```

Install:

```bash
npm install resend
```

---

## Testing & Verification

- Use providers’ sandbox/test modes for automated tests.
- Capture manual verification steps in `.cfoi/branches/<branch>/proof/.../manual.md`.
- Add integration tests for the most critical notification flows (`/implement` Step 5).

Finally, store API keys in your secret manager (`SECRETS_MANAGEMENT.md`) and add
CI secrets if needed (e.g., `SENDGRID_API_KEY`). Avoid hardcoding secrets in code
or committing `.env` files — the git hooks enforce this policy.

