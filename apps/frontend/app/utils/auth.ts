
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

export const startAuth = async (phone: string): Promise<AuthStartResponse> => {
  const body = { phone };
  
  const res = await fetch('/api/auth/start', {
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

export const verifyAuth = async (phone: string, code: string): Promise<AuthVerifyResponse> => {
  const body = { phone, code };

  const res = await fetch('/api/auth/verify', {
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
  await fetch('/api/auth/logout', { method: 'POST' });
  // Cookie is HttpOnly — server clears it via the proxy route response.
};

export function getToken(): string {
  return typeof window !== 'undefined' ? localStorage.getItem('session_token') || '' : '';
}

export function authHeaders(): Record<string, string> {
  return { Authorization: `Bearer ${getToken()}` };
}

export const getMe = async (): Promise<AuthMeResponse | null> => {
  try {
    const res = await fetch('/api/auth/me');
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.error('Failed to get user session', err);
  }
  return null;
};
