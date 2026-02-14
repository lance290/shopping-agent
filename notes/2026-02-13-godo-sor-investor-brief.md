# GoDo as System of Record for BuyAnything

## One-liner

BuyAnything uses GoDo — our blockchain-verified compliance platform — as the system of record for all high-value and service-provider transactions.

## How it works

BuyAnything is a two-tier marketplace:

- **Commodity tier** (Amazon, eBay, Google Shopping) — standard e-commerce bids managed entirely within BuyAnything's operational database.
- **Premium tier** (private aviation, concierge, bespoke services, high-ticket goods) — every bid, quote, deal handoff, and financial event is forwarded to GoDo for immutable recording.

GoDo provides:

- **Immutable event log** — append-only, cryptographically checksummed records of every premium transaction.
- **Blockchain anchoring** — decision hashes written to Ethereum (L2) for tamper-proof, third-party-verifiable audit trails.
- **Compliance rules engine** — LLM-assisted regulatory evaluation (built for ABL/EWA-grade requirements).
- **Durable workflows** — Temporal.io orchestration ensures exactly-once execution of critical deal flows.

## Why it matters

BuyAnything's clientele are high-net-worth individuals transacting on high-value services. A $50k private jet charter or a six-figure procurement requires a legally defensible record that cannot be altered or lost. GoDo delivers that — and we already own and operate it.

## Architecture (simplified)

```
BuyAnything (operational layer)
  ├── Commodity bids → BuyAnything DB (pgvector, backups)
  └── Premium events → GoDo (immutable log + blockchain anchor)
                          └── Independent Postgres + Ethereum L2
```

Both systems run on Railway. BuyAnything's DB is backed up continuously via WAL archiving. GoDo's event store is an independent, append-only copy — if either system fails, the other survives.
