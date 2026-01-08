---
allowed-tools: "*"
description: Comprehensive validation — if this passes, manual testing is unnecessary
---
allowed-tools: "*"

# Validation Workflow

**Philosophy**: If `/validation` passes, the app works. Period.

> This validation is SO thorough that manual testing becomes unnecessary.
> Every user workflow, every API endpoint, every edge case — validated.
>
> **Framework-agnostic**: Works with any language, auth provider, architecture, or deployment target.

---
allowed-tools: "*"

## Step 1: Discover Environment
// turbo

### 1.1: Detect Stack (Auto-Discovery)

**Languages** — Check for:
| Indicator | Language |
|---
allowed-tools: "*"--------|----------|
| `tsconfig.json`, `package.json` | TypeScript/JavaScript |
| `pyproject.toml`, `requirements.txt`, `setup.py` | Python |
| `go.mod`, `go.sum` | Go |
| `Cargo.toml` | Rust |
| `CMakeLists.txt`, `*.cpp`, `*.hpp` | C++ |
| `pom.xml`, `build.gradle` | Java/Kotlin |
| `mix.exs` | Elixir |
| `Gemfile` | Ruby |

**Test Runners** — Detect and use:
| Indicator | Runner | Command |
|---
allowed-tools: "*"--------|--------|---------|
| `jest.config.*`, `vitest.config.*` | Jest/Vitest | `npm test` |
| `pytest.ini`, `conftest.py` | pytest | `pytest` |
| `go.mod` + `*_test.go` | go test | `go test ./...` |
| `Cargo.toml` | cargo test | `cargo test` |
| `*.spec.rb` | RSpec | `bundle exec rspec` |
| `mix.exs` | ExUnit | `mix test` |

**Architecture** — Identify:
| Pattern | Indicators |
|---
allowed-tools: "*"------|------------|
| Monorepo | `pnpm-workspace.yaml`, `lerna.json`, `nx.json`, `turbo.json`, multiple `package.json` |
| Microservices | Multiple `Dockerfile`s, `docker-compose.yml` with many services, `/services/` dir |
| Monolith | Single app entry point, unified config |
| Hybrid | Mix of above |

