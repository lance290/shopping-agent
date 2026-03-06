
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
  name?: string;
  company?: string;
  zip_code?: string;
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
  // Viral Flywheel (PRD 06): include referral token if user arrived via share link
  const referralToken = typeof window !== 'undefined' ? localStorage.getItem('referral_token') : null;
  // TeamPop Referral (PRD 06): include affiliate code if user arrived via /?ref=XYZ
  const refCode = typeof window !== 'undefined' ? localStorage.getItem('pop_ref_code') : null;

  const body: Record<string, string> = { phone, code };
  if (referralToken) {
    body.referral_token = referralToken;
  }
  if (refCode) {
    body.ref_code = refCode;
  }

  const res = await fetch('/api/auth/verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to verify code' }));
    throw new Error(error.detail || 'Failed to verify code');
  }

  // Clear tokens after successful signup
  if (typeof window !== 'undefined') {
    if (referralToken) localStorage.removeItem('referral_token');
    if (refCode) localStorage.removeItem('pop_ref_code');
  }

  return res.json();
};

export const logout = async (): Promise<void> => {
  await fetch('/api/auth/logout', { method: 'POST' });
  if (typeof window !== 'undefined') {
    localStorage.removeItem('session_token');
    localStorage.removeItem('is_logged_in');
  }
};

export function getToken(): string {
  return typeof window !== 'undefined' ? localStorage.getItem('session_token') || '' : '';
}

export function isLoggedIn(): boolean {
  return typeof window !== 'undefined' && localStorage.getItem('is_logged_in') === '1';
}

export function setLoggedIn(): void {
  if (typeof window !== 'undefined') localStorage.setItem('is_logged_in', '1');
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
