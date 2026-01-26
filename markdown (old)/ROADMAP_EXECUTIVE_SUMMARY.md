# Implementation Roadmap - Executive Summary

**Project:** Shopping Agent Multi-Feature Implementation
**Timeline:** 12 weeks (MVP in 8 weeks)
**Budget:** $390,000
**Team Size:** 6.5 FTEs
**Status:** Planning Complete ✅

---

## Quick Facts

### Features Being Implemented

| # | Feature | Status | Priority | Duration | Team |
|---|---------|--------|----------|----------|------|
| 1 | **Clerk SMS Authentication** | Architected | HIGH | 4 weeks | 1 FS Dev |
| 2 | **Google Shopping Integration** | Architected | HIGH | 2 weeks | 1 BE Dev |
| 3 | **Tile Interaction System** | Architected | MEDIUM | 4 weeks | 1 FE + 1 BE |
| 4 | **Tile Layout Refactor** | ✅ Complete | N/A | 0 weeks | N/A |
| 5 | **Interactive FAQ Collection** | Pending | MEDIUM | 2 weeks | 1 FS Dev |

---

## Timeline at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: Foundation (Weeks 1-2)                            │
│  ▪ Clerk SMS setup + integration                             │
│  ▪ Google Shopping provider implementation                   │
│  ▪ Tile interactions database + API                          │
├─────────────────────────────────────────────────────────────┤
│  Phase 2: Integration & Polish (Weeks 3-4)                  │
│  ▪ Clerk SMS testing + migration flow                        │
│  ▪ Google Shopping optimization + caching                    │
│  ▪ Tile interactions frontend + animations                   │
├─────────────────────────────────────────────────────────────┤
│  Phase 3: FAQ Collection (Weeks 5-6)                        │
│  ▪ Chat-based purchase factor collection                     │
│  ▪ LLM integration for question generation                   │
│  ▪ RequestTile integration                                   │
├─────────────────────────────────────────────────────────────┤
│  Phase 4: Testing & Launch (Weeks 7-8)                      │
│  ▪ Integration testing                                       │
│  ▪ Security audit                                            │
│  ▪ Production deployment (10% rollout)                       │
├─────────────────────────────────────────────────────────────┤
│  Phase 5: Full Rollout (Weeks 9-12)                         │
│  ▪ Gradual rollout to 100%                                   │
│  ▪ Legacy auth deprecation                                   │
│  ▪ V2 planning                                               │
└─────────────────────────────────────────────────────────────┘

MVP Launch: Week 8
Full Rollout: Week 12
```

---

## Dependency Graph

```
                    START
                      │
                      ├──────────────┬──────────────┬──────────────┐
                      ▼              ▼              ▼              ▼
              ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
              │  Clerk   │   │  Google  │   │   Tile   │   │  Layout  │
              │   SMS    │   │ Shopping │   │Interact. │   │ Refactor │
              │          │   │          │   │          │   │          │
              │ Week 1-4 │   │ Week 1-4 │   │ Week 1-4 │   │ COMPLETE │
              └────┬─────┘   └────┬─────┘   └────┬─────┘   └─────┬────┘
                   │              │              │               │
                   └──────┬───────┴──────┬───────┘               │
                          │              │                       │
                          ▼              ▼                       │
                    ┌──────────────────────┐                    │
                    │    FAQ Collection    │◀───────────────────┘
                    │                      │
                    │      Week 5-6        │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Integration Testing │
                    │      Week 7-8        │
                    └──────────┬───────────┘
                               │
                               ▼
                          PRODUCTION
```

**Key Insights:**
- 3 features can start immediately (parallel work)
- FAQ depends on Auth + Google Shopping
- Layout refactor already complete (saves 2 weeks!)

---

## Critical Path

**Longest Sequence:** 8 weeks

```
Week 1-2: Clerk SMS (Foundation)
    ↓
