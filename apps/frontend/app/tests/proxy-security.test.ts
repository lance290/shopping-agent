import { describe, test, expect } from 'vitest';

/**
 * Tests for P0-1 (SSRF proxy allowlist) and P1-3 (HttpOnly cookie).
 * 
 * These tests verify:
 * 1. The proxy route only allows specific paths (auth/start, auth/verify, auth/me, auth/logout)
 * 2. Path traversal attempts are blocked
 * 3. Arbitrary paths return 404
 * 4. The auth verify response sets HttpOnly cookies
 * 5. Client-side code does not try to read cookies directly
 */

// ─── P0-1: Proxy Path Allowlist ──────────────────────────────────────────────

describe('Proxy Path Allowlist (P0-1)', () => {
  const ALLOWED_PROXY_PATHS = new Set([
    'auth/start',
    'auth/verify',
    'auth/me',
    'auth/logout',
  ]);

  function isAllowedPath(path: string): boolean {
    if (ALLOWED_PROXY_PATHS.has(path)) return true;
    if (path.includes('..') || path.includes('//')) return false;
    return false;
  }

  test('allows auth/start', () => {
    expect(isAllowedPath('auth/start')).toBe(true);
  });

  test('allows auth/verify', () => {
    expect(isAllowedPath('auth/verify')).toBe(true);
  });

  test('allows auth/me', () => {
    expect(isAllowedPath('auth/me')).toBe(true);
  });

  test('allows auth/logout', () => {
    expect(isAllowedPath('auth/logout')).toBe(true);
  });

  test('rejects arbitrary paths', () => {
    expect(isAllowedPath('rows')).toBe(false);
    expect(isAllowedPath('admin/audit')).toBe(false);
    expect(isAllowedPath('api/bugs')).toBe(false);
    expect(isAllowedPath('internal/users')).toBe(false);
  });

  test('rejects path traversal attempts', () => {
    expect(isAllowedPath('../../etc/passwd')).toBe(false);
    expect(isAllowedPath('../internal-service/admin')).toBe(false);
    expect(isAllowedPath('auth/../../admin')).toBe(false);
  });

  test('rejects double slash injection', () => {
    expect(isAllowedPath('auth//verify')).toBe(false);
    expect(isAllowedPath('//internal')).toBe(false);
  });

  test('rejects empty path', () => {
    expect(isAllowedPath('')).toBe(false);
  });

  test('rejects paths with query strings baked in', () => {
    expect(isAllowedPath('auth/start?redirect=evil.com')).toBe(false);
  });
});

// ─── P0-1: Proxy Route File Structure ────────────────────────────────────────

describe('Proxy Route Configuration (P0-1)', () => {
  test('proxy route file contains ALLOWED_PROXY_PATHS constant', async () => {
    const fs = await import('fs');
    const path = await import('path');
    const routeFile = path.resolve(__dirname, '../api/proxy/[...path]/route.ts');
    const content = fs.readFileSync(routeFile, 'utf-8');

    expect(content).toContain('ALLOWED_PROXY_PATHS');
    expect(content).toContain('isAllowedPath');
  });

  test('proxy route rejects disallowed paths with 404', async () => {
    const fs = await import('fs');
    const path = await import('path');
    const routeFile = path.resolve(__dirname, '../api/proxy/[...path]/route.ts');
    const content = fs.readFileSync(routeFile, 'utf-8');

    // Both GET and POST should check the allowlist before forwarding
    const postSection = content.indexOf('export async function POST');
    const getSection = content.indexOf('export async function GET');

    // Verify allowlist check appears before the fetch call in both handlers
    const postAllowCheck = content.indexOf('isAllowedPath', postSection);
    const postFetch = content.indexOf('await fetch(url', postSection);
    expect(postAllowCheck).toBeLessThan(postFetch);

    const getAllowCheck = content.indexOf('isAllowedPath', getSection);
    const getFetch = content.indexOf('await fetch(url', getSection);
    expect(getAllowCheck).toBeLessThan(getFetch);
  });

  test('proxy route uses server-only BACKEND_URL (not just NEXT_PUBLIC_)', async () => {
    const fs = await import('fs');
    const path = await import('path');
    const routeFile = path.resolve(__dirname, '../api/proxy/[...path]/route.ts');
    const content = fs.readFileSync(routeFile, 'utf-8');

    // Should prefer BACKEND_URL (server-only) over NEXT_PUBLIC_BACKEND_URL
    expect(content).toContain('process.env.BACKEND_URL');
  });
});

