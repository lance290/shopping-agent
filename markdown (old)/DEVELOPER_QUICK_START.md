# Developer Quick Start Guide

**Last Updated:** 2026-01-20

This guide provides immediate actionable steps for developers starting work on the Shopping Agent multi-feature implementation.

---

## Your Work Stream Assignment

### Stream A: Authentication (Clerk SMS)

**Developer:** Full-Stack Developer 1
**Duration:** Weeks 1-4, 8
**Tech Stack:** Next.js, Clerk SDK, FastAPI, PostgreSQL

**Your Tasks (Week 1):**
```
Day 1-2: Clerk Setup
  ├─ Create Clerk app at dashboard.clerk.com
  ├─ Configure SMS authentication
  ├─ Add environment variables to .env.local
  └─ Install @clerk/nextjs

Day 3-4: Frontend Integration
  ├─ Wrap app with ClerkProvider in layout.tsx
  ├─ Create custom phone login page
  ├─ Update middleware.ts
  └─ Test login flow in development

Day 5: Backend Preparation
  ├─ Add clerk_user_id column to user table
  ├─ Create clerk_auth.py module
  └─ Test JWT verification locally
```

**Key Files to Create/Modify:**
- `/apps/frontend/app/layout.tsx` - Add ClerkProvider
- `/apps/frontend/app/login/page.tsx` - Custom phone login
- `/apps/frontend/middleware.ts` - Clerk middleware
- `/apps/backend/clerk_auth.py` - JWT verification
- `/apps/backend/models.py` - Add clerk_user_id column

**Architecture Doc:** `/CLERK_SMS_MIGRATION_ARCHITECTURE.md`

**Daily Checklist:**
- [ ] Commit code at least once
- [ ] Update Jira tickets
- [ ] Attend 9:30 AM standup
- [ ] Ask for help if blocked >30 min

---

### Stream B: Google Shopping Integration

**Developer:** Backend Developer 1
**Duration:** Weeks 1-4
**Tech Stack:** Python, Google Shopping API, FastAPI, Redis

**Your Tasks (Week 1):**
```
Day 1-2: Google Cloud Setup
  ├─ Create project at console.cloud.google.com
  ├─ Enable Shopping Content API
  ├─ Generate service account key
  ├─ Set up GOOGLE_APPLICATION_CREDENTIALS
  └─ Test API connection

Day 3-4: Provider Implementation
  ├─ Create GoogleShoppingProvider class
  ├─ Implement search() method
  ├─ Map response to Offer model
  ├─ Add error handling
  └─ Write unit tests

Day 5: Integration
  ├─ Register provider in SourcingRepository
  ├─ Test with real queries
  ├─ Add caching layer
  └─ Monitor quota usage
```

**Key Files to Create/Modify:**
- `/apps/backend/sourcing/google_shopping_provider.py` - New file
- `/apps/backend/sourcing/repository.py` - Register provider
- `/apps/backend/models.py` - Ensure Offer model compatible
- `/apps/backend/tests/test_google_shopping.py` - Unit tests

**Architecture Doc:** `/docs/google-shopping-api-architecture.md`

**Daily Checklist:**
- [ ] Test API calls (watch quota)
- [ ] Check cache hit rate
- [ ] Monitor response times
- [ ] Document any API quirks

---

### Stream C: Tile Interactions

**Developers:** Frontend Developer 1 + Backend Developer 2
**Duration:** Weeks 1-4
**Tech Stack:** React, Zustand, Framer Motion, FastAPI, PostgreSQL

#### Backend Developer 2 (Week 1-2)

**Your Tasks (Week 1):**
```
Day 1-2: Database Design
  ├─ Review TILE_INTERACTION_ARCHITECTURE.md
  ├─ Create Alembic migration
  ├─ Add tile_like, tile_comment, tile_share tables
  ├─ Add engagement columns to bid table
  └─ Test migration on local DB

Day 3-4: API Endpoints
  ├─ POST /api/tiles/:bidId/like
  ├─ DELETE /api/tiles/:bidId/like
  ├─ POST /api/tiles/:bidId/comments
  ├─ GET /api/tiles/:bidId/comments
  ├─ POST /api/tiles/:bidId/share
  └─ GET /api/rows/:rowId/tiles/engagement

Day 5: Testing
  ├─ Write Pytest tests for each endpoint
  ├─ Test optimistic locking
  ├─ Load test with 100 concurrent likes
  └─ Document API in Swagger
```

