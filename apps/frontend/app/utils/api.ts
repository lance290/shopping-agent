import { Row, Offer, Project } from '../store';

function getDevAuthToken(): string {
  const disableClerk = process.env.NEXT_PUBLIC_DISABLE_CLERK === '1';
  if (!disableClerk) return '';

  // Prefer the Playwright-set cookie so UI E2E tests and API-created rows share the same session.
  if (typeof document !== 'undefined') {
    const match = document.cookie
      .split(';')
      .map((c) => c.trim())
      .find((c) => c.startsWith('sa_session='));
    if (match) {
      const value = match.split('=')[1];
      if (value) return decodeURIComponent(value);
    }
  }

  return process.env.NEXT_PUBLIC_DEV_SESSION_TOKEN || '';
}

async function getOrCreateDevAuthToken(forceMint: boolean = false): Promise<string> {
  const disableClerk = process.env.NEXT_PUBLIC_DISABLE_CLERK === '1';
  if (!disableClerk) return '';

  const existing = getDevAuthToken();
  if (existing && !forceMint) return existing;

  if (typeof document === 'undefined') return '';

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
  try {
    const res = await fetch(`${backendUrl}/test/mint-session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'dev@example.com' }),
    });
    if (!res.ok) return '';
    const data = await res.json();
    if (data?.session_token) {
      document.cookie = `sa_session=${encodeURIComponent(data.session_token)}; path=/`;
      return data.session_token;
    }
  } catch (err) {
    console.error('[API] Dev session mint failed:', err);
  }
  return '';
}

async function fetchWithDevAuth(url: string, init: RequestInit = {}): Promise<Response> {
  const baseHeaders = init.headers ? { ...(init.headers as Record<string, string>) } : {};
  const token = await getOrCreateDevAuthToken();
  const headers = token ? { ...baseHeaders, Authorization: `Bearer ${token}` } : baseHeaders;

  const res = await fetch(url, { ...init, headers });
  if (res.status !== 401) {
    return res;
  }

  // If we got a 401, mint a fresh token and retry once.
  const freshToken = await getOrCreateDevAuthToken(true);
  if (!freshToken || freshToken === token) {
    return res;
  }

  const retryHeaders = { ...baseHeaders, Authorization: `Bearer ${freshToken}` };
  return fetch(url, { ...init, headers: retryHeaders });
}

export interface CommentDto {
  id: number;
  row_id: number;
  body: string;
  bid_id?: number | null;
  offer_url?: string | null;
  visibility: string;
  created_at: string;
}

export const createCommentApi = async (
  rowId: number,
  body: string,
  bidId?: number,
  offerUrl?: string
): Promise<CommentDto | null> => {
  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
    const res = await fetchWithDevAuth(`${backendUrl}/comments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ row_id: rowId, body, bid_id: bidId, offer_url: offerUrl, visibility: 'private' }),
    });
    if (!res.ok) {
      console.error('[API] createComment failed:', res.status);
      return null;
    }
    return await res.json();
  } catch (err) {
    console.error('[API] createComment error:', err);
    return null;
  }
};

export const fetchCommentsApi = async (rowId: number): Promise<CommentDto[]> => {
  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
    const res = await fetchWithDevAuth(`${backendUrl}/comments?row_id=${rowId}`);
    if (!res.ok) {
      console.error('[API] fetchComments failed:', res.status);
      return [];
    }
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch (err) {
    console.error('[API] fetchComments error:', err);
    return [];
  }
};

// Helper: Persist row to database
export const persistRowToDb = async (rowId: number, title: string) => {
  console.log('[API] Persisting to DB:', rowId, title);
  try {
    const res = await fetch(`/api/rows?id=${rowId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    if (res.ok) {
      console.log('[API] DB persist success');
      return true;
    } else {
      console.error('[API] DB persist failed:', res.status);
      return false;
    }
  } catch (err) {
    console.error('[API] DB persist error:', err);
    return false;
  }
};

// Helper: Select an offer for a row
export const selectOfferForRow = async (rowId: number, bidId: number): Promise<boolean> => {
  try {
    const res = await fetch(`/api/rows?id=${rowId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ selected_bid_id: bidId }),
    });

    if (!res.ok) {
      console.error('[API] Select offer failed:', res.status);
      return false;
    }
    return true;
  } catch (err) {
    console.error('[API] Select offer error:', err);
    return false;
  }
};