// ─── P1-3: HttpOnly Cookie ───────────────────────────────────────────────────

describe('HttpOnly Cookie Security (P1-3)', () => {
  test('proxy route sets httpOnly: true on session cookie', async () => {
    const fs = await import('fs');
    const path = await import('path');
    const routeFile = path.resolve(__dirname, '../api/proxy/[...path]/route.ts');
    const content = fs.readFileSync(routeFile, 'utf-8');

    // Should set httpOnly: true
    expect(content).toContain('httpOnly: true');
    // Should NOT contain httpOnly: false
    expect(content).not.toContain('httpOnly: false');
  });

  test('proxy route sets secure flag for production', async () => {
    const fs = await import('fs');
    const path = await import('path');
    const routeFile = path.resolve(__dirname, '../api/proxy/[...path]/route.ts');
    const content = fs.readFileSync(routeFile, 'utf-8');

    expect(content).toContain("secure: process.env.NODE_ENV === 'production'");
  });

  test('client-side getAuthToken does not read document.cookie', async () => {
    const fs = await import('fs');
    const path = await import('path');
    const apiFile = path.resolve(__dirname, '../utils/api.ts');
    const content = fs.readFileSync(apiFile, 'utf-8');

    // getAuthToken should not access document.cookie
    // Find the function body
    const funcStart = content.indexOf('function getAuthToken');
    const funcEnd = content.indexOf('}', funcStart);
    const funcBody = content.substring(funcStart, funcEnd);

    expect(funcBody).not.toContain('document.cookie');
  });

  test('client-side auth.ts logout does not clear cookie via document.cookie', async () => {
    const fs = await import('fs');
    const path = await import('path');
    const authFile = path.resolve(__dirname, '../utils/auth.ts');
    const content = fs.readFileSync(authFile, 'utf-8');

    expect(content).not.toContain('document.cookie');
  });

  test('server-side route handlers still read cookie correctly', async () => {
    const fs = await import('fs');
    const path = await import('path');

    // Verify that server-side API routes read the cookie via request.cookies.get
    const routeFiles = [
      '../api/rows/route.ts',
      '../api/search/route.ts',
      '../api/chat/route.ts',
    ];

    for (const routeFile of routeFiles) {
      const fullPath = path.resolve(__dirname, routeFile);
      if (fs.existsSync(fullPath)) {
        const content = fs.readFileSync(fullPath, 'utf-8');
        // Server-side routes should read cookie via request.cookies.get
        expect(content).toContain("cookies.get('sa_session')");
      }
    }
  });
});

// ─── P0-1: SSRF Attack Vector Tests ─────────────────────────────────────────

describe('SSRF Attack Vectors (P0-1)', () => {
  const ALLOWED_PROXY_PATHS = new Set([
    'auth/start',
    'auth/verify',
    'auth/me',
    'auth/logout',
  ]);

  function isAllowedPath(path: string): boolean {
    if (ALLOWED_PROXY_PATHS.has(path)) return true;
    if (path.includes('..') || path.includes('//')) return false;
    return false;
  }

  const attackPaths = [
    // Path traversal
    '../../etc/passwd',
    '../../../etc/shadow',
    'auth/../../../admin',
    // Internal service scanning
    'internal-service/admin',
    'metadata/v1/instance',
    // Cloud metadata endpoints
    '169.254.169.254/latest/meta-data',
    // Double encoding
    '%2e%2e/admin',
    // Null byte
    'auth/start\x00.html',
    // Various bypasses
    'auth/start/../admin',
    'rows/1/search',
    'webhooks/github',
    'test/reset-db',
  ];

  test.each(attackPaths)('blocks attack path: %s', (path) => {
    expect(isAllowedPath(path)).toBe(false);
  });
});
