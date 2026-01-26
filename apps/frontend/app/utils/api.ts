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
    const bffUrl = process.env.NEXT_PUBLIC_BFF_URL || 'http://127.0.0.1:8081';
    const token = getDevAuthToken();
    const res = await fetch(`${bffUrl}/api/rows`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
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
    // Call BFF directly to bypass Next.js API route registration issue
    const bffUrl = process.env.NEXT_PUBLIC_BFF_URL || 'http://127.0.0.1:8081';
    const token = getDevAuthToken();
    const res = await fetch(`${bffUrl}/api/projects`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
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
    const bffUrl = process.env.NEXT_PUBLIC_BFF_URL || 'http://127.0.0.1:8081';
    const token = getDevAuthToken();
    const res = await fetch(`${bffUrl}/api/projects`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ title }),
    });
    if (res.ok) {
      return await res.json();
    }
    console.error('[API] Create project failed:', res.status);
  } catch (err) {
    console.error('[API] Create project error:', err);
  }
  return null;
};

// Helper: Delete project
export const deleteProjectFromDb = async (id: number): Promise<boolean> => {
  try {
    const bffUrl = process.env.NEXT_PUBLIC_BFF_URL || 'http://127.0.0.1:8081';
    const token = getDevAuthToken();
    const res = await fetch(`${bffUrl}/api/projects/${id}`, { 
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` },
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

