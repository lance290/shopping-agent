# PRD Traceability Matrix

Updated: 2026-02-28
Build Scope Source: `docs/PRD/`
Output Folder: `docs/PRD/bob-shopping-agent/`
Parent Sources:
- `docs/PRD/prd (4).md`
- `docs/PRD/need sourcing_ Bob@buy-anything.com.md`

## Child PRD Mapping

| Child PRD name | Priority | Phase | Ship Order | Status | Dependencies | Prioritization Rationale |
|---|---|---|---|---|---|---|
| `prd-onboarding-and-intake.md` | P0 | MVP | 1 | Done | none | Required to activate households and unlock all downstream value loops. |
| `prd-shared-list-collaboration.md` | P0 | MVP | 2 | Done | `prd-onboarding-and-intake.md` | Core daily utility; without list collaboration, savings loop cannot start. |
| `prd-swap-discovery-and-claiming.md` | P0 | MVP | 3 | Done | `prd-shared-list-collaboration.md` | First direct path to measurable savings and north star movement. |
| `prd-receipt-redemption-and-wallet.md` | P1 | v1.1 | 4 | Done | `prd-swap-discovery-and-claiming.md` | Converts claims into verified value; phased after core claim adoption stabilizes. |
| `prd-brand-portal-and-demand-response.md` | P1 | v1.1 | 5 | Deferred | `prd-swap-discovery-and-claiming.md` | Expands supply-side offer inventory after demand signal quality is proven. |
| `prd-referrals-growth-economics.md` | P1 | v2.0 | 6 | Done | `prd-receipt-redemption-and-wallet.md`, `prd-brand-portal-and-demand-response.md` | Growth optimization follows once core economics are trusted and measurable. |
| `prd-whatsapp-and-scale-operations.md` | P2 | Future | 7 | Deferred | `prd-onboarding-and-intake.md`, `prd-shared-list-collaboration.md`, `prd-referrals-growth-economics.md` | Channel expansion is deferred until baseline quality and economics are stable. |

## Execution Order
1. `docs/PRD/bob-shopping-agent/prd-onboarding-and-intake.md`
2. `docs/PRD/bob-shopping-agent/prd-shared-list-collaboration.md`
3. `docs/PRD/bob-shopping-agent/prd-swap-discovery-and-claiming.md`
4. `docs/PRD/bob-shopping-agent/prd-receipt-redemption-and-wallet.md`
5. `docs/PRD/bob-shopping-agent/prd-brand-portal-and-demand-response.md`
6. `docs/PRD/bob-shopping-agent/prd-referrals-growth-economics.md`
7. `docs/PRD/bob-shopping-agent/prd-whatsapp-and-scale-operations.md`
