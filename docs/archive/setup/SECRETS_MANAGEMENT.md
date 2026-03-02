# Secrets Management Guide

Protect credentials from source control and accidental leakage. This guide shows
you how to manage secrets locally, in CI, and in production.

---

## 1. Local Development

Use `.env` files for local overrides:

```bash
cp env.example .env
```

- `.env` — shared local development defaults
- `.env.local` — developer-specific overrides (ignored by git)
- `.env.test` — values used by automated tests

Never commit these files. The `.gitignore` already protects them.

### Optional: direnv

Install [direnv](https://direnv.net/) to load `.env` automatically:

```bash
brew install direnv
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc
```

Create `.envrc` that sources `.env` securely.

---

## 2. GitHub Actions Secrets

Navigate to **Repository Settings → Secrets and variables → Actions** and add
entries such as:

- `GCP_PROJECT_ID`
- `GCP_SA_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `SENDGRID_API_KEY`

Access them in workflows via `${{ secrets.NAME }}`.

---

## 3. Google Cloud Secret Manager

For production deployments on GCP:

```bash
gcloud secrets create app-config --replication-policy=automatic
printf "DATABASE_URL=%s" "$DATABASE_URL" | \
  gcloud secrets versions add app-config --data-file=-
```

Grant the Cloud Run service account access:

```bash
gcloud secrets add-iam-policy-binding app-config \
  --member="serviceAccount:sa-cloud-run@<PROJECT_ID>.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

Mount secrets in Cloud Run by referencing them in `infra/pulumi/index.js` or
through the Cloud Console.

---

## 4. Environment Promotion Checklist

| Stage         | Storage            | Rotation Policy          |
|---------------|--------------------|--------------------------|
| Development   | `.env`, direnv     | Regenerate when compromised |
| CI / Preview  | GitHub Secrets     | Rotate every 90 days        |
| Production    | Secret Manager     | Rotate 60–90 days, automate |

Document rotations in `.cfoi/branches/<branch>/DECISIONS.md` or a dedicated
runbook.

---

## 5. Detecting Leaks

- Enable secret scanning alerts in GitHub.
- Configure the `pre-commit` hook to flag accidental `.env` commits (already
  handled via ignore files and manual checks).
- Use tools like [trufflehog](https://github.com/trufflesecurity/trufflehog) for periodic audits.

---

## 6. Cleanup

When rotating credentials:

1. Create a new secret.
2. Update all consumers (local `.env`, GitHub secrets, Cloud Run config).
3. Invalidate the old secret.
4. Record the change in `DECISIONS.md` so the team stays informed.

Following this cycle keeps audit trails clean and prevents long-lived keys from lingering.