**Auth Provider** — Detect (don't assume):
| Indicator | Provider |
|---
allowed-tools: "*"--------|----------|
| `@clerk/nextjs`, `@clerk/*` | Clerk |
| `stytch`, `@stytch/nextjs` | Stytch |
| `next-auth`, `@auth/*` | NextAuth/Auth.js |
| `passport`, `passport-*` | Passport.js |
| `firebase-admin`, `firebase/auth` | Firebase Auth |
| `@supabase/auth-helpers` | Supabase Auth |
| `oauth2`, `authlib` | Generic OAuth |
| Custom `auth/`, `middleware` | Custom auth |

**Database** — Detect:
| Indicator | Database |
|---
allowed-tools: "*"--------|----------|
| `pg`, `postgres`, `@prisma/client` + postgres | PostgreSQL |
| `mysql`, `mysql2` | MySQL |
| `mongodb`, `mongoose` | MongoDB |
| `neo4j-driver`, `neo4j` | Neo4j |
| `redis`, `ioredis` | Redis |
| `better-sqlite3`, `sqlite3` | SQLite |
| `@prisma/client`, `prisma/schema.prisma` | Prisma (check schema for DB) |
| `drizzle-orm` | Drizzle (check config for DB) |
| `typeorm` | TypeORM (check config for DB) |

### 1.2: Read Documentation for User Workflows

Before analyzing code, understand how users ACTUALLY use the app:

1. **Read workflow docs**:
   - `README.md` — "Usage", "Quickstart", "Examples"
   - `CLAUDE.md` / `AGENTS.md` — AI workflow patterns
   - `docs/` — User guides, tutorials

2. **Extract user journeys**:
   - "User registers → verifies email → logs in → creates item"
   - Each documented workflow = an E2E test scenario

3. **Identify external integrations**:
   - CLIs: `gh`, `gcloud`, `aws`, `railway`, `fly`, etc.
   - APIs: Stripe, Twilio, SendGrid, etc.
   - Check `Dockerfile` for installed tools

### 1.3: Map Entry Points
// turbo

1. **API routes**: REST, GraphQL, gRPC, tRPC
2. **CLI commands**: If app has CLI interface
3. **Webhook handlers**: Incoming webhooks
4. **Background jobs**: Cron, queues, workers
5. **Database**: Schema, migrations, models

### 1.4: Handle Architecture-Specific Validation

**Monorepo** (pnpm workspaces, Nx, Turborepo, Lerna):
```bash
# Run validation for each package/app
pnpm -r run test          # All packages
pnpm --filter=app test    # Specific app
turbo run test            # Turborepo
nx run-many -t test       # Nx
```

**Microservices** (multiple services):
```bash
# Start all services
docker compose up -d

# Validate each service independently
for service in api worker gateway; do
  docker compose exec $service npm test
done

# Then run cross-service integration tests
npm run test:integration
```

**Hybrid/Polyglot** (multiple languages):
```bash
# Run validation per language
cd backend && pytest           # Python backend
cd ../frontend && npm test     # JS frontend
cd ../ml-service && cargo test # Rust ML service
```

**Cloud-Native** (K8s, serverless):
```bash
# Local: Use Docker Compose or local emulators
# CI: Use test clusters or ephemeral environments
# Validate: Ensure all functions/pods respond correctly
```

---
allowed-tools: "*"

## Step 2: Identify Gaps
// turbo

Compare documented workflows against existing tests:

1. **Untested API endpoints**: Routes with no test coverage
2. **Untested user journeys**: Workflows from docs not covered by E2E
3. **Untested integrations**: External services not mocked or tested
4. **Missing edge cases**: Error handling, validation, permissions

If coverage is adequate:
```
✅ Coverage adequate — proceeding to execution
```

---
allowed-tools: "*"

## Step 3: Generate Missing Tests (Only If Needed)
// turbo

For each gap, create appropriate test using the **detected test framework**.

### Unit Tests (adapt to language)

**JavaScript/TypeScript (Jest/Vitest):**
```typescript
describe('[Function]', () => {
  it('handles valid input', () => { /* happy path */ });
  it('handles empty/null', () => { /* edge case */ });
  it('throws on invalid', () => { /* error case */ });
});
```

**Python (pytest):**
```python
def test_function_valid_input():
    """Happy path"""
    
def test_function_empty_input():
    """Edge case"""
    
def test_function_invalid_raises():
    """Error case"""
```

**Go:**
```go
func TestFunction(t *testing.T) {
    t.Run("valid input", func(t *testing.T) { /* happy path */ })
    t.Run("empty input", func(t *testing.T) { /* edge case */ })
    t.Run("invalid input", func(t *testing.T) { /* error case */ })
}
```

**Rust:**
```rust
#[cfg(test)]
mod tests {
    #[test]
    fn test_valid_input() { /* happy path */ }
    #[test]
    fn test_empty_input() { /* edge case */ }
    #[test]
    #[should_panic]
    fn test_invalid_input() { /* error case */ }
}
```

### API Tests (language-agnostic pattern)

Test every endpoint for:
- ✅ 200: Expected success response
- ❌ 400: Input validation
- 🔐 401: Auth required
- 🚫 403: Permission denied
- ❓ 404: Not found

### E2E Tests (use detected browser automation)

| Tool | When to use |
|---
allowed-tools: "*"---|-------------|
| Playwright | JS/TS projects, cross-browser |
| Cypress | JS/TS projects, component testing |
| Selenium | Multi-language, legacy |
| pytest + requests | Python API-only |
| curl/httpie scripts | Any language, simple APIs |

---
allowed-tools: "*"

## Step 4: Execute Validation
// turbo

### 4.1: Static Analysis (use detected tools)
// turbo

**Type Checking** — Run what exists:
| Language | Command |
|---
allowed-tools: "*"-------|---------|
| TypeScript | `npx tsc --noEmit` |
| Python | `mypy .` or `pyright` |
| Go | `go vet ./...` |
| Rust | `cargo check` |
| C++ | Compiler warnings |

**Linting** — Run what exists:
| Language | Command |
|---
allowed-tools: "*"-------|---------|
| JS/TS | `npm run lint` or `eslint .` |
| Python | `ruff check .` or `pylint` |
| Go | `golangci-lint run` |
| Rust | `cargo clippy` |

**Security** — Run what exists:
| Language | Command |
|---
allowed-tools: "*"-------|---------|
| JS/TS | `npm audit` or `pnpm audit` |
| Python | `pip-audit` or `safety check` |
| Go | `govulncheck ./...` |
| Rust | `cargo audit` |
| Any | `trivy fs .` or `snyk test` |

**If blocking errors**: Stop and report.

### 4.2: Unit Tests (use detected runner)
// turbo

Run the project's test command:
```bash
# Detect and run (examples)
npm test              # JS/TS
pytest                # Python
go test ./...         # Go
cargo test            # Rust
mix test              # Elixir
bundle exec rspec     # Ruby
```

### 4.3: Integration Tests
// turbo

```bash
# Start services (if docker-compose/compose.yaml exists)
docker compose up -d

# Wait for health (adapt port to project)
timeout 60 bash -c 'until curl -sf http://localhost:${PORT:-3000}/health; do sleep 2; done'

# Run integration tests (use project's command)
npm run test:integration  # or pytest tests/integration, etc.
```

### 4.4: E2E Tests (BE COMPREHENSIVE)
// turbo

**Three levels of E2E testing:**

1. **Internal APIs** (basic):
   - Test all API endpoints respond correctly
   - Verify CRUD operations work

2. **External Integrations** (important):
   ```bash
   # Test CLI integrations
   gh auth status  # GitHub CLI works
   # Test API integrations (with test accounts)
   curl -X POST $WEBHOOK_URL -d '{"test": true}'
   ```

3. **Complete User Journeys** (critical):
   - Follow workflows from docs start-to-finish
   - Test like a real user in production
   ```bash
   npx playwright test
   ```

#### Handling Auth & Protected Routes (Provider-Agnostic)

The pattern is the same regardless of auth provider (Clerk, Stytch, NextAuth, custom, etc.):

**Option A: Saved Session State (Recommended for local)**

1. Log in once (manually or via test account)
2. Save session/cookies to file
3. Reuse in all tests

```bash
# Playwright example (adapt to your E2E tool)
# 1. Create auth.setup that logs in and saves state
# 2. Configure tests to load saved state before running
# 3. Add saved state file to .gitignore
```

**Option B: Test Mode Bypass (Recommended for CI)**

Add test-only auth bypass to your app:
```
# Environment variables
TEST_MODE=true
TEST_USER_ID=test-user-123
TEST_USER_ROLE=admin
```

Your auth middleware checks these and injects a test session.
Works with ANY auth provider because you're bypassing it entirely.

**Option C: Provider-Specific Test Tokens**

Some providers offer test modes:
| Provider | Test Mode |
|---
allowed-tools: "*"-------|-----------|
| Clerk | Test instance + test users |
| Stytch | Test project + test magic links |
| Stripe | Test API keys |
| Firebase | Emulator suite |
| Supabase | Local dev instance |

**Option D: Direct API Auth (if supported)**

If your app supports email/password or API keys:
```bash
# Get auth token via API
TOKEN=$(curl -X POST /api/auth/login -d '{"email":"test@test.com","password":"..."}' | jq -r '.token')

# Use token in subsequent requests
curl -H "Authorization: Bearer $TOKEN" /api/protected
```

**Which to use:**
| Environment | Recommended |
|---
allowed-tools: "*"----------|-------------|
| Local dev | Option A (saved state) |
| CI/CD | Option B (test bypass) or D (API auth) |
| Production-like | Option C (provider test mode) |

### 4.5: Database Verification (adapt to your DB)
// turbo

Verify data integrity after tests:

| Database | Verification Command |
|---
allowed-tools: "*"-------|---------------------|
| PostgreSQL | `docker exec postgres psql -U user -d db -c "SELECT COUNT(*) FROM users;"` |
| MySQL | `docker exec mysql mysql -u user -p -e "SELECT COUNT(*) FROM users;"` |
| MongoDB | `docker exec mongo mongosh --eval "db.users.countDocuments()"` |
| Neo4j | `docker exec neo4j cypher-shell -u neo4j -p password "MATCH (n:User) RETURN count(n)"` |
| Redis | `docker exec redis redis-cli DBSIZE` |
| SQLite | `sqlite3 db.sqlite "SELECT COUNT(*) FROM users;"` |

Check for:
- Orphaned records
- Constraint violations
- Expected row counts after test operations
- Test data cleanup

### 4.6: Cleanup
// turbo
```bash
# Stop and remove test containers
docker compose down -v

# Clean test artifacts
rm -rf coverage/ .nyc_output/ test-results/
```

---
allowed-tools: "*"

## Step 5: Report Results

```
🏁 VALIDATION COMPLETE

📊 STATUS: [✅ PASSED / ❌ FAILED]

[If tests generated:]
🧪 New tests: [N] files

📈 Results:
┌─────────────────┬────────┬─────────┐
│ Phase           │ Status │ Details │
├─────────────────┼────────┼─────────┤
│ Static Analysis │ ✅/❌  │ [n] issues │
│ Unit Tests      │ ✅/❌  │ [n]/[n] passed │
│ Integration     │ ✅/❌  │ [n]/[n] passed │
│ E2E Journeys    │ ✅/❌  │ [n]/[n] passed │
│ External APIs   │ ✅/❌  │ [n] verified │
│ Database        │ ✅/❌  │ integrity ok │
└─────────────────┴────────┴─────────┘

[If PASSED:]
✅ Ready for deployment. Manual testing unnecessary.

[If FAILED:]
❌ Fix issues and run `/validation` again.
```

---
allowed-tools: "*"

## Critical Reminders

**Don't stop until everything is validated:**
- Every user workflow from docs → tested E2E
- Every API endpoint → hit with real requests
- Every external integration → exercised
- Every error case → verified
- Database integrity → confirmed

**Good vs Bad E2E tests:**
- ❌ Bad: "Test that /api/items returns 200"
- ✅ Good: "User creates item → edits it → deletes it → verify DB is clean"
- ✅ Great: "User signs up → verifies email → logs in → creates item → shares with team → teammate sees it"
