# Authentication & User Management Setup

The framework does not mandate a single auth provider, but your MVP will likely need one. This guide covers setup for all major providers with framework-specific guidance.

## Quick Comparison

| Provider | Best For | Multi-Framework | User Management UI | Pricing |
|----------|----------|-----------------|-------------------|---------|
| **Clerk** | Multi-framework, ease of use | ✅ Excellent | ✅ Built-in | Free tier, then $25/mo |
| **Stytch** | Passwordless, B2B | ✅ Good | ✅ Built-in | Free tier, then usage-based |
| **Auth0** | Enterprise, SAML/SSO | ✅ Excellent | ✅ Built-in | Free tier, then $23/mo |
| **Supabase** | Open source, PostgreSQL | ✅ Good | ⚠️ Basic | Free tier, then $25/mo |
| **NextAuth** | Next.js, self-hosted | ⚠️ Next.js/SvelteKit | ❌ DIY | Free (self-hosted) |
| **Lucia** | SvelteKit, full control | ⚠️ SvelteKit-focused | ❌ DIY | Free (library) |
| **Firebase** | Google ecosystem | ✅ Good | ⚠️ Basic | Free tier, then usage-based |

---

## Option A: Firebase Authentication

1. Go to <https://console.firebase.google.com/>.
2. Create a project (or link your GCP project).
3. Enable Email/Password or OAuth providers under **Authentication → Sign-in method**.
4. Generate a service account key (**Project Settings → Service Accounts**).
5. Populate `.env`:

```bash
FIREBASE_PROJECT_ID=your-firebase-project
FIREBASE_CLIENT_EMAIL=service-account@project.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
```

Install the admin SDK:

```bash
npm install firebase-admin
```

---

## Option B: Auth0

1. Sign in at <https://manage.auth0.com/>.
2. Create a new **Regular Web Application**.
3. Note the **Domain**, **Client ID**, and **Client Secret**.
4. Add callback URLs for local development and production.
5. `.env` entries:

```bash
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_CLIENT_ID=client-id
AUTH0_CLIENT_SECRET=client-secret
AUTH0_AUDIENCE=https://api.yourdomain.com
```

Install dependencies:

```bash
npm install express-oauth2-jwt-bearer jsonwebtoken
```

---

## Option C: Clerk

1. Visit <https://dashboard.clerk.com/>.
2. Create an application and enable Email/Password + OAuth providers.
3. Copy the **Publishable key** and **Secret key**.
4. `.env` variables:

```bash
CLERK_PUBLISHABLE_KEY=pk_live_xxx
CLERK_SECRET_KEY=sk_live_xxx
```

Install:

```bash
npm install @clerk/clerk-sdk-node
```

---

## Option D: Supabase Auth

1. Log in to <https://app.supabase.com/>.
2. Create a project and enable the **Auth** features you need.
3. Under **Project Settings → API**, copy the **URL**, **anon key**, and **service role key**.
4. `.env`:

```bash
SUPABASE_URL=https://xyzcompany.supabase.co
SUPABASE_ANON_KEY=public-anon-key
SUPABASE_SERVICE_KEY=service-role-key
```

Install:

```bash
npm install @supabase/supabase-js
```

---

## Option E: Stytch

1. Sign up at <https://stytch.com/>.
2. Create a project and enable authentication methods (email magic links, SMS, OAuth).
3. Copy **Project ID**, **Secret**, and **Public Token**.
4. `.env`:

```bash
STYTCH_PROJECT_ID=project-live-xxx
STYTCH_SECRET=secret-live-xxx
STYTCH_PUBLIC_TOKEN=public-token-live-xxx
```

Install:

```bash
npm install stytch
```

---

## Option F: NextAuth.js (Auth.js)

**Best for:** Next.js (native), SvelteKit (with adapter)

### Next.js Setup

1. Install:

```bash
npm install next-auth
```

2. Create `app/api/auth/[...nextauth]/route.ts`:

```typescript
import NextAuth from "next-auth"
import GoogleProvider from "next-auth/providers/google"

export const authOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
}

const handler = NextAuth(authOptions)
export { handler as GET, handler as POST }
```

3. `.env`:

```bash
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-key
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### SvelteKit Setup

1. Install:

```bash
npm install @auth/core @auth/sveltekit
```

2. Create `src/hooks.server.ts`:

```typescript
import { SvelteKitAuth } from "@auth/sveltekit"
import Google from "@auth/sveltekit/providers/google"

export const handle = SvelteKitAuth({
  providers: [Google],
})
```

---

## Option G: Lucia Auth

**Best for:** SvelteKit (native), full control over auth logic

1. Install:

```bash
npm install lucia @lucia-auth/adapter-postgresql
```

2. Initialize Lucia:

```typescript
import { lucia } from "lucia"
import { postgres as postgresAdapter } from "@lucia-auth/adapter-postgresql"

export const auth = lucia({
  adapter: postgresAdapter(pool),
  env: "DEV", // "PROD" in production
})
```

3. Create auth tables in PostgreSQL (see Lucia docs for schema)

---

## Framework-Specific Recommendations

### Next.js
- ✅ **Best:** NextAuth.js (native integration)
- ✅ **Alternative:** Clerk (drop-in components)
- ⚠️ **Avoid:** Custom JWT (reinventing the wheel)

### SvelteKit
- ✅ **Best:** Clerk (official SDK) or Lucia (native, full control)
- ⚠️ **OK:** NextAuth via `@auth/sveltekit` (requires adapter)
- ⚠️ **Avoid:** NextAuth without adapter (not compatible)

### Remix
- ✅ **Best:** Clerk or Auth0 (official SDKs)
- ⚠️ **OK:** `remix-auth` (community library)
- ⚠️ **Avoid:** NextAuth (not compatible)

### Vue
- ✅ **Best:** Clerk, Auth0, or Supabase (official SDKs)
- ❌ **Avoid:** NextAuth (no Vue support)

### React Native / Expo
- ✅ **Best:** Clerk (official SDK with components)
- ✅ **Alternative:** Supabase (good mobile support)
- ⚠️ **OK:** Auth0 (requires custom UI)

---

## Compliance Considerations

### SOC 2 / HIPAA
**Required features:**
- Audit logging (who logged in, when, from where)
- MFA enforcement
- Session management (timeouts, revocation)
- Password policies

**Recommended providers:**
- ✅ Clerk (audit logs built-in)
- ✅ Auth0 (enterprise audit logs)
- ✅ Supabase (PostgreSQL audit triggers)

### PCI DSS
**If handling payments:**
- ✅ Use Clerk, Auth0, or Stytch (PCI-compliant infrastructure)
- ⚠️ Self-hosted auth requires PCI compliance audit

### GDPR
**Required features:**
- User data export
- Right to deletion
- Consent management

**All providers support GDPR**, but verify data residency requirements.

---

## Security Checklist

- [ ] Store secrets using the process in [`SECRETS_MANAGEMENT.md`](./SECRETS_MANAGEMENT.md).
- [ ] Rotate credentials periodically.
- [ ] Enforce HTTPS-only callbacks once deployed.
- [ ] Enable MFA for admin accounts.
- [ ] Implement session timeouts (15-30 minutes for sensitive apps).
- [ ] Log all authentication events (success and failures).
- [ ] Add automated tests for auth-critical flows (`/implement` Step 5).
- [ ] Review provider's compliance certifications (SOC 2, HIPAA, etc.).

Record the chosen provider in `.cfoi/branches/<branch>/DECISIONS.md` so future
maintainers understand why it was selected and how to manage it.

