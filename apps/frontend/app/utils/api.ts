import { Row, Offer, Project, ProviderStatusSnapshot } from '../store';

function getAuthToken(): string {
  // Cookie is HttpOnly — cannot be read from JS.
  // All /api/* routes are same-origin, so the cookie is sent automatically.
  // Server-side route handlers read the cookie and forward as Authorization header.
  return '';
}

async function fetchWithAuth(url: string, init: RequestInit = {}): Promise<Response> {
  const baseHeaders = init.headers ? { ...(init.headers as Record<string, string>) } : {};
  const token = getAuthToken();
  const headers = token ? { ...baseHeaders, Authorization: `Bearer ${token}` } : baseHeaders;

  const res = await fetch(url, { ...init, headers });
  
  // NOTE: Do NOT redirect to /login on 401 here.
  // The workspace page must be accessible to anonymous visitors (affiliate requirement).
  // Individual components should handle 401 gracefully (show empty state, prompt sign-in, etc.).
  
  return res;
}

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';

async function readResponseBodySafe(res: Response): Promise<string> {
  try {
    return await res.text();
  } catch {
    return '';
  }
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

// Provenance types for BidWithProvenance
export interface ProvenanceData {
  product_info?: ProductInfo | null;
  matched_features?: string[];
  chat_excerpts?: ChatExcerpt[];
}

export interface ProductInfo {
  title?: string;
  brand?: string;
  specs?: Record<string, any>;
  [key: string]: any; // Allow additional fields
}

export interface ChatExcerpt {
  role: string;
  content: string;
}

export interface BidWithProvenance {
  id: number;
  price: number;
  currency: string;
  item_title: string;
  item_url: string | null;
  image_url: string | null;
  source: string;
  is_selected: boolean;
  seller?: {
    name: string;
    domain: string | null;
  };
  provenance?: string | null;
  provenance_data?: ProvenanceData | null;
  product_info?: ProductInfo | null;
  matched_features?: string[] | null;
  chat_excerpts?: ChatExcerpt[] | null;
}

export const createCommentApi = async (
  rowId: number,
  body: string,
  bidId?: number,
  offerUrl?: string
): Promise<CommentDto | null> => {
  try {
    const res = await fetchWithAuth('/api/comments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ row_id: rowId, body, bid_id: bidId, offer_url: offerUrl, visibility: 'private' }),
    });
    if (!res.ok) {
      if (res.status === 404) {
        return null;
      }
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
    const res = await fetchWithAuth(`/api/comments?row_id=${rowId}`);
    if (!res.ok) {
      if (res.status === 404) {
        return [];
      }
      if (res.status === 401) return [];  // Anonymous user — not an error
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
    const res = await fetchWithAuth(`/api/rows?id=${rowId}`, {
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
    const res = await fetchWithAuth(`/api/rows?id=${rowId}`, {
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

export interface SearchApiResponse {
  results: Offer[];
  providerStatuses?: ProviderStatusSnapshot[];
  userMessage?: string;
}

// Helper: Run search
export const runSearchApi = async (
  query: string,
  rowId?: number | null,
  options?: { providers?: string[] }
): Promise<Offer[]> => {
  const response = await runSearchApiWithStatus(query, rowId, options);
  return response.results;
};

// Helper: Run search with status message
export const runSearchApiWithStatus = async (
  query: string | null | undefined,
  rowId?: number | null,
  options?: { providers?: string[] }
): Promise<SearchApiResponse> => {
  console.log('[API] Running search:', query ?? '(auto)', 'for rowId:', rowId);
  try {
    const body: any = rowId ? { rowId } : {};
    if (typeof query === 'string' && query.trim().length > 0) {
      body.query = query;
    }
    if (options?.providers && options.providers.length > 0) {
      body.providers = options.providers;
    }

    const res = await fetchWithAuth('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    const rawResults = Array.isArray(data?.results) ? data.results : [];
    const userMessage = typeof data?.user_message === 'string' ? data.user_message : undefined;
    const providerStatuses = Array.isArray(data?.provider_statuses) ? data.provider_statuses : undefined;
    
    // Combine vendor results (first) with product results
    const results = [...rawResults.map((r: any) => {
      const sourceRaw = String(r?.source ?? 'unknown');
      const price = Number(r?.price);
      const rating = r?.rating === null || r?.rating === undefined ? null : Number(r?.rating);
      const reviewsCount = r?.reviews_count === null || r?.reviews_count === undefined ? null : Number(r?.reviews_count);
      // Trust the is_service_provider flag from backend - no heuristic fallback
      const isServiceProvider = r?.is_service_provider === true;

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
        source: sourceRaw,
        merchant_domain: r?.merchant_domain ?? undefined,
        click_url: r?.click_url ?? undefined,
        match_score: typeof r?.match_score === 'number' ? r.match_score : undefined,
        bid_id: typeof r?.bid_id === 'number' ? r.bid_id : undefined,
        is_selected: typeof r?.is_selected === 'boolean' ? r.is_selected : undefined,
        is_liked: r?.is_liked === true,
        liked_at: typeof r?.liked_at === 'string' ? r.liked_at : undefined,
        is_service_provider: isServiceProvider,
        vendor_email: typeof r?.vendor_email === 'string' ? r.vendor_email : undefined,
        vendor_name: typeof r?.vendor_name === 'string' ? r.vendor_name : undefined,
        vendor_company: typeof r?.vendor_company === 'string' ? r.vendor_company : undefined,
      } satisfies Offer;
    })];
    
    return { results, userMessage, providerStatuses };
  } catch (err) {
    console.error('[API] Search error:', err);
    return { results: [] };
  }
};

// Helper: Create a new row in database
export const createRowInDb = async (title: string, projectId?: number | null): Promise<Row | null> => {
  console.log('[API] Creating row in DB:', title, 'projectId:', projectId);
  try {
    const res = await fetchWithAuth('/api/rows', {
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

// Helper: Fetch a single row by ID (avoids re-rendering all rows)
export const fetchSingleRowFromDb = async (rowId: number): Promise<Row | null> => {
  try {
    const res = await fetchWithAuth(`/api/rows?id=${rowId}`);
    if (res.ok) {
      const row = await res.json();
      return row && typeof row === 'object' && !Array.isArray(row) ? row : null;
    }
    if (res.status === 401) return null;  // Anonymous user — not an error
    console.error('[API] fetchSingleRowFromDb failed:', res.status);
  } catch (err) {
    console.error('[API] Fetch single row error:', err);
  }
  return null;
};

// Helper: Fetch all rows from DB
export const fetchRowsFromDb = async (): Promise<Row[] | null> => {
  try {
    console.log('[API] fetchRowsFromDb: calling /api/rows');
    const res = await fetchWithAuth('/api/rows');
    console.log('[API] fetchRowsFromDb: status', res.status);
    if (res.ok) {
      const rows = await res.json();
      return Array.isArray(rows) ? rows : [];
    }
    
    if (res.status === 401) return [];  // Anonymous user — not an error
    const errText = await res.text().catch(() => '');
    console.error('[API] fetchRowsFromDb failed:', res.status, errText);
  } catch (err) {
    console.error('[API] Fetch rows error:', err);
  }
  return null;
};

// Helper: Fetch projects
export const fetchProjectsFromDb = async (): Promise<Project[] | null> => {
  try {
    const res = await fetchWithAuth('/api/projects');
    if (res.ok) {
      const projects = await res.json();
      return Array.isArray(projects) ? projects : [];
    }
    
    if (res.status === 401) return [];  // Anonymous user — not an error
    console.error('[API] fetchProjectsFromDb failed:', res.status);
    return null;
  } catch (err) {
    console.error('[API] fetchProjectsFromDb error:', err);
    return null;
  }
};

// Helper: Create project
export const createProjectInDb = async (title: string): Promise<Project | null> => {
  try {
    const res = await fetchWithAuth('/api/projects', {
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
    const res = await fetchWithAuth(`/api/projects?id=${id}`, { 
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
  answer: string | number | boolean | string[],
  existingAnswers?: Record<string, any>
): Promise<boolean> => {
  try {
    const answers: Record<string, any> = { ...(existingAnswers || {}) };
    answers[factorName] = answer;

    const res = await fetchWithAuth(`/api/rows?id=${rowId}`, {
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

export const saveOutreachToDb = async (
  rowId: number,
  outreach: Record<string, any>,
  existingAnswers?: Record<string, any>
): Promise<boolean> => {
  try {
    const answers: Record<string, any> = { ...(existingAnswers || {}) };
    answers.outreach = outreach;

    const res = await fetchWithAuth(`/api/rows?id=${rowId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ choice_answers: JSON.stringify(answers) }),
    });

    return res.ok;
  } catch (err) {
    console.error('[API] Save outreach error:', err);
    return false;
  }
};

// Helper: Save chat history for a row
export const saveChatHistory = async (rowId: number, messages: Array<{id: string; role: string; content: string}>): Promise<boolean> => {
  try {
    const res = await fetchWithAuth(`/api/rows?id=${rowId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_history: JSON.stringify(messages) }),
    });
    return res.ok;
  } catch (err) {
    console.error('[API] Save chat history error:', err);
    return false;
  }
};

// Helper: Toggle like — ONE function, ONE endpoint
export const toggleLikeApi = async (
  _rowId: number,
  _isLiked: boolean,
  bidId?: number,
): Promise<{ is_liked: boolean; like_count?: number; bid_id: number } | null> => {
  if (!bidId) {
    console.error('[API] toggleLikeApi: no bid_id — cannot toggle');
    return null;
  }
  try {
    const res = await fetchWithAuth('/api/likes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bid_id: bidId }),
    });
    if (res.ok) return await res.json();
    const body = await readResponseBodySafe(res);
    console.error('[API] Toggle like failed:', res.status, body);
    return null;
  } catch (err) {
    console.error('[API] Toggle like error:', err);
    return null;
  }
};

// Helper: Fetch likes
export const fetchLikesApi = async (rowId?: number): Promise<any[]> => {
  try {
    const params = rowId ? `?row_id=${rowId}` : '';
    const res = await fetchWithAuth(`/api/likes${params}`);
    if (res.ok) {
      return await res.json();
    }
    const body = await readResponseBodySafe(res);
    console.error('[API] Fetch likes failed:', res.status, body);
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
    const res = await fetchWithAuth('/api/bugs', {
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
    const res = await fetchWithAuth(`/api/bugs/${id}`);
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

// Helper: Fetch bid with provenance data
export const fetchBidWithProvenance = async (bidId: number): Promise<BidWithProvenance | null> => {
  try {
    const res = await fetchWithAuth(`/api/bids/${bidId}?include_provenance=true`, {
      signal: AbortSignal.timeout(5000), // 5 second timeout
    });

    if (!res.ok) {
      if (res.status === 404) {
        console.error('[API] Bid not found:', bidId);
        return null;
      }
      console.error('[API] Fetch bid with provenance failed:', res.status);
      return null;
    }

    const data = await res.json();
    return data as BidWithProvenance;
  } catch (err) {
    if (err instanceof Error && err.name === 'TimeoutError') {
      console.error('[API] Fetch bid with provenance timeout:', bidId);
    } else {
      console.error('[API] Fetch bid with provenance error:', err);
    }
    return null;
  }
};

// Share Links API

export interface ShareLinkCreate {
  resource_type: 'project' | 'row' | 'tile' | 'bid';
  resource_id: number;
}

export interface ShareLinkResponse {
  token: string;
  share_url: string;
  resource_type: string;
  resource_id: number;
  created_at: string;
}

export interface ShareContentResponse {
  resource_type: string;
  resource_id: number;
  resource_data: any;
  created_by: number;
  access_count: number;
}

export interface ShareMetricsResponse {
  token: string;
  access_count: number;
  unique_visitors: number;
  search_initiated_count: number;
  search_success_count: number;
  signup_conversion_count: number;
  search_success_rate: number;
}

// Helper: Create share link
export const createShareLink = async (
  resourceType: 'project' | 'row' | 'tile' | 'bid',
  resourceId: number
): Promise<ShareLinkResponse | null> => {
  try {
    const res = await fetchWithAuth('/api/shares', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resource_type: resourceType, resource_id: resourceId }),
    });

    if (!res.ok) {
      console.error('[API] Create share link failed:', res.status, await res.text());
      return null;
    }

    return await res.json();
  } catch (err) {
    console.error('[API] Create share link error:', err);
    return null;
  }
};

// Helper: Resolve share link (public access)
export const resolveShareLink = async (token: string): Promise<ShareContentResponse | null> => {
  try {
    const res = await fetchWithAuth(`/api/shares/${token}`);

    if (!res.ok) {
      if (res.status === 404) {
        console.error('[API] Share link not found:', token);
        return null;
      }
      console.error('[API] Resolve share link failed:', res.status);
      return null;
    }

    return await res.json();
  } catch (err) {
    console.error('[API] Resolve share link error:', err);
    return null;
  }
};

// Helper: Get share metrics (requires ownership)
export const getShareMetrics = async (token: string): Promise<ShareMetricsResponse | null> => {
  try {
    const res = await fetchWithAuth(`/api/shares/${token}/metrics`);

    if (!res.ok) {
      if (res.status === 403) {
        console.error('[API] Not authorized to view share metrics');
        return null;
      }
      if (res.status === 404) {
        console.error('[API] Share link not found:', token);
        return null;
      }
      console.error('[API] Get share metrics failed:', res.status);
      return null;
    }

    return await res.json();
  } catch (err) {
    console.error('[API] Get share metrics error:', err);
    return null;
  }
};