// Helper: Run search
export const runSearchApi = async (
  query: string,
  rowId?: number | null,
  options?: { providers?: string[] }
): Promise<Offer[]> => {
  console.log('[API] Running search:', query, 'for rowId:', rowId);
  try {
    const body: any = rowId ? { query, rowId } : { query };
    if (options?.providers && options.providers.length > 0) {
      body.providers = options.providers;
    }

    const res = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    const rawResults = Array.isArray(data?.results) ? data.results : [];
    return rawResults.map((r: any) => {
      const price = Number(r?.price);
      const rating = r?.rating === null || r?.rating === undefined ? null : Number(r?.rating);
      const reviewsCount = r?.reviews_count === null || r?.reviews_count === undefined ? null : Number(r?.reviews_count);

      return {
        title: String(r?.title ?? ''),
        price: Number.isFinite(price) ? price : 0,
        currency: String(r?.currency ?? 'USD'),
        merchant: String(r?.merchant ?? 'Unknown'),
        url: String(r?.url ?? '#'),
        image_url: r?.image_url ?? null,
        rating: Number.isFinite(rating as any) ? (rating as number) : null,
        reviews_count: Number.isFinite(reviewsCount as any) ? (reviewsCount as number) : null,
        shipping_info: r?.shipping_info ?? null,
        source: String(r?.source ?? 'unknown'),
        merchant_domain: r?.merchant_domain ?? undefined,
        click_url: r?.click_url ?? undefined,
        match_score: typeof r?.match_score === 'number' ? r.match_score : undefined,
        bid_id: typeof r?.bid_id === 'number' ? r.bid_id : undefined,
        is_selected: typeof r?.is_selected === 'boolean' ? r.is_selected : undefined,
      } satisfies Offer;
    });
  } catch (err) {
    console.error('[API] Search error:', err);
    return [];
  }
};

// Helper: Create a new row in database
export const createRowInDb = async (title: string, projectId?: number | null): Promise<Row | null> => {
  console.log('[API] Creating row in DB:', title, 'projectId:', projectId);
  try {
    const res = await fetch('/api/rows', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        title, 
        status: 'sourcing',
        project_id: projectId,
        request_spec: {
          item_name: title,
          constraints: '{}'
        }
      }),
    });
    if (res.ok) {
      const newRow = await res.json();
      console.log('[API] Row created:', newRow);
      return newRow;
    } else {
      console.error('[API] Create row failed:', res.status, await res.text());
    }
  } catch (err) {
    console.error('[API] Create row error:', err);
  }
  return null;
};

// Helper: Fetch all rows from DB
export const fetchRowsFromDb = async (): Promise<Row[]> => {
  try {
    const res = await fetch('/api/rows');
    if (res.ok) {
      const rows = await res.json();
      return Array.isArray(rows) ? rows : [];
    } else {
      console.error('[API] fetchRowsFromDb failed:', res.status);
    }
  } catch (err) {
    console.error('[API] Fetch rows error:', err);
  }
  return [];
};

// Helper: Fetch projects
export const fetchProjectsFromDb = async (): Promise<Project[]> => {
  try {
    const res = await fetch('/api/projects');
    if (res.ok) {
      const projects = await res.json();
      return Array.isArray(projects) ? projects : [];
    } else {
      console.error('[API] fetchProjectsFromDb failed:', res.status);
      return [];
    }
  } catch (err) {
    console.error('[API] fetchProjectsFromDb error:', err);
    return [];
  }
};

// Helper: Create project
export const createProjectInDb = async (title: string): Promise<Project | null> => {
  try {
    const res = await fetch('/api/projects', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ title }),
    });
    if (res.ok) {
      return await res.json();
    }
    const errorText = await res.text();
    console.error(`[API] Create project failed: ${res.status} ${res.statusText}`, errorText);
    
    // Attempt to parse JSON error if available
    try {
      const errorJson = JSON.parse(errorText);
      if (errorJson.error) {
        console.error(`[API] Server error detail: ${errorJson.error}`);
      }
    } catch {
      // Not JSON, ignore
    }
  } catch (err) {
    console.error('[API] Create project network error:', err);
  }
  return null;
};