Week 3-4: Clerk SMS (Testing)
    ↓
Week 5-6: FAQ Collection (depends on Auth)
    ↓
Week 7-8: Integration Testing + Launch
```

**Bottleneck:** Clerk SMS migration (4 weeks)
**Risk:** SMS delivery or user adoption issues

---

## MVP vs V2 Scope

### MVP (Week 8 Launch)

**SHIP:**
- ✅ Phone login with SMS codes
- ✅ Google Shopping auto-bidding
- ✅ Like functionality + basic reordering
- ✅ Simplified FAQ (3-5 questions)

**DEFER to V2:**
- ❌ Comment threads
- ❌ Share functionality
- ❌ Real-time WebSocket updates
- ❌ Advanced FAQ branching
- ❌ Email auth deprecation (migration period)

### V2 Enhancements (Weeks 9-16)

**Phase 2A: Social Features**
- Comment system with threads
- Share via link/email
- Advanced sorting (engagement, recency)

**Phase 2B: Search Enhancements**
- Review data enrichment
- Multi-provider deduplication
- Merchant reputation scoring

**Phase 2C: Chat & FAQ**
- Branching question logic
- Multi-turn conversations
- Pre-fill from history

**Phase 2D: Polish & Scale**
- Redis caching
- Virtual scrolling
- Legacy auth removal

---

## Resource Plan

### Team Allocation

```
Tech Lead (1)
    │
    ├─ Stream A: Auth Team
    │  └─ Full-Stack Dev 1 (100%, Weeks 1-8)
    │
    ├─ Stream B: Search Team
    │  └─ Backend Dev 1 (100%, Weeks 1-4)
    │
    ├─ Stream C: Social Team
    │  ├─ Frontend Dev 1 (100%, Weeks 1-4)
    │  └─ Backend Dev 2 (100%, Weeks 1-2)
    │
    ├─ Stream D: Chat Team
    │  └─ Full-Stack Dev 2 (100%, Weeks 5-6)
    │
    └─ Support
       ├─ QA Engineer (100%, Weeks 1-12)
       └─ DevOps Engineer (25%, Weeks 1-12)
```

**Total:** 5 developers + 2 support = 6.5 FTEs

---

### Budget Summary

| Category | Cost | Notes |
|----------|------|-------|
| **Development** | $373,600 | 5 developers × 8-12 weeks |
| **Support** | $15,600 | QA + DevOps (partial) |
| **Infrastructure** | $1,287 | Clerk, SMS, hosting, monitoring |
| **TOTAL** | **$390,487** | 12-week project |

**Cost per Week:** ~$32,500
**Cost per Feature:** ~$78,000 (5 features)

---

## Risk Matrix

### High Priority Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Clerk SMS costs exceed budget** | 🟡 Medium | 🟡 Medium | Daily monitoring + spend caps |
| **LLM question quality poor** | 🔴 High | 🟡 Medium | User testing + fallback templates |
| **Critical production bug** | 🔴 Critical | 🟡 Medium | Staged rollout + feature flags |
| **User migration adoption low** | 🟡 Medium | 🟡 Medium | Incentives + clear messaging |

### Low Priority Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Animation performance jank** | 🟢 Low | 🟡 Medium | GPU acceleration + testing |
| **Google quota exhausted** | 🔴 High | 🟢 Low | Aggressive caching + fallback |
| **Team member blocked** | 🟡 Medium | 🟡 Medium | Daily standups + clear comms |

**Overall Risk Level:** 🟡 MEDIUM

---

## Success Metrics

### Launch Criteria (Week 8)

**Technical:**
- [ ] API P95 response time < 2s
- [ ] Error rate < 1%
- [ ] Test coverage > 80%
- [ ] Load test passed (1000 users)

**Product:**
- [ ] Clerk SMS adoption > 50%
- [ ] Google Shopping > 10 offers/row
- [ ] Tile interaction rate > 30%
- [ ] FAQ completion rate > 70%

**Business:**
- [ ] Zero critical bugs
- [ ] Support tickets < 5% increase
- [ ] User satisfaction > 4.0/5.0

---

## Parallel Work Streams

### Week 1-2: All Hands on Deck

```
┌─────────────────────────────────────────────────────────┐
│ Monday          Tuesday         Wednesday    Thu    Fri │
├─────────────────────────────────────────────────────────┤
│ FS Dev 1: Clerk setup → Frontend → Backend → Test      │
│ BE Dev 1: Google API → Provider → Cache → Test         │
│ FE Dev 1: Design patterns → Components (prep)          │
│ BE Dev 2: DB schema → API endpoints → Test             │
│ QA: Test plans → Automation setup → Smoke tests        │
└─────────────────────────────────────────────────────────┘
```

**Sync Points:**
- Daily standup: 9:30 AM
- Integration meeting: Friday 2 PM
- Demo to stakeholders: Friday 3 PM

**Communication:**
- Slack: `#shopping-agent-dev`
- Jira: Sprint board
- GitHub: Feature branches → `develop`

