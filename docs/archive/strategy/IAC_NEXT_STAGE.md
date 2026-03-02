# IaC Next-Stage Integration Plan

_Date: 2025-11-01_

This document folds in the genuinely useful material from the previously delivered strategy pack while discarding or parking the rest. It aligns with our focus on **GCP + Railway**, **Pulumi**, and **Docker-first** development for intern-friendly deployments.

---

## 1. Messaging & Stakeholder Framing (Adopted)

- Reuse the concise stakeholder narrative from `EXECUTIVE_SUMMARY.md` to communicate:
  - Goal: interns ship production-ready MVPs in < 2 weeks.
  - Hybrid architecture: Railway for app hosting, GCP for managed services.
  - Cost guardrails: target $35–$75/mo per project, <$200 in production.
- Action: Extract key paragraphs into upcoming stakeholder brief deck; keep the rest archived.

---

## 2. Implementation Timeline (Refined)

The 6-week roadmap is retained but condensed into clear, testable milestones:

1. **Week 1 – Docker Foundations**
   - Validate and adapt the Node.js multi-stage Dockerfile (`infra/docker/templates/nodejs/`).
   - Produce equivalent templates for Python, Go, and Java (keep scope lean: one template per language + README).
   - Deliver a shared `docker-compose` example covering app + Postgres + Redis.

2. **Week 2 – Railway Enablement**
   - Author real Railway config/templates and CLI helper scripts (missing in original pack).
   - Draft `/deploy-railway` workflow and hands-on tutorial.
   - Smoke-test with sample app deployment.

3. **Week 3 – Pulumi Modularization**
   - Use the suggested module breakdown (cloud-run, cloud-sql, storage, secrets) as a blueprint.
   - Implement modules incrementally; ensure unit tests or integration checks accompany each.
   - Update Pulumi stacks to separate shared infra vs. per-environment artifacts.

4. **Week 4 – Hybrid Connectivity**
   - Wire Railway services to GCP databases/storage securely (service accounts, signed URLs, proxies).
   - Provide scripts for syncing secrets between GCP Secret Manager and Railway env vars.

5. **Week 5 – Observability & Reliability**
   - Stand up logging/monitoring dashboards in GCP (structured logging, alerting).
   - Package optional Sentry integration starter.

6. **Week 6 – Enablement Assets**
   - Replace verbose prose with concise guides, checklists, and a short Loom/video walkthrough series.
   - Publish troubleshooting playbooks focused on Docker, Railway, and Pulumi basics.

Each milestone should exit with a demo and documentation stub committed to the repo.

---

## 3. Technical Assets to Incorporate (Adopted/Adjusted)

| Asset | Status | Next Action |
|-------|--------|-------------|
| `infra/docker/templates/nodejs/` | Usable baseline | Review for best practices (non-root, health checks already present); replicate structure for other languages. |
| Pulumi module breakdown (`IAC_STRATEGY.md`) | Conceptual only | Implement real modules in `infra/pulumi/modules/` with tests; update main stack to consume them. |
| Week-by-week checklists (`IMPLEMENTATION_PLAN.md`) | Useful structure | Translate into task tracker tickets; discard redundant verbiage. |
| Stakeholder cost table | Messaging value | Verify figures with actual projections before sharing externally. |

---

## 4. Items Discarded or Deferred

- **Inflated Word Count:** Long-form narrative sections without concrete output are archived, not maintained.
- **Unimplemented Railway scripts/templates:** Replace with our own practical tooling deliverables.
- **Speculative cost estimates:** Only reuse after validation with GCP/Railway pricing calculators.
- **Observability/security bullet lists:** Rebuild as actionable runbooks with code/config examples during Week 5.

---

## 5. Immediate TODOs

1. ✅ Document integrated plan (this file).
2. 🔄 Create tickets for Week 1 tasks (Docker templates, compose file, README updates).
3. 🔄 Schedule review of Node.js Docker template with DevOps lead before replicating.
4. 🔄 Prepare stakeholder brief slide using extracted messaging snippets.

---

## 6. References

- `docs/strategy/EXECUTIVE_SUMMARY.md` – Keep for stakeholder-facing excerpts.
- `docs/strategy/IMPLEMENTATION_PLAN.md` – Source for timeline granularity, but consult this plan for scope control.
- `docs/strategy/IAC_STRATEGY.md` – Use the module breakdown table only; ignore aspirational sections until implemented.
- `infra/docker/templates/nodejs/` – Primary reusable asset today.