**Key Files to Create/Modify:**
- `/apps/backend/alembic/versions/XXX_tile_interactions.py` - Migration
- `/apps/backend/models.py` - Add TileLike, TileComment, TileShare
- `/apps/backend/main.py` - Add tile endpoints
- `/apps/backend/tests/test_tile_interactions.py` - Tests

#### Frontend Developer 1 (Week 3-4)

**Your Tasks (Week 3):**
```
Day 1-2: Core Components
  ├─ Create TileActions.tsx component
  ├─ Implement LikeButton with heart icon
  ├─ Add CommentButton (opens panel)
  ├─ Add ShareButton (opens popover)
  └─ Style with Tailwind

Day 3-4: Comment Panel
  ├─ Create CommentPanel.tsx (slide-in)
  ├─ Create CommentItem.tsx (individual comment)
  ├─ Add comment input with validation
  ├─ Implement threaded replies
  └─ Add smooth animations

Day 5: Integration
  ├─ Add TileActions to OfferTile.tsx
  ├─ Connect to Zustand state
  ├─ Test optimistic updates
  └─ Handle error states
```

**Your Tasks (Week 4):**
```
Day 1-2: Animations
  ├─ Install framer-motion
  ├─ Implement tile reordering on like
  ├─ Add stagger effect
  ├─ Test on slow devices
  └─ Add reduced-motion support

Day 3: State Management
  ├─ Update store.ts with engagement state
  ├─ Add toggleTileLike action
  ├─ Add loadComments action
  ├─ Add bulkLoadEngagement
  └─ Test optimistic rollback

Day 4-5: Polish
  ├─ Add loading skeletons
  ├─ Improve error messages
  ├─ Accessibility audit (keyboard nav)
  └─ Cross-browser testing
```

**Key Files to Create/Modify:**
- `/apps/frontend/app/components/TileActions.tsx` - New component
- `/apps/frontend/app/components/CommentPanel.tsx` - New component
- `/apps/frontend/app/components/OfferTile.tsx` - Add TileActions
- `/apps/frontend/app/store.ts` - Add engagement state
- `/apps/frontend/package.json` - Add framer-motion

**Architecture Doc:** `/TILE_INTERACTION_ARCHITECTURE.md`

**Daily Checklist:**
- [ ] Test animations on real devices
- [ ] Check accessibility (screen reader)
- [ ] Verify mobile responsive
- [ ] Update Storybook stories

---

### Stream D: FAQ Collection

**Developer:** Full-Stack Developer 2
**Duration:** Weeks 5-6
**Tech Stack:** Next.js, OpenAI API, FastAPI, LangChain

**Your Tasks (Week 5):**
```
Day 1-2: Conversation Design
  ├─ Design question flow diagram
  ├─ Write LLM prompt templates
  ├─ Test question quality with GPT-4
  ├─ Define answer validation rules
  └─ Create FAQ state machine

Day 3-4: Backend Integration
  ├─ Create /api/faq/start endpoint
  ├─ Create /api/faq/answer endpoint
  ├─ Integrate OpenAI API
  ├─ Add context from Google Shopping
  └─ Save answers to row.choice_answers

Day 5: Testing
  ├─ Test with various product types
  ├─ Ensure questions are relevant
  ├─ Test answer parsing
  └─ Handle edge cases (invalid answers)
```

**Your Tasks (Week 6):**
```
Day 1-2: Frontend Integration
  ├─ Update Chat component with FAQ mode
  ├─ Add FAQ start button (+ icon)
  ├─ Display questions in chat
  ├─ Capture user answers
  └─ Show progress indicator

Day 3: RequestTile Integration
  ├─ Update RequestTile to show FAQ answers
  ├─ Add edit button to restart FAQ
  ├─ Format answers for display
  └─ Handle empty state

Day 4-5: Testing & Polish
  ├─ User acceptance testing
  ├─ Measure completion rate
  ├─ Fix UX issues
  └─ Document conversation flows
```

**Key Files to Create/Modify:**
- `/apps/backend/faq/conversation.py` - New module
- `/apps/backend/faq/prompts.py` - LLM templates
- `/apps/backend/main.py` - Add FAQ endpoints
- `/apps/frontend/app/components/Chat.tsx` - Add FAQ mode
- `/apps/frontend/app/components/RequestTile.tsx` - Display answers

**Prerequisites:**
- ✅ Clerk SMS (authentication for user context)
- ✅ Google Shopping (data source for contextual questions)