// Helper: Delete project
export const deleteProjectFromDb = async (id: number): Promise<boolean> => {
  try {
    const res = await fetch(`/api/projects?id=${id}`, { 
      method: 'DELETE',
    });
    return res.ok;
  } catch (err) {
    console.error('[API] Delete project error:', err);
    return false;
  }
};

// Helper: Save choice answer
export const saveChoiceAnswerToDb = async (
  rowId: number,
  factorName: string,
  answer: string | number | boolean,
  existingAnswers?: Record<string, any>
): Promise<boolean> => {
  try {
    const answers: Record<string, any> = { ...(existingAnswers || {}) };
    answers[factorName] = answer;

    const res = await fetch(`/api/rows?id=${rowId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ choice_answers: JSON.stringify(answers) }),
    });
    
    return res.ok;
  } catch (err) {
    console.error('[API] Save answer error:', err);
    return false;
  }
};

// Helper: Toggle like (persist)
export const toggleLikeApi = async (
  rowId: number,
  isLiked: boolean,
  bidId?: number,
  offerUrl?: string
): Promise<boolean> => {
  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (isLiked) {
      // Create like
      const res = await fetchWithDevAuth(`${backendUrl}/likes`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ row_id: rowId, bid_id: bidId, offer_url: offerUrl }),
      });
      return res.ok;
    } else {
      // Delete like
      // We send params as query string for DELETE if simple, or body if allowed.
      // Backend expects query params or body? Let's use query params to be safe with standard fetch/FastAPI.
      // Let's use query params to be safe with standard fetch/FastAPI.
      const params = new URLSearchParams({ row_id: String(rowId) });
      if (bidId) params.append('bid_id', String(bidId));
      if (offerUrl) params.append('offer_url', offerUrl);
      
      const res = await fetchWithDevAuth(`${backendUrl}/likes?${params.toString()}`, {
        method: 'DELETE',
        headers,
      });
      return res.ok;
    }
  } catch (err) {
    console.error('[API] Toggle like error:', err);
    return false;
  }
};

// Helper: Fetch likes
export const fetchLikesApi = async (rowId?: number): Promise<any[]> => {
  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
    const params = rowId ? `?row_id=${rowId}` : '';
    const res = await fetchWithDevAuth(`${backendUrl}/likes${params}`);
    if (res.ok) {
      return await res.json();
    }
    return [];
  } catch (err) {
    console.error('[API] Fetch likes error:', err);
    return [];
  }
};


export interface BugReportResponse {
  id: string;
  status: string;
  created_at: string;
  notes: string;
  severity: string;
  category: string;
  attachments?: string[];
  previewUrl?: string; // Note: Backend sends snake_case 'preview_url', we might need to map it or use snake_case in interface if we don't transform it.
  // Actually, checking the backend response, it returns snake_case fields.
  // We should align the interface to match the JSON response from backend.
  preview_url?: string;
  github_issue_url?: string;
  github_pr_url?: string;
}

export const submitBugReport = async (formData: FormData): Promise<BugReportResponse | null> => {
  const startTime = performance.now();
  console.log('[API] Submitting bug report');
  
  try {
    const res = await fetch('/api/bugs', {
      method: 'POST',
      body: formData,
    });
    
    const duration = performance.now() - startTime;

    if (res.ok) {
      const data = await res.json();
      console.log(`[API] Bug report submitted successfully in ${duration.toFixed(0)}ms`, {
        id: data.id,
        status: data.status
      });
      return data;
    } else {
      console.error(`[API] Bug report submission failed after ${duration.toFixed(0)}ms:`, res.status);
      return null;
    }
  } catch (err) {
    const duration = performance.now() - startTime;
    console.error(`[API] Bug report submission error after ${duration.toFixed(0)}ms:`, err);
    return null;
  }
};

export const fetchBugReport = async (id: string): Promise<BugReportResponse | null> => {
  try {
    const res = await fetch(`/api/bugs/${id}`);
    if (res.ok) {
      return await res.json();
    }
    console.error('[API] Fetch bug report failed:', res.status);
    return null;
  } catch (err) {
    console.error('[API] Fetch bug report error:', err);
    return null;
  }
};

