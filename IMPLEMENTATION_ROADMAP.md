# Shopping Agent - Comprehensive Implementation Roadmap

**Document Version:** 1.0
**Created:** 2026-01-20
**Status:** Planning Phase

---

## Executive Summary

This roadmap provides a comprehensive implementation strategy for 5 major feature initiatives across the Shopping Agent application. The plan prioritizes dependencies, identifies parallel work streams, and establishes a phased rollout over 12-16 weeks.

**Features to Implement:**
1. **Clerk SMS Authentication** - Replace custom email auth with phone-based SMS
2. **Google Shopping Integration** - Auto-bidding from Google Shopping API
3. **Tile Interaction System** - Like, comment, share with dynamic reordering
4. **Tile Layout Refactor** - Each purchase request as row with RequestTile + bid tiles
5. **Interactive FAQ Collection** - Chat-based purchase factor collection

**Total Estimated Timeline:** 12-16 weeks (3-4 months)
**Recommended Team Size:** 3-5 developers + 1 QA + 1 designer
**Budget Estimate:** $150K-$200K (personnel + infrastructure)

---

## Table of Contents

1. [Dependency Analysis](#1-dependency-analysis)
2. [Critical Path Analysis](#2-critical-path-analysis)
3. [Implementation Phases](#3-implementation-phases)
4. [Parallel Work Streams](#4-parallel-work-streams)
5. [MVP vs V2 Feature Prioritization](#5-mvp-vs-v2-feature-prioritization)
6. [Risk Assessment by Phase](#6-risk-assessment-by-phase)
7. [Testing Strategy](#7-testing-strategy)
8. [Integration Points](#8-integration-points)
9. [Resource Allocation](#9-resource-allocation)
10. [Timeline and Milestones](#10-timeline-and-milestones)

---

## 1. Dependency Analysis

### Feature Dependency Graph

```
┌──────────────────────────────────────────────────────┐
│                  FOUNDATION LAYER                     │
│                  (Must Complete First)                │
├──────────────────────────────────────────────────────┤
│                                                       │
│  [4] Tile Layout Refactor                            │
│      Current: Row → RequestTile + OfferTiles         │
│      Target: Row → RequestTile (1st) + BidTiles (rest)│
│      Status: ✅ ALREADY COMPLETE                     │
│                                                       │
└──────────────────┬───────────────────────────────────┘
                   │
                   ├─────────────────┬─────────────────┬──────────────────┐
                   │                 │                 │                  │
                   ▼                 ▼                 ▼                  ▼
         ┌─────────────────┐ ┌──────────────┐ ┌─────────────┐  ┌──────────────┐
         │ [1] Clerk SMS   │ │ [2] Google   │ │ [3] Tile    │  │ [5] FAQ      │
         │ Authentication  │ │ Shopping     │ │ Interactions│  │ Collection   │
         │                 │ │              │ │             │  │              │
         │ INDEPENDENT     │ │ INDEPENDENT  │ │ INDEPENDENT │  │ DEPENDS ON:  │
         │                 │ │              │ │             │  │ - Auth (1)   │
         │ Blocks: N/A     │ │ Blocks: FAQ  │ │ Blocks: N/A │  │ - Chat UI    │
         └─────────────────┘ └──────┬───────┘ └─────────────┘  └──────────────┘
                                    │
                                    │ (Data source for FAQ)
                                    ▼
                            ┌──────────────────┐
                            │ [5] FAQ          │
                            │ Collection       │
                            │ (Phase 3)        │
                            └──────────────────┘
```

### Dependency Matrix

| Feature | Depends On | Blocks | Can Start Immediately? |
|---------|------------|--------|----------------------|
| **Clerk SMS Auth** | None | None | ✅ Yes |
| **Google Shopping** | None | FAQ Collection (data source) | ✅ Yes |
| **Tile Interactions** | None | None | ✅ Yes |
| **Tile Layout Refactor** | None | None | ✅ Already Complete |
| **FAQ Collection** | Auth (1), Chat UI | None | ⚠️ After Auth |

### Key Insights

1. **Layout Refactor Already Complete**: Current implementation already follows the target pattern (RequestTile as first tile, then OfferTiles)
2. **Three Independent Work Streams**: Auth, Google Shopping, and Tile Interactions can all proceed in parallel
3. **FAQ Depends on Multiple Features**: Requires authentication (for user context) and should wait for Google Shopping (to use its data)

---

## 2. Critical Path Analysis

### Critical Path: Foundation → MVP Launch

```
Week 1-2: Parallel Foundation
├─ Stream A: Clerk SMS (2 weeks)
├─ Stream B: Google Shopping (2 weeks)
└─ Stream C: Tile Interactions DB (1 week)

Week 3-4: Integration & Polish
├─ Stream A: Auth Testing & Migration
├─ Stream B: Google Shopping Testing
└─ Stream C: Tile Interactions Frontend (2 weeks)

Week 5-6: FAQ Collection
└─ Unified: Interactive FAQ System (2 weeks)

Week 7-8: Testing & Launch
└─ Full Integration Testing, Staging Deploy, Production Rollout
```

**Critical Path Duration:** 8 weeks (minimum)
**Realistic Timeline:** 10 weeks (with buffer for issues)

### Longest Pole Items

1. **Clerk SMS Migration** (2 weeks setup + 2 weeks migration) = **4 weeks total**
2. **Tile Interactions** (1 week backend + 2 weeks frontend + 1 week polish) = **4 weeks total**
3. **Google Shopping** (1 week integration + 1 week optimization) = **2 weeks total**

**Bottleneck:** Clerk SMS and Tile Interactions are tied for longest duration.

---

## 3. Implementation Phases

### Phase 0: Pre-Implementation (Week 0)

**Goal:** Set up infrastructure and planning

**Tasks:**
- [ ] Create project board with all features
- [ ] Set up feature flags for gradual rollout
- [ ] Create staging environment matching production
- [ ] Allocate team members to work streams
- [ ] Review and approve architecture documents
- [ ] Set up monitoring/alerting infrastructure

**Deliverables:**
- Project board with all tasks
- Feature flag configuration
- Staging environment ready
- Team assignments confirmed

**Duration:** 3-5 days

---

### Phase 1: Foundation (Weeks 1-2)

**Goal:** Implement core features that don't depend on each other

#### Stream A: Clerk SMS Authentication (Priority: HIGH)

**Week 1:**
- [ ] Day 1-2: Create Clerk app, configure SMS settings
- [ ] Day 3-4: Frontend integration (ClerkProvider, login page)
- [ ] Day 5: Backend JWT verification setup

**Week 2:**
- [ ] Day 1-2: Database migration (add clerk_user_id)
- [ ] Day 3: Dual auth support (legacy + Clerk)
- [ ] Day 4-5: Testing and bug fixes

**Deliverables:**
- Clerk SMS login working in development
- Dual auth support (email + phone)
- Database migrations complete

**Team:** 1 full-stack developer

---

#### Stream B: Google Shopping Integration (Priority: HIGH)

**Week 1:**
- [ ] Day 1-2: Set up Google Cloud project, enable API
- [ ] Day 3-4: Implement GoogleShoppingProvider class
- [ ] Day 5: Response mapping and error handling

**Week 2:**
- [ ] Day 1-2: Integration with SourcingRepository
- [ ] Day 3: Caching strategy implementation
- [ ] Day 4-5: Testing and quota monitoring

**Deliverables:**
- Google Shopping as new sourcing provider
- Results appearing in offer tiles
- Caching working, quota monitoring in place

**Team:** 1 backend developer

---

#### Stream C: Tile Interactions (Database) (Priority: MEDIUM)

**Week 1:**
- [ ] Day 1-2: Database schema design and migration
- [ ] Day 3-4: Backend API endpoints (like, comment, share)
- [ ] Day 5: Bulk engagement endpoint

**Week 2:**
- [ ] (Reserved for frontend work in Week 3-4)

**Deliverables:**
- Database tables created (tile_like, tile_comment, tile_share)
- API endpoints functional and tested
- Engagement aggregation working

**Team:** 1 backend developer

---

### Phase 2: Integration & Polish (Weeks 3-4)

**Goal:** Complete features and prepare for production

#### Stream A: Clerk SMS Migration (Priority: HIGH)

**Week 3:**
- [ ] Deploy to staging with dual auth
- [ ] Internal testing (team uses both auth methods)
- [ ] Create migration prompt UI for existing users
- [ ] Day 4-5: Fix bugs, polish UX

**Week 4:**
- [ ] Soft launch to 10% of new users
- [ ] Monitor error rates and SMS delivery
- [ ] Prepare user communications
- [ ] Day 4-5: Gradual rollout plan

**Deliverables:**
- Clerk SMS working in staging
- Migration flow tested
- Rollout plan documented

**Team:** 1 full-stack developer + 1 QA

---

#### Stream B: Google Shopping Optimization (Priority: MEDIUM)

**Week 3:**
- [ ] Performance optimization (parallel requests)
- [ ] Review enrichment (add ratings data)
- [ ] Match scoring improvements
- [ ] Day 4-5: Load testing

**Week 4:**
- [ ] Deploy to staging
- [ ] Monitor quota usage
- [ ] Optimize cache TTLs
- [ ] Integration with affiliate links

**Deliverables:**
- Response time < 2 seconds
- Review data enriched
- Production-ready

**Team:** 1 backend developer

---

#### Stream C: Tile Interactions (Frontend) (Priority: HIGH)

**Week 3:**
- [ ] Day 1-2: Create TileActions component (like, comment, share)
- [ ] Day 3-4: Comment panel slide-in
- [ ] Day 5: Share popover and copy functionality

**Week 4:**
- [ ] Day 1-2: Tile reordering animations (Framer Motion)
- [ ] Day 3: Zustand state integration
- [ ] Day 4-5: Testing and bug fixes

**Deliverables:**
- Like, comment, share working
- Dynamic tile reordering on like
- Smooth animations

**Team:** 1 frontend developer

---

### Phase 3: FAQ Collection (Weeks 5-6)

**Goal:** Implement chat-based purchase factor collection

**Prerequisites:** ✅ Auth (Phase 1A) ✅ Google Shopping (Phase 1B)

**Week 5:**
- [ ] Day 1-2: Design FAQ conversation flow
- [ ] Day 3-4: Update Chat component with FAQ mode
- [ ] Day 5: Backend LLM integration for question generation

**Week 6:**
- [ ] Day 1-2: Connect FAQ to RequestTile display
- [ ] Day 3: Save answers to row choice_answers
- [ ] Day 4-5: Testing and polish

**Deliverables:**
- Click + button starts FAQ chat
- Chat asks about purchase factors
- Answers populate RequestTile

**Team:** 1 full-stack developer + 1 AI/LLM specialist

---

### Phase 4: Testing & Integration (Weeks 7-8)

**Goal:** End-to-end testing and production deployment

**Week 7:**
- [ ] Day 1-2: Integration testing (all features together)
- [ ] Day 3: Load testing and performance tuning
- [ ] Day 4-5: Security audit and penetration testing

**Week 8:**
- [ ] Day 1: Deploy to staging
- [ ] Day 2-3: Final QA and bug fixes
- [ ] Day 4: Production deployment (10% rollout)
- [ ] Day 5: Monitor metrics, fix critical issues

**Deliverables:**
- All features integrated and tested
- Production deployment successful
- Monitoring dashboards showing green

**Team:** Entire team (3-5 developers + 1 QA)

---

### Phase 5: Rollout & Iteration (Weeks 9-12)

**Goal:** Gradual rollout and post-launch improvements

**Week 9:**
- [ ] Gradual rollout: 10% → 25% → 50%
- [ ] Monitor user feedback and metrics
- [ ] Fix high-priority bugs

**Week 10:**
- [ ] Rollout: 50% → 75% → 100%
- [ ] Performance optimization based on real usage
- [ ] Begin deprecation of legacy auth

**Week 11:**
- [ ] Legacy auth deprecation warnings
- [ ] Email migration reminders to remaining users
- [ ] Documentation updates

**Week 12:**
- [ ] Full rollout complete (100%)
- [ ] Cleanup legacy code
- [ ] Post-mortem and lessons learned
- [ ] Plan Phase 2 features

**Deliverables:**
- All features at 100% rollout
- Legacy systems deprecated
- Documentation complete
- Phase 2 roadmap

**Team:** 2 developers + 1 support engineer

---

## 4. Parallel Work Streams

### Swarm Coordination Strategy

**Team Structure:**

```
┌─────────────────────────────────────────────────────┐
│              Tech Lead / Architect                   │
│     (Coordinates all streams, resolves blockers)    │
└─────────────────────────────────────────────────────┘
            │
            ├──────────────┬──────────────┬──────────────┐
            ▼              ▼              ▼              ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  Stream A    │ │  Stream B    │ │  Stream C    │ │  Stream D    │
    │  Auth Team   │ │  Search Team │ │  Social Team │ │  Chat Team   │
    ├──────────────┤ ├──────────────┤ ├──────────────┤ ├──────────────┤
    │ - 1 FS Dev   │ │ - 1 BE Dev   │ │ - 1 FE Dev   │ │ - 1 FS Dev   │
    │ - Auth SME   │ │ - API SME    │ │ - UI/UX SME  │ │ - LLM SME    │
    └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
            │              │              │              │
            └──────────────┴──────────────┴──────────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │  QA Engineer     │
                  │  (Cross-stream)  │
                  └──────────────────┘
```

### Parallel Execution Schedule

**Phase 1 (Weeks 1-2):**

| Week | Stream A (Auth) | Stream B (Shopping) | Stream C (Interactions) | Dependencies |
|------|----------------|-------------------|----------------------|--------------|
| 1 | Clerk setup + Frontend | Google API + Provider | DB Schema + Backend API | None |
| 2 | Backend + Migration | Caching + Testing | (Frontend prep) | None |

**Phase 2 (Weeks 3-4):**

| Week | Stream A (Auth) | Stream B (Shopping) | Stream C (Interactions) | Dependencies |
|------|----------------|-------------------|----------------------|--------------|
| 3 | Staging + Testing | Optimization | Frontend Components | Phase 1 complete |
| 4 | Soft Launch | Deploy + Monitor | Animations + Polish | Phase 1 complete |

**Phase 3 (Weeks 5-6):**

| Week | Stream D (FAQ) | Notes |
|------|---------------|-------|
| 5 | Chat Flow Design + Backend | Requires Auth (A) + Data from Shopping (B) |
| 6 | Frontend + Testing | Can leverage Interactions UI patterns (C) |

### Communication & Sync Points

**Daily Standup (15 min):**
- Each stream reports: Yesterday's progress, Today's plan, Blockers
- Tech lead identifies cross-stream dependencies

**Weekly Integration Meeting (1 hour):**
- Demo completed features
- Merge code and resolve conflicts
- Adjust priorities based on progress

**Slack Channels:**
- `#shopping-agent-dev` - General development
- `#stream-auth` - Clerk SMS team
- `#stream-shopping` - Google Shopping team
- `#stream-social` - Tile interactions team
- `#stream-chat` - FAQ collection team

### Merge Strategy

**Branch Strategy:**
```
main (production)
  ├─ develop (integration branch)
     ├─ feature/clerk-sms-auth
     ├─ feature/google-shopping
     ├─ feature/tile-interactions
     └─ feature/faq-collection
```

**Merge Cadence:**
- Merge to `develop` daily (small, tested PRs)
- Merge `develop` → `main` weekly (after integration testing)
- Use feature flags to control rollout

---

## 5. MVP vs V2 Feature Prioritization

### MVP Scope (Weeks 1-8)

**Must-Have for Launch:**

1. ✅ **Clerk SMS Authentication**
   - Phone-based login with SMS codes
   - Dual auth support (migration period)
   - Session management

2. ✅ **Google Shopping Integration**
   - Auto-bidding from Google Shopping API
   - Product images, prices, merchant info
   - Basic caching (1-hour TTL)

3. ✅ **Tile Interactions (Core)**
   - Like functionality
   - Like counts displayed
   - Basic reordering by likes

4. ⚠️ **FAQ Collection (Simplified)**
   - Click + starts chat
   - Chat asks 3-5 key questions
   - Answers saved to RequestTile
   - Basic question flow (no branching)

**Out of Scope for MVP:**
- Comment threads (→ V2)
- Share functionality (→ V2)
- Real-time WebSocket updates (→ V2)
- Advanced FAQ branching logic (→ V2)
- Email auth deprecation (migration period)

---

### V2 Enhancements (Weeks 9-16)

**Phase 2A: Social Features (Weeks 9-10)**

1. **Comment System**
   - Threaded comments (1 level deep)
   - Comment panel slide-in
   - Edit/delete own comments
   - Comment count badges

2. **Share Functionality**
   - Copy shareable link
   - Email share
   - Share count tracking

3. **Advanced Reordering**
   - Sort by engagement (likes + comments)
   - Sort by recency
   - Manual drag-and-drop

---

**Phase 2B: Search Enhancements (Weeks 11-12)**

1. **Google Shopping Optimization**
   - Review data enrichment
   - Advanced filtering (price range, brand)
   - Merchant reputation scoring

2. **Multi-Provider Deduplication**
   - Smart deduplication across sources
   - Confidence scoring
   - User preference learning

---

**Phase 2C: Chat & FAQ (Weeks 13-14)**

1. **Advanced FAQ Logic**
   - Branching question flows
   - Context-aware questions
   - Pre-fill from past requests

2. **Chat Improvements**
   - Multi-turn conversations
   - Edit/undo responses
   - Save conversation history

---

**Phase 2D: Polish & Scale (Weeks 15-16)**

1. **Performance**
   - Redis caching layer
   - CDN for images
   - Virtual scrolling for large rows

2. **Analytics**
   - User engagement dashboards
   - A/B testing framework
   - Conversion tracking

3. **Cleanup**
   - Remove legacy auth system
   - Database optimization
   - Code refactoring

---

## 6. Risk Assessment by Phase

### Phase 1 Risks (Weeks 1-2)

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Clerk SMS costs exceed budget** | Medium | Medium | Monitor daily usage, set quota alerts, add spend cap |
| **Google Shopping quota exhausted** | Low | High | Implement aggressive caching, use fallback provider (SerpAPI) |
| **Database migration breaks prod** | Low | Critical | Test migration in staging 3x, have rollback script ready |
| **Team members blocked on dependencies** | Medium | Medium | Daily standups, clear communication, task queue |

**Mitigation Strategy:**
- Run all migrations in staging first
- Set up cost alerts for Clerk and Google APIs
- Have rollback procedures documented
- Use feature flags to disable features quickly

---

### Phase 2 Risks (Weeks 3-4)

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Tile reordering animations cause jank** | Medium | Low | Use GPU-accelerated CSS transforms, test on slow devices |
| **SMS delivery failures** | Low | High | Clerk handles this, but monitor delivery rates |
| **User migration adoption low** | Medium | Medium | Show clear benefits, offer incentives, gentle prompts |
| **Integration bugs across streams** | High | Medium | Weekly integration testing, shared Storybook |

**Mitigation Strategy:**
- Performance testing on low-end devices
- Monitor SMS delivery rates in Clerk dashboard
- A/B test migration prompts
- Dedicated integration day each week

---

### Phase 3 Risks (Weeks 5-6)

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **LLM question generation quality poor** | Medium | High | Test with real users, iterate on prompts, add fallback templates |
| **FAQ chat flow confuses users** | Medium | Medium | User testing, clear instructions, skip option |
| **Depends on Auth + Shopping complete** | Low | High | Phases 1-2 are on critical path, monitor closely |

**Mitigation Strategy:**
- Early user testing with FAQ prototypes
- Provide skip/cancel options in chat
- Buffer time in Phase 2 for delays

---

### Phase 4 Risks (Weeks 7-8)

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Critical bug found in production** | Medium | Critical | Gradual rollout (10% → 100%), feature flags for instant disable |
| **Performance degradation under load** | Medium | High | Load testing before launch, auto-scaling infrastructure |
| **User complaints about new auth** | Low | Medium | Clear communication, support documentation, fallback to email |

**Mitigation Strategy:**
- Staged rollout with monitoring at each stage
- Load testing with 10x expected traffic
- Support team trained on new features
- One-click rollback procedure

---

## 7. Testing Strategy

### Testing Pyramid

```
                    /\
                   /  \
                  / E2E \ ← 10% (Critical user flows)
                 /      \
                /--------\
               /  Integ. \ ← 20% (API + DB interactions)
              /           \
             /-------------\
            /     Unit      \ ← 70% (Business logic, utils)
           /                 \
          /___________________\
```

### Test Coverage Targets

| Layer | Coverage | Tools | Owner |
|-------|----------|-------|-------|
| **Unit Tests** | 80% | Vitest (Frontend), Pytest (Backend) | Each developer |
| **Integration Tests** | 60% | Playwright, Postman | QA + Developers |
| **E2E Tests** | Critical paths | Playwright | QA Lead |
| **Performance Tests** | Key endpoints | Artillery, k6 | Backend team |

---

### Phase-by-Phase Testing

**Phase 1 Testing (Weeks 1-2):**

**Clerk SMS:**
- [ ] Unit: JWT verification logic
- [ ] Integration: POST /auth/start-sms, /auth/verify-sms
- [ ] E2E: New user signup with phone → login → session valid
- [ ] E2E: Existing user (email) → see migration prompt

**Google Shopping:**
- [ ] Unit: Response mapping, caching logic
- [ ] Integration: GoogleShoppingProvider.search()
- [ ] E2E: Create row → see Google Shopping offers
- [ ] Performance: < 2s response time for 50 products

**Tile Interactions (Backend):**
- [ ] Unit: Engagement aggregation queries
- [ ] Integration: POST /api/tiles/:bidId/like
- [ ] Integration: GET /api/rows/:rowId/tiles/engagement
- [ ] Load: 100 concurrent like requests

---

**Phase 2 Testing (Weeks 3-4):**

**Clerk SMS Migration:**
- [ ] E2E: Existing user links phone → login with phone works
- [ ] E2E: Dual auth works (both email and phone sessions valid)
- [ ] E2E: 10% rollout via feature flag

**Google Shopping Optimization:**
- [ ] Performance: Cache hit rate > 60%
- [ ] Load: 1000 searches/hour within quota
- [ ] E2E: Review data displayed correctly

**Tile Interactions (Frontend):**
- [ ] E2E: Click like → count increments → tile reorders
- [ ] E2E: Open comment panel → add comment → see in list
- [ ] E2E: Share tile → copy link → link works
- [ ] Visual: Animations smooth on iPhone 8 (benchmark)

---

**Phase 3 Testing (Weeks 5-6):**

**FAQ Collection:**
- [ ] E2E: Click + → chat opens → answer 3 questions → RequestTile updates
- [ ] Integration: LLM generates contextual questions
- [ ] Unit: Question parsing and answer storage
- [ ] Usability: 5 users can complete flow without help

---

**Phase 4 Testing (Weeks 7-8):**

**Full Integration:**
- [ ] E2E: Complete user journey (signup → FAQ → search → like → select)
- [ ] Load: 1000 concurrent users on staging
- [ ] Security: Penetration testing on all auth flows
- [ ] Cross-browser: Chrome, Safari, Firefox, Edge
- [ ] Mobile: iOS Safari, Android Chrome

---

### Testing Checklist Before Production

```markdown
## Pre-Launch Checklist

### Functionality
- [ ] All features work on staging
- [ ] No critical bugs in backlog
- [ ] All E2E tests passing
- [ ] Mobile responsive (iOS + Android)

### Performance
- [ ] P95 response time < 2s for all endpoints
- [ ] Load test passed (1000 concurrent users)
- [ ] Database indexes optimized
- [ ] Caching strategy validated

### Security
- [ ] Auth flows penetration tested
- [ ] SQL injection tests passed
- [ ] XSS vulnerability scan clean
- [ ] API rate limiting tested
- [ ] Secrets rotated (no test keys in prod)

### Monitoring
- [ ] Error tracking (Sentry) configured
- [ ] Performance monitoring (DataDog) active
- [ ] Alerts set up (PagerDuty)
- [ ] Dashboard showing green

### Documentation
- [ ] User guide updated
- [ ] API docs current
- [ ] Runbook for on-call engineer
- [ ] Rollback procedure documented

### Rollout
- [ ] Feature flags configured (10% rollout)
- [ ] Rollback plan tested
- [ ] Support team trained
- [ ] User communication prepared
```

---

## 8. Integration Points

### Feature Integration Map

```
┌─────────────────────────────────────────────────────────────┐
│                      Application Layer                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────┐   ┌──────────────┐   ┌────────────────┐   │
│  │   Auth     │──▶│  User Context│──▶│  Personalized  │   │
│  │  (Clerk)   │   │  (user_id)   │   │  Experience    │   │
│  └────────────┘   └──────────────┘   └────────────────┘   │
│         │                │                      │           │
│         │                ▼                      ▼           │
│         │         ┌──────────────┐      ┌──────────────┐   │
│         │         │ Row/Request  │      │  Tile Social │   │
│         │         │   System     │◀─────│  Features    │   │
│         │         └──────────────┘      └──────────────┘   │
│         │                │                      │           │
│         │                ▼                      │           │
│         │         ┌──────────────┐             │           │
│         └────────▶│  FAQ Chat    │             │           │
│                   │  Collection  │             │           │
│                   └──────────────┘             │           │
│                          │                     │           │
│                          ▼                     ▼           │
│                   ┌──────────────────────────────────┐     │
│                   │     Google Shopping API          │     │
│                   │  (Data Source for Offers)        │     │
│                   └──────────────────────────────────┘     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Integration Points

**1. Auth → All Features**
- **Integration:** Clerk JWT passed in Authorization header
- **Data Flow:** User ID extracted from JWT → used for user-specific queries
- **Critical Point:** All protected endpoints verify JWT
- **Testing:** Test each feature with valid/invalid tokens

**2. Google Shopping → FAQ Collection**
- **Integration:** FAQ uses Google Shopping data to suggest questions
- **Data Flow:** User searches → Google returns product attributes → FAQ asks about missing attributes
- **Critical Point:** FAQ must gracefully handle missing Google data
- **Testing:** Test FAQ with and without Google Shopping results

**3. Tile Interactions → Row Sorting**
- **Integration:** Like counts stored in bid table → used for sorting offers
- **Data Flow:** User likes tile → increment like_count → re-sort row
- **Critical Point:** Sorting must be fast even with 50+ tiles
- **Testing:** Performance test with 100 tiles

**4. FAQ Collection → RequestTile Display**
- **Integration:** FAQ answers saved to row.choice_answers → displayed in RequestTile
- **Data Flow:** User completes FAQ → answers persisted → RequestTile re-renders
- **Critical Point:** RequestTile must update without page refresh
- **Testing:** Test various answer combinations

---

### Shared Components

**Database:**
- `user` table: Shared by Auth (clerk_user_id) and all features (user_id FK)
- `row` table: Shared by FAQ (choice_answers), Interactions (row_id FK), and Shopping (search query)
- `bid` table: Shared by Shopping (offer data), Interactions (engagement counts), and Selection (is_selected)

**State Management (Zustand):**
- `rowResults`: Shared by Shopping (offer data), Interactions (engagement), and Selection
- `activeRowId`: Shared by RequestTile, FAQ, and Sidebar
- `isSearching`: Shared by Shopping and UI loading states

**API Layer:**
- All features use same authentication (Clerk JWT)
- All features return JSON with standard error format
- All features support feature flags (gradual rollout)

---

## 9. Resource Allocation

### Team Composition

**Development Team:**

| Role | Count | Allocation | Primary Focus |
|------|-------|-----------|---------------|
| **Tech Lead** | 1 | 100% | Architecture, integration, unblocking |
| **Full-Stack Developer 1** | 1 | 100% | Clerk SMS Auth (Phases 1-2) |
| **Backend Developer 1** | 1 | 100% | Google Shopping (Phases 1-2) |
| **Frontend Developer 1** | 1 | 100% | Tile Interactions UI (Phases 1-2) |
| **Backend Developer 2** | 1 | 100% | Tile Interactions API (Phase 1), FAQ (Phase 3) |
| **Full-Stack Developer 2** | 1 | 50% Phase 1-2, 100% Phase 3 | FAQ Collection (Phase 3) |
| **QA Engineer** | 1 | 100% | Cross-stream testing, automation |
| **DevOps Engineer** | 1 | 25% | Infrastructure, monitoring, deployments |

**Total:** 5.25 FTEs (development) + 1.25 support (QA + DevOps)

---

### Budget Breakdown

**Personnel Costs (12 weeks):**

| Role | Rate | Weeks | Total |
|------|------|-------|-------|
| Tech Lead | $200/hr × 40hr/wk | 12 | $96,000 |
| Full-Stack Dev 1 | $150/hr × 40hr/wk | 8 | $48,000 |
| Backend Dev 1 | $140/hr × 40hr/wk | 8 | $44,800 |
| Frontend Dev 1 | $140/hr × 40hr/wk | 8 | $44,800 |
| Backend Dev 2 | $140/hr × 40hr/wk | 10 | $56,000 |
| Full-Stack Dev 2 | $150/hr × 40hr/wk | 6 | $36,000 |
| QA Engineer | $100/hr × 40hr/wk | 12 | $48,000 |
| DevOps Engineer | $130/hr × 10hr/wk | 12 | $15,600 |

**Subtotal Personnel:** $389,200

---

**Infrastructure Costs (12 weeks):**

| Service | Monthly Cost | 3 Months | Total |
|---------|-------------|----------|-------|
| Clerk Pro | $25 | 3 | $75 |
| SMS (10K users) | $150 | 3 | $450 |
| Google Shopping API | $0 (free tier) | 3 | $0 |
| Database (PostgreSQL) | $50 | 3 | $150 |
| Hosting (Vercel/Railway) | $100 | 3 | $300 |
| Monitoring (DataDog) | $75 | 3 | $225 |
| Error Tracking (Sentry) | $29 | 3 | $87 |

**Subtotal Infrastructure:** $1,287

---

**Total Project Cost:** ~$390K (12 weeks)

**Cost Optimization:**
- Use free tiers where possible (Google Shopping, Clerk development)
- Defer non-MVP features to reduce timeline
- Consider contractors for specialized work (e.g., LLM integration)

---

## 10. Timeline and Milestones

### Gantt Chart Overview

```
Weeks  1    2    3    4    5    6    7    8    9-12
     ┌────┬────┬────┬────┬────┬────┬────┬────┬────┐
Auth │████│████│░░░░│░░░░│    │    │    │████│    │
     ├────┼────┼────┼────┼────┼────┼────┼────┼────┤
Shop │████│████│░░░░│░░░░│    │    │    │    │    │
     ├────┼────┼────┼────┼────┼────┼────┼────┼────┤
Tile │████│    │████│████│    │    │    │    │    │
     ├────┼────┼────┼────┼────┼────┼────┼────┼────┤
FAQ  │    │    │    │    │████│████│    │    │    │
     ├────┼────┼────┼────┼────┼────┼────┼────┼────┤
Test │    │    │    │    │    │    │████│████│    │
     ├────┼────┼────┼────┼────┼────┼────┼────┼────┤
Roll │    │    │    │    │    │    │    │    │████│
     └────┴────┴────┴────┴────┴────┴────┴────┴────┘
Legend: ████ = Development  ░░░░ = Testing
```

---

### Milestone Schedule

**Milestone 1: Foundation Complete (End of Week 2)**

**Deliverables:**
- ✅ Clerk SMS login working in dev
- ✅ Google Shopping returning results
- ✅ Tile interactions database + API ready

**Acceptance Criteria:**
- Can login with phone number in development
- Google Shopping offers appear in UI
- Like endpoint returns correct engagement counts

**Risk Level:** 🟡 Medium (new external dependencies)

---

**Milestone 2: Integration Complete (End of Week 4)**

**Deliverables:**
- ✅ Clerk SMS in staging with dual auth
- ✅ Google Shopping optimized and cached
- ✅ Tile interactions UI complete with animations

**Acceptance Criteria:**
- Staging environment mirrors production
- All features working together
- Performance tests passing

**Risk Level:** 🟢 Low (integration mostly complete)

---

**Milestone 3: FAQ Collection Complete (End of Week 6)**

**Deliverables:**
- ✅ Click + starts FAQ chat
- ✅ Chat asks contextual questions
- ✅ Answers populate RequestTile

**Acceptance Criteria:**
- User can complete FAQ flow without assistance
- RequestTile updates immediately
- Questions are relevant to product type

**Risk Level:** 🟡 Medium (LLM quality unknown)

---

**Milestone 4: MVP Ready (End of Week 8)**

**Deliverables:**
- ✅ All features tested and integrated
- ✅ Production deployment (10% rollout)
- ✅ Monitoring and alerts active

**Acceptance Criteria:**
- All tests passing
- 10% of users using new features
- Zero critical bugs

**Risk Level:** 🟠 High (first real user traffic)

---

**Milestone 5: Full Rollout (End of Week 12)**

**Deliverables:**
- ✅ 100% of users on new features
- ✅ Legacy auth deprecated
- ✅ V2 roadmap defined

**Acceptance Criteria:**
- <1% error rate
- User satisfaction >80%
- No rollback required

**Risk Level:** 🟢 Low (gradual rollout reduces risk)

---

### Go/No-Go Decision Points

**Week 2 Decision: Proceed to Phase 2?**

Criteria:
- [ ] All Phase 1 features functional in dev
- [ ] No critical blockers discovered
- [ ] Team velocity on track (±20%)
- [ ] Infrastructure costs within budget

**Action if NO-GO:** Re-evaluate scope, extend Phase 1 by 1 week

---

**Week 4 Decision: Proceed to Phase 3?**

Criteria:
- [ ] Staging environment stable
- [ ] Phase 2 features integrated
- [ ] Performance tests passing
- [ ] User acceptance testing positive

**Action if NO-GO:** Hold at Phase 2, defer FAQ to V2

---

**Week 6 Decision: Proceed to Production?**

Criteria:
- [ ] All features complete
- [ ] Security audit passed
- [ ] Load testing successful
- [ ] Support team trained

**Action if NO-GO:** Extend testing phase by 1 week

---

**Week 8 Decision: Proceed with Full Rollout?**

Criteria:
- [ ] 10% rollout successful (no major issues)
- [ ] User feedback positive
- [ ] Error rate <1%
- [ ] Performance stable

**Action if NO-GO:** Hold at 10%, investigate issues

---

## Success Metrics

### Technical KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| **API Response Time (P95)** | <2s | DataDog APM |
| **Error Rate** | <1% | Sentry |
| **Test Coverage** | >80% | Codecov |
| **Deployment Frequency** | 2x/week | GitHub Actions |
| **Mean Time to Recovery** | <1 hour | PagerDuty |

### Product KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| **User Adoption (Clerk SMS)** | >50% in 2 weeks | Database query |
| **Google Shopping Offers/Row** | >10 | Analytics |
| **Tile Interaction Rate** | >30% users like/comment | Analytics |
| **FAQ Completion Rate** | >70% | Analytics |
| **User Retention (30-day)** | >60% | Mixpanel |

### Business KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Clickthrough Rate** | +20% vs baseline | Analytics |
| **Affiliate Revenue** | +15% vs baseline | Affiliate dashboard |
| **User Satisfaction** | >4.0/5.0 | In-app survey |
| **Support Tickets** | <5% increase | Zendesk |

---

## Appendix

### Feature Flag Configuration

```yaml
# features.yml
features:
  clerk_sms_enabled:
    enabled: true
    rollout_percentage: 100
    rollout_strategy: "user_id"  # Hash-based

  google_shopping_enabled:
    enabled: true
    rollout_percentage: 100
    providers: ["google_shopping", "ebay", "rainforest"]

  tile_interactions_enabled:
    enabled: true
    features:
      like: true
      comment: true  # V2
      share: true    # V2

  faq_collection_enabled:
    enabled: true
    rollout_percentage: 50  # Gradual rollout
    llm_provider: "openai"
```

---

### Communication Plan

**Internal Stakeholders:**
- **Weekly Demo:** Friday 2pm - Show progress to stakeholders
- **Status Report:** Monday morning - Email update to leadership
- **Blocker Meeting:** As needed - Tech lead escalates to PM

**External Communications:**
- **User Announcement:** 1 week before launch - Email + in-app banner
- **Migration Notice:** 2 weeks before deprecation - Email to legacy auth users
- **Feature Blog Post:** At 100% rollout - Company blog + social media

---

### Rollback Procedures

**Emergency Rollback (Critical Bug):**

1. **Disable Feature Flag** (2 minutes)
   ```bash
   # In production environment
   export FEATURE_FLAG_ENABLED=false
   kubectl rollout restart deployment/frontend
   ```

2. **Database Rollback** (if needed, 15 minutes)
   ```bash
   alembic downgrade -1
   ```

3. **Notify Users** (5 minutes)
   ```
   Post banner: "We're experiencing technical difficulties.
   Some features may be temporarily unavailable."
   ```

4. **Post-Mortem** (within 24 hours)
   - Root cause analysis
   - Action items to prevent recurrence
   - Update runbook

---

## Summary

This comprehensive roadmap provides:

✅ **Clear Dependency Analysis**: Layout refactor already complete, 3 parallel streams for Phase 1
✅ **Phased Implementation**: 5 phases over 12 weeks with clear milestones
✅ **Parallel Work Streams**: 4 independent teams working simultaneously
✅ **MVP Prioritization**: Core features in 8 weeks, enhancements in V2
✅ **Risk Mitigation**: Risk assessment for each phase with mitigation strategies
✅ **Testing Strategy**: 70/20/10 unit/integration/E2E with clear coverage targets
✅ **Integration Points**: Clear mapping of feature dependencies and shared components
✅ **Resource Plan**: 5.25 FTE developers + 1.25 FTE support, $390K budget
✅ **Timeline**: 8 weeks to MVP, 12 weeks to full rollout with V2 roadmap

**Next Steps:**
1. Review and approve roadmap with stakeholders
2. Assign team members to work streams
3. Set up project board with all tasks
4. Schedule kick-off meeting
5. Begin Phase 0 (infrastructure setup)

---

**Document Maintained By:** Architecture Team
**Last Updated:** 2026-01-20
**Next Review:** End of Phase 1 (Week 2)
