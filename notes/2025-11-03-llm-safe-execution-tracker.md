# LLM-Safe Execution Tracker (Temporary)

Note: Temporary tracking doc. Delete after completion.

## A) North Star
- **Mission**: Enable safe, auditable AI-assisted development with human-in-the-loop, auto-provisioned PR preview envs, and gated promotion to production.
- **Primary outcome**: Every PR gets a preview environment on Railway (primary) or Cloud Run (optional), with logs/metrics visible and tests run; merges require all checks + reviewer approval.
- **Non-negotiables**:
  - No autonomous LLM writes/merges.
  - Immutable logs of AI activity and deployments.
  - Secrets in GCP Secret Manager or Railway env vars; no long-lived keys.
- **Scope now**:
  - Pulumi-first GCP modules.
  - Railway-first app runtime for PR previews; Cloud Run path remains as fallback.
  - GitHub Environments gate staging/production.

## B) PRD Addendum (Execution-Level)
- **CI/CD**
  - GitHub Actions with environments: `review` (PR previews), `staging`, `production`.
  - Required reviewers: ≥1 for staging, ≥2 for production.
  - Required checks: tests, infra plan/apply, verification script.
  - Auth: Prefer Workload Identity Federation (OIDC) over SA JSON keys.
- **Deploy targets**
  - Primary: Railway service per PR (branch-named).
  - Optional: Cloud Run per PR via Pulumi (GCP-native preview path).
- **Secrets**
  - Runtime app: Railway environment variables.
  - Backend/services: GCP Secret Manager.
  - CI: Short-lived OIDC tokens; no long-lived JSON keys.
- **Observability**
  - OTEL SDK in app; export to Grafana/Loki or GCP Monitoring/Logging.
  - Surface Railway logs; link in PR comments.
- **Policy engine**
  - Enforce provider targets (GCP/Railway), allowed paths, dependency pins, and environment gates.

## C) Plan & Task List
(IDs map to our working TODOs; mark these complete as we ship. Delete this section when finished.)

- [in_progress] task-01-decide-preview-target — Decide PR preview target: Railway-first vs Cloud Run vs toggle.
- [pending] task-02-pulumi-dependson-bug — Fix `infra/pulumi/index.js` to use resource objects in `dependsOn`.
- [pending] task-03-actions-bucket-order — Create GCS Pulumi state bucket before `pulumi login` in `.github/workflows/pr-env.yml`.
- [pending] task-04-ci-environment-gates — Add GitHub Environment gates (review/staging/prod) and required reviewers/checks.
- [pending] task-05-wif-auth — Replace SA JSON key auth with Workload Identity Federation.
- [pending] task-06-railway-workflow — Add Railway PR workflow and/or toggle to choose Railway vs Cloud Run per branch.
- [pending] task-07-ci-scripts-guards — Harden CI: run seed/test only if scripts exist; document health endpoint contract.
- [pending] task-08-docs-addendum — Add CI policy snippet, secrets matrix, observability defaults to docs.
- [pending] task-09-otel-guidance — Add OTEL starter guidance and exporter examples (Grafana/Loki or GCP).
- [pending] task-10-docs-prune-aws — Prune any remaining AWS/Vault references; align to GCP Secret Manager + Railway env vars.

## Links
- Source PRD: `/LLM_Safe_Framework_Internal_PRD.md`
- CI workflow: `/.github/workflows/pr-env.yml`
- Pulumi infra: `/infra/pulumi/`
- Railway templates: `/infra/railway/templates/`
