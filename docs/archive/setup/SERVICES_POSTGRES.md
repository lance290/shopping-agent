# PostgreSQL / Cloud SQL Setup

PostgreSQL is the default relational database assumed by the framework. Follow
these steps to provision an instance and connect it to your application and
ephemeral environments.

---

## 1. Provision the Database

### Option A: Google Cloud SQL (recommended for Cloud Run)

1. Open <https://console.cloud.google.com/sql>.
2. Create Instance → **PostgreSQL**.
3. Choose the smallest production tier (e.g., `db-g1-small`) to start.
4. Enable **Public IP** for quick start. Restrict to your IPs once stable.
5. Set an admin password and record it securely.

### Option B: Hosted PostgreSQL Providers

Services such as **Neon**, **Supabase**, **Railway**, or **Render** provide one
click PostgreSQL clusters with generous free tiers. Grab the connection string
from their dashboard.

---

## 2. Create an Application Database & User

```bash
psql "host=<HOST> port=5432 user=postgres password=<ADMIN_PASSWORD>" <<'SQL'
CREATE DATABASE mvp_app;
CREATE USER mvp_user WITH PASSWORD 'change-me-now';
GRANT ALL PRIVILEGES ON DATABASE mvp_app TO mvp_user;
SQL
```

If you are using Cloud SQL, connect via the Cloud SQL Proxy or the web console's
`psql` tool.

---

## 3. Configure Environment Variables

Update `.env` (and CI secrets if needed):

```bash
DATABASE_URL=postgresql://mvp_user:change-me-now@<HOST>:5432/mvp_app

# For tests (optional)
TEST_DATABASE_URL=postgresql://mvp_user:change-me-now@<HOST>:5432/mvp_app_test
```

For Cloud SQL, the host often looks like `/cloudsql/<PROJECT_ID>:<REGION>:<INSTANCE>`
when accessed from Cloud Run or via the proxy.

---

## 4. Local Migrations

Install a migration tool (Prisma, Knex, Drizzle, etc.) and run:

```bash
npm run db:migrate    # or the equivalent for your stack
```

Document the command in your README to keep onboarding friction low.

---

## 5. Pulumi Integration (Optional)

If you want Pulumi to manage Cloud SQL:

1. Add `@pulumi/gcp` resources for `sql.DatabaseInstance`, `sql.Database`, and
   `sql.User` in `infra/pulumi/index.js`.
2. Output connection information with `pulumi export`.
3. Store secrets using Pulumi config (`pulumi config set --secret` …).

This can be added later — start manually, automate once requirements stabilize.

---

## 6. Security Hardening Checklist

- [ ] Rotate credentials into Secret Manager.
- [ ] Restrict inbound IP addresses or use Cloud SQL Auth Proxy.
- [ ] Enable automated backups.
- [ ] Set up monitoring & alerting (Cloud SQL → Monitoring tab).

Keep this checklist in `.cfoi/branches/<branch>/DECISIONS.md` once completed to
signal maturity of the data layer.

