/**
 * Row, Project, and Search API functions.
 */
import { Row, Offer, Project, ProviderStatusSnapshot, useShoppingStore } from '../store';
import { fetchWithAuth } from './api-core';

export interface SearchApiResponse {
  results: Offer[];
  providerStatuses?: ProviderStatusSnapshot[];
  userMessage?: string;
}

export interface DealTransitionPayload {
  new_status: string;
  vendor_quoted_price?: number;
  agreed_terms_summary?: string;
  stripe_payment_intent_id?: string;
}

export interface DealFundingResponse {
  checkout_url?: string;
  session_id?: string;
}

const PROVIDER_ALIASES: Record<string, string> = {
  rainforest: 'amazon',
  google: 'serpapi',
  google_shopping: 'serpapi',
  ebay: 'ebay_browse',
};

function normalizeProviders(providerIds: string[]): string[] {
  const dedup = new Set<string>();
  for (const providerId of providerIds) {
    const raw = String(providerId || '').trim().toLowerCase();
    if (!raw) continue;
    dedup.add(PROVIDER_ALIASES[raw] || raw);
  }
  return Array.from(dedup.values());
}

function getEnabledProvidersFromStore(): string[] {
  try {
    const selected = useShoppingStore.getState().selectedProviders || {};
    return Object.entries(selected)
      .filter(([, enabled]) => Boolean(enabled))
      .map(([providerId]) => providerId);
  } catch {
    return [];
  }
}

// Helper: Run search with status message
export const runSearchApiWithStatus = async (
  query: string | null | undefined,
  rowId?: number | null,
  options?: { providers?: string[] }
): Promise<SearchApiResponse> => {
  try {
    const body: Record<string, unknown> = rowId ? { rowId } : {};
    if (typeof query === 'string' && query.trim().length > 0) {
      body.query = query;
    }
    const requestedProviders = options?.providers && options.providers.length > 0
      ? options.providers
      : getEnabledProvidersFromStore();
    const normalizedProviders = normalizeProviders(requestedProviders);
    if (normalizedProviders.length > 0) {
      body.providers = normalizedProviders;
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
    const results = [...rawResults.map((r: Record<string, unknown>) => {
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
        image_url: typeof r?.image_url === 'string' ? r.image_url : null,
        rating: Number.isFinite(rating) ? rating : null,
        reviews_count: Number.isFinite(reviewsCount) ? reviewsCount : null,
        shipping_info: typeof r?.shipping_info === 'string' ? r.shipping_info : null,
        source: sourceRaw,
        merchant_domain: typeof r?.merchant_domain === 'string' ? r.merchant_domain : undefined,
        click_url: typeof r?.click_url === 'string' ? r.click_url : undefined,
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

// Helper: Persist row to database
export const persistRowToDb = async (rowId: number, title: string) => {
  try {
    const res = await fetchWithAuth(`/api/rows?id=${rowId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    if (res.ok) {
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

// Helper: Create a new row in database
export const createRowInDb = async (title: string, projectId?: number | null): Promise<Row | null> => {
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
    const res = await fetchWithAuth('/api/rows');
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

// Helper: Claim anonymous (guest) rows for the authenticated user
export const claimGuestRows = async (rowIds: number[]): Promise<number> => {
  if (!rowIds.length) return 0;
  try {
    const res = await fetchWithAuth('/api/rows/claim', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ row_ids: rowIds }),
    });
    if (res.ok) {
      const data = await res.json();
      console.log('[API] Claimed guest rows:', data.claimed);
      return data.claimed ?? 0;
    }
    console.error('[API] claimGuestRows failed:', res.status);
  } catch (err) {
    console.error('[API] claimGuestRows error:', err);
  }
  return 0;
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

// Helper: Duplicate project
export const duplicateProjectInDb = async (id: number): Promise<Project | null> => {
  try {
    const res = await fetchWithAuth(`/api/projects/${id}/duplicate`, { 
      method: 'POST',
    });
    if (res.ok) {
      return await res.json();
    }
    console.error('[API] Duplicate project failed:', res.status, await res.text());
    return null;
  } catch (err) {
    console.error('[API] Duplicate project error:', err);
    return null;
  }
};

// Helper: Save choice answer
export const saveChoiceAnswerToDb = async (
  rowId: number,
  factorName: string,
  answer: string | number | boolean | string[],
  existingAnswers?: Record<string, unknown>
): Promise<boolean> => {
  try {
    const answers: Record<string, unknown> = { ...(existingAnswers || {}) };
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

export const transitionDealInDb = async (dealId: number, payload: DealTransitionPayload): Promise<boolean> => {
  try {
    const res = await fetchWithAuth(`/api/deals/${dealId}/transition`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return res.ok;
  } catch (err) {
    console.error('[API] Transition deal error:', err);
    return false;
  }
};

export const fundDealEscrowInDb = async (dealId: number): Promise<DealFundingResponse | null> => {
  try {
    const res = await fetchWithAuth(`/api/deals/${dealId}/fund`, {
      method: 'POST',
    });
    if (!res.ok) {
      console.error('[API] Fund deal failed:', res.status, await res.text().catch(() => ''));
      return null;
    }
    return await res.json() as DealFundingResponse;
  } catch (err) {
    console.error('[API] Fund deal error:', err);
    return null;
  }
};