---

## Testing Strategy

### Coverage Targets

```
        E2E (10%)
         /\
        /  \
       /────\
      /Integ.\  (20%)
     /        \
    /──────────\
   /    Unit    \  (70%)
  /______________\
```

**Tools:**
- Unit: Vitest (FE), Pytest (BE)
- Integration: Playwright, Postman
- E2E: Playwright
- Load: Artillery, k6

**Pre-Launch Checklist:**
- [ ] All E2E tests passing
- [ ] Security audit complete
- [ ] Load test (1000 users) passed
- [ ] Cross-browser tested
- [ ] Mobile responsive verified
- [ ] Feature flags configured
- [ ] Rollback procedure tested

---

## Integration Points

### Data Flow Diagram

```
┌─────────────┐
│  Clerk JWT  │
│  (User ID)  │
└──────┬──────┘
       │
       ├─────────────────┬────────────────┬───────────────┐
       ▼                 ▼                ▼               ▼
┌──────────┐      ┌──────────┐    ┌──────────┐   ┌──────────┐
│   FAQ    │      │  Google  │    │   Tile   │   │   Row    │
│  Chat    │◀─────│ Shopping │    │ Interact.│   │  System  │
└──────────┘      └──────────┘    └────┬─────┘   └────┬─────┘
       │                                │              │
       └────────────────────────────────┴──────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │  PostgreSQL  │
                  │   Database   │
                  └──────────────┘
```

**Shared Components:**
- Database: `user`, `row`, `bid` tables
- State: Zustand `rowResults`, `activeRowId`
- API: Clerk JWT authentication on all endpoints

---

## Milestones & Go/No-Go Decisions

### Milestone 1: Foundation (Week 2)

**Deliverables:**
- Clerk SMS working in dev
- Google Shopping returning results
- Tile interactions API ready

**Go/No-Go Criteria:**
- [ ] All features functional
- [ ] No critical blockers
- [ ] Team velocity ±20% of plan

**Decision:** Proceed to Phase 2? ✅ / ❌

---

### Milestone 2: Integration (Week 4)

**Deliverables:**
- Clerk SMS in staging
- Google Shopping optimized
- Tile interactions UI complete

**Go/No-Go Criteria:**
- [ ] Staging environment stable
- [ ] Performance tests passing
- [ ] UAT positive

**Decision:** Proceed to Phase 3? ✅ / ❌

---

### Milestone 3: FAQ Complete (Week 6)

**Deliverables:**
- FAQ chat functional
- RequestTile integration
- LLM quality validated

**Go/No-Go Criteria:**
- [ ] FAQ completion rate > 70%
- [ ] Questions are relevant
- [ ] No critical bugs

**Decision:** Proceed to Production? ✅ / ❌

---

### Milestone 4: MVP Launch (Week 8)