**Daily Checklist:**
- [ ] Test LLM outputs for quality
- [ ] Monitor OpenAI API costs
- [ ] Gather user feedback
- [ ] Iterate on question prompts

---

## Development Environment Setup

### First-Time Setup (All Developers)

```bash
# 1. Clone repository
git clone https://github.com/your-org/shopping-agent.git
cd shopping-agent

# 2. Install dependencies
cd apps/frontend && pnpm install
cd ../backend && pip install -r requirements.txt
cd ../bff && pnpm install

# 3. Set up environment variables
cp apps/frontend/.env.example apps/frontend/.env.local
cp apps/backend/.env.example apps/backend/.env
cp apps/bff/.env.example apps/bff/.env

# 4. Start database
docker-compose up -d postgres

# 5. Run migrations
cd apps/backend
alembic upgrade head

# 6. Start development servers
# Terminal 1: Frontend
cd apps/frontend && pnpm dev

# Terminal 2: Backend
cd apps/backend && uvicorn main:app --reload

# Terminal 3: BFF
cd apps/bff && pnpm dev
```

### Feature Branch Workflow

```bash
# 1. Create feature branch from develop
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name

# 2. Make changes and commit frequently
git add .
git commit -m "feat: add tile like button"

# 3. Push to remote
git push origin feature/your-feature-name

# 4. Create pull request
# Go to GitHub → New Pull Request
# Base: develop, Compare: feature/your-feature-name

# 5. After PR approved and merged
git checkout develop
git pull origin develop
git branch -d feature/your-feature-name
```

### Daily Development Routine

**Morning (9:00-12:00):**
- [ ] 9:30 AM: Attend standup
- [ ] Pull latest from `develop`
- [ ] Review Jira tickets for the day
- [ ] Focus time (no meetings)

**Afternoon (1:00-5:00):**
- [ ] Code review for teammates
- [ ] Commit progress (at least once)
- [ ] Update Jira ticket status
- [ ] 5:00 PM: End-of-day sync (optional)

**Friday:**
- [ ] 2:00 PM: Integration meeting
- [ ] 3:00 PM: Demo to stakeholders
- [ ] Merge feature branch to `develop`

---

## Testing Your Work

### Unit Tests

**Frontend (Vitest):**
```bash
cd apps/frontend
pnpm test

# Watch mode
pnpm test:watch

# Coverage
pnpm test:coverage
```

**Backend (Pytest):**
```bash
cd apps/backend
pytest

# Specific test
pytest tests/test_tile_interactions.py

# Coverage
pytest --cov=.
```

### Integration Tests

**API Testing (Postman):**
```bash
# Import collection
postman import postman_collection.json

# Run tests
newman run postman_collection.json
```

**E2E Testing (Playwright):**
```bash
cd apps/frontend
pnpm playwright test

# UI mode (great for debugging)
pnpm playwright test --ui

# Specific test
pnpm playwright test tests/login.spec.ts
```

### Manual Testing Checklist

**Before Creating PR:**
- [ ] Feature works on Chrome
- [ ] Feature works on Safari
- [ ] Feature works on mobile (iOS or Android)
- [ ] No console errors
- [ ] Accessibility: Keyboard navigation works
- [ ] Accessibility: Screen reader tested (VoiceOver/NVDA)
- [ ] Edge cases handled (empty state, error state)
- [ ] Loading states implemented

---

## Code Style & Best Practices

### Naming Conventions

**Files:**
- Components: `PascalCase.tsx` (e.g., `TileActions.tsx`)
- Utilities: `camelCase.ts` (e.g., `formatPrice.ts`)
- Hooks: `use*.ts` (e.g., `useAuth.ts`)
- API routes: `route.ts` (Next.js convention)

**Variables:**
- React components: `PascalCase`
- Functions: `camelCase`
- Constants: `UPPER_SNAKE_CASE`
- Database models: `PascalCase` (SQLModel)

