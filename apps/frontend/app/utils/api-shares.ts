/**
 * Share links API types and functions.
 */
import { fetchWithAuth } from './api-core';

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
