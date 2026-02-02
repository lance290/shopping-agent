
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export interface AuthStartResponse {
  status: string;
  locked_until?: string;
}

export interface AuthVerifyResponse {
  status: string;
  session_token: string;
  user_id: number;
}

export interface AuthMeResponse {
  authenticated: boolean;
  email?: string;
  phone_number?: string;
  user_id?: number;
}

export const startAuth = async (identifier: string): Promise<AuthStartResponse> => {
  const isEmail = identifier.includes('@');
  const body = isEmail ? { email: identifier } : { phone: identifier };
  
  const res = await fetch('/api/proxy/auth/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to start authentication' }));
    throw new Error(error.detail || 'Failed to start authentication');
  }

  return res.json();
};

export const verifyAuth = async (identifier: string, code: string): Promise<AuthVerifyResponse> => {
  const isEmail = identifier.includes('@');
  const body = isEmail 
    ? { email: identifier, code } 
    : { phone: identifier, code };

  const res = await fetch('/api/proxy/auth/verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to verify code' }));
    throw new Error(error.detail || 'Failed to verify code');
  }

  return res.json();
};

export const logout = async (): Promise<void> => {
  await fetch('/api/proxy/auth/logout', { method: 'POST' });
  // Also clear cookie on client side if possible, or rely on API to clear it
  document.cookie = 'sa_session=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
};

export const getMe = async (): Promise<AuthMeResponse | null> => {
  try {
    const res = await fetch('/api/proxy/auth/me');
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.error('Failed to get user session', err);
  }
  return null;
};
