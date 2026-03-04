/**
 * Comments API functions.
 */
import { fetchWithAuth, AUTH_REQUIRED } from './api-core';

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
): Promise<CommentDto | typeof AUTH_REQUIRED | null> => {
  try {
    const res = await fetchWithAuth('/api/comments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ row_id: rowId, body, bid_id: bidId, offer_url: offerUrl, visibility: 'private' }),
    });
    if (!res.ok) {
      if (res.status === 401) return AUTH_REQUIRED;
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