**Deliverables:**
- 10% production rollout
- All features integrated
- Monitoring active

**Go/No-Go Criteria:**
- [ ] Error rate < 1%
- [ ] Security audit passed
- [ ] Load test successful

**Decision:** Proceed with Full Rollout? ✅ / ❌

---

## Rollback Plan

### Emergency Rollback (15 minutes)

```bash
# 1. Disable feature flags
kubectl set env deployment/frontend CLERK_ENABLED=false
kubectl set env deployment/frontend GOOGLE_SHOPPING_ENABLED=false
kubectl set env deployment/frontend TILE_INTERACTIONS_ENABLED=false

# 2. Rollback deployment (if needed)
kubectl rollout undo deployment/frontend
kubectl rollout undo deployment/backend

# 3. Verify
kubectl get pods
curl https://app.example.com/health
```

### Database Rollback (15 minutes)

```bash
# Only if database changes break production
cd apps/backend
alembic downgrade -1
```

### Communication

```
Subject: Service Interruption - Rollback in Progress

We've detected an issue with our latest deployment and are
rolling back to the previous version. Service should be
restored within 15 minutes.

Status updates: https://status.example.com
```

---

## Next Steps

### Immediate Actions (This Week)

1. **Approve Roadmap**
   - Review with stakeholders
   - Get sign-off on budget and timeline

2. **Team Allocation**
   - Assign developers to streams
   - Schedule kick-off meeting

3. **Infrastructure Setup**
   - Create Clerk account
   - Enable Google Shopping API
   - Set up feature flags

4. **Project Management**
   - Create Jira board with all tasks
   - Set up Slack channels
   - Schedule recurring meetings

### Week 1 Kickoff Agenda

**Monday, Week 1:**
- 9:00 AM: All-hands kickoff meeting
- 10:00 AM: Architecture review
- 11:00 AM: Break into work streams
- 2:00 PM: Sprint planning
- 4:00 PM: Environment setup

**Daily for Week 1:**
- 9:30 AM: Standup
- 5:00 PM: End-of-day sync

---

## FAQs

**Q: Can we launch faster than 8 weeks?**

A: Possible but risky. Critical path is 8 weeks assuming no major blockers. We could reduce to 6 weeks by:
- Deferring FAQ to V2
- Using Clerk's pre-built UI (less custom)
- Reducing testing scope (not recommended)

**Q: What if Google Shopping quota is too low?**

A: We have fallback options:
1. Use SerpAPI (paid backup)
2. Aggressive caching (1-hour TTL → 24-hour)
3. Request quota increase from Google

**Q: What if users resist phone authentication?**

A: Migration strategy includes:
- Dual auth support (email + phone) for 30 days
- Clear benefits messaging
- Optional migration (not forced initially)
- Fallback to email if SMS fails

**Q: Can we add more features mid-project?**

A: Not recommended. Scope creep is #1 cause of delays. Log requests for V2.

**Q: What's the rollback success rate?**

A: With feature flags, rollback takes <15 minutes. Database rollbacks take longer (30 min) but are rarely needed. Practice rollback in staging first.

---

## Contact & Escalation

**Project Leadership:**
- Tech Lead: [Name]
- Product Manager: [Name]
- Engineering Manager: [Name]

**Escalation Path:**
1. Try to resolve in stream (30 min)
2. Escalate to Tech Lead
3. If critical, page on-call
4. If business impact, notify PM

**Communication Channels:**
- Slack: `#shopping-agent-dev` (general)
- Slack: `#shopping-agent-critical` (incidents)
- Email: engineering@company.com
- Phone: On-call rotation (PagerDuty)

---

## Document Status

**Version:** 1.0
**Last Updated:** 2026-01-20
**Next Review:** End of Week 2 (Milestone 1)
**Owner:** Architecture Team

**Change Log:**
- 2026-01-20: Initial roadmap created