**Commits:**
- Follow [Conventional Commits](https://www.conventionalcommits.org/)
- Format: `type(scope): message`
- Examples:
  - `feat(auth): add Clerk SMS login`
  - `fix(tiles): resolve like count bug`
  - `test(api): add tile interaction tests`
  - `docs(readme): update setup instructions`

### Code Review Checklist

**Before Requesting Review:**
- [ ] Code follows style guide
- [ ] Tests added/updated
- [ ] No console.log() statements
- [ ] No commented-out code
- [ ] PR description clear
- [ ] Screenshots for UI changes

**Reviewing Others' Code:**
- [ ] Understand the change
- [ ] Check for edge cases
- [ ] Verify tests are adequate
- [ ] Suggest improvements (kindly)
- [ ] Approve or request changes within 24 hours

---

## Debugging Tips

### Frontend Debugging

**React DevTools:**
```bash
# Install browser extension
# Chrome: React Developer Tools
# Firefox: React DevTools

# Inspect component props/state
# Click React icon in browser toolbar
```

**Zustand DevTools:**
```typescript
// In store.ts, add devtools middleware
import { devtools } from 'zustand/middleware';

export const useShoppingStore = create<ShoppingState>()(
  devtools(
    (set, get) => ({
      // ... state
    }),
    { name: 'ShoppingStore' }
  )
);
```

**Network Debugging:**
```bash
# Chrome DevTools → Network tab
# Filter by: Fetch/XHR
# Look for: Status code, response time, payload

# Copy as cURL to replay requests
# Right-click request → Copy → Copy as cURL
```

### Backend Debugging

**FastAPI Logging:**
```python
# Add to main.py
import logging
logging.basicConfig(level=logging.DEBUG)

# In your code
logger = logging.getLogger(__name__)
logger.debug(f"User {user.id} liked tile {bid_id}")
```

**Database Queries:**
```bash
# Connect to local database
psql postgresql://postgres:postgres@localhost:5435/shopping_agent

# View recent queries
SELECT * FROM pg_stat_activity;

# Explain query performance
EXPLAIN ANALYZE SELECT * FROM bid WHERE row_id = 123;
```

**Pdb Debugger:**
```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Commands:
# n - next line
# s - step into
# c - continue
# p variable - print variable
# q - quit
```

---

## Common Issues & Solutions

### Issue: Clerk JWT verification fails

**Symptoms:** 401 Unauthorized on API calls

**Solutions:**
1. Check `CLERK_SECRET_KEY` is set correctly
2. Ensure `CLERK_DOMAIN` matches your Clerk app
3. Verify JWKS URL is accessible
4. Check token expiration (tokens expire in 1 hour)

```bash
# Test JWT manually
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/rows
```

---

### Issue: Google Shopping quota exceeded

**Symptoms:** 429 Too Many Requests

**Solutions:**
1. Check quota in Google Cloud Console
2. Increase cache TTL (reduce API calls)
3. Use fallback provider (SerpAPI)
4. Request quota increase

```python
# In google_shopping_provider.py
CACHE_TTL = 3600  # 1 hour → increase to 86400 (24 hours)
```

---

### Issue: Tile reordering animations are janky

**Symptoms:** Slow/choppy animations on low-end devices

**Solutions:**
1. Use CSS transforms (GPU-accelerated)
2. Reduce number of animated tiles
3. Add `will-change: transform` hint
4. Test on real device, not simulator

```css
/* In OfferTile.tsx */
.tile-reorder {
  will-change: transform;
  transform: translateZ(0); /* Force GPU layer */
}
```

---

### Issue: Database migration fails

**Symptoms:** `alembic upgrade head` errors

**Solutions:**
1. Check current revision: `alembic current`
2. View migration history: `alembic history`
3. Rollback one step: `alembic downgrade -1`
4. Fix migration file, try again
5. If stuck, drop local DB and start fresh (dev only!)

```bash
# Nuclear option (local dev only!)
docker-compose down -v
docker-compose up -d postgres
alembic upgrade head
```

---

## Performance Optimization

### Frontend Performance

**Lazy Loading:**
```typescript
// In page.tsx
import dynamic from 'next/dynamic';

const CommentPanel = dynamic(() => import('./CommentPanel'), {
  loading: () => <p>Loading...</p>,
});
```

**Memoization:**
```typescript
// In OfferTile.tsx
import { useMemo } from 'react';

const sortedOffers = useMemo(() => {
  return offers.sort((a, b) => b.like_count - a.like_count);
}, [offers]);
```

**Virtual Scrolling:**
```bash
# For large lists (50+ items)
pnpm add @tanstack/react-virtual
```

### Backend Performance

**Database Indexes:**
```sql
-- Already in migration, but verify:
CREATE INDEX idx_bid_row_engagement ON bid(row_id, like_count DESC);
CREATE INDEX idx_tile_like_bid ON tile_like(bid_id);
```

**Caching:**
```python
# In google_shopping_provider.py
from functools import lru_cache

@lru_cache(maxsize=1000)
def search_cached(query: str) -> List[Offer]:
    return self.search(query)
```

**Batch Queries:**
```python
# Instead of N+1 queries
for bid_id in bid_ids:
    engagement = get_engagement(bid_id)  # Bad!

# Use bulk query
engagements = get_bulk_engagement(bid_ids)  # Good!
```

---

## Security Checklist

**Before Deploying to Production:**

- [ ] No secrets in code (use environment variables)
- [ ] All API endpoints require authentication
- [ ] Input validation on all user inputs
- [ ] SQL injection prevention (use parameterized queries)
- [ ] XSS prevention (sanitize HTML)
- [ ] CSRF protection enabled
- [ ] Rate limiting configured
- [ ] HTTPS enforced
- [ ] Dependencies updated (no known vulnerabilities)

**Tools:**
```bash
# Check for secrets
git secrets --scan

# Check for vulnerabilities
pnpm audit
pip-audit

# Security linting
eslint --plugin security
bandit -r apps/backend
```

---

## Communication

### Slack Channels

- `#shopping-agent-dev` - General development chat
- `#stream-auth` - Clerk SMS team
- `#stream-shopping` - Google Shopping team
- `#stream-social` - Tile interactions team
- `#stream-chat` - FAQ collection team
- `#shopping-agent-critical` - P0/P1 incidents only

### When to Ask for Help

**Immediately (Slack or call):**
- Production is down
- Security vulnerability discovered
- Blocked on critical task for >1 hour

**Within 30 minutes (Slack):**
- Unclear requirements
- Technical decision needed
- Integration issue with another stream

**Next standup (wait until meeting):**
- General questions
- Feature ideas
- Process improvements

### Status Updates

**Green (on track):**
- Making progress, no blockers
- Emoji: ✅

**Yellow (needs attention):**
- Minor blocker, can work around
- May need help soon
- Emoji: ⚠️

**Red (blocked):**
- Critical blocker, cannot proceed
- Need help ASAP
- Emoji: 🚨

**Format:**
```
Stream: Auth
Status: ✅
Progress: Clerk setup complete, working on frontend integration
Blockers: None
ETA: On track for Friday
```

---

## Resources

### Documentation

- **Architecture Docs:** `/docs/` folder
- **API Docs:** `http://localhost:8000/docs` (Swagger)
- **Component Storybook:** `pnpm storybook`
- **Database Schema:** `alembic current` + `/docs/database.md`

### External Resources

- **Clerk Docs:** https://clerk.com/docs
- **Google Shopping API:** https://developers.google.com/shopping-content/guides/quickstart
- **Next.js Docs:** https://nextjs.org/docs
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **Zustand Docs:** https://zustand-demo.pmnd.rs
- **Framer Motion:** https://www.framer.com/motion

### Learning Resources

- **Clerk SMS Tutorial:** https://clerk.com/docs/authentication/phone-number
- **Google Shopping Samples:** https://github.com/googleads/shopping-samples
- **Framer Motion Animations:** https://www.framer.com/motion/animation
- **FastAPI Async:** https://fastapi.tiangolo.com/async

---

## Emergency Contacts

**On-Call Rotation:**
- View schedule: https://pagerduty.com/schedules
- Escalate: Text on-call number or page via PagerDuty

**Tech Lead:**
- Slack: @tech-lead
- Email: tech-lead@company.com
- Phone: [Redacted]

**DevOps:**
- Slack: @devops-team
- Email: devops@company.com
- PagerDuty: Auto-escalates after 15 min

**Support:**
- During business hours: `#help-desk`
- After hours: support@company.com

---

## Glossary

**Auth:** Authentication system (Clerk SMS)
**BFF:** Backend-for-Frontend (Fastify proxy)
**Bid:** An offer from a seller/merchant
**Clerk:** Third-party authentication service
**E2E:** End-to-end testing
**FAQ:** Frequently Asked Questions (our interactive chat feature)
**FTE:** Full-Time Equivalent
**JWT:** JSON Web Token (authentication token format)
**LLM:** Large Language Model (GPT-4, etc.)
**MVP:** Minimum Viable Product
**Offer:** Product result from search provider
**PR:** Pull Request
**RequestTile:** First tile in row showing purchase requirements
**Row:** A single purchase request with multiple offers
**UAT:** User Acceptance Testing
**V2:** Version 2 (post-MVP features)

---

**Good luck! Remember: Ask questions, commit often, and ship small PRs. You've got this!** 🚀
