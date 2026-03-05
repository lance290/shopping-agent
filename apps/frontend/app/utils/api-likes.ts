/**
 * Likes API functions.
 */
import { fetchWithAuth, readResponseBodySafe, AUTH_REQUIRED } from './api-core';

// Helper: Toggle like — ONE function, ONE endpoint
export const toggleLikeApi = async (
  _rowId: number,
  _isLiked: boolean,
  bidId?: number,
): Promise<{ is_liked: boolean; like_count?: number; bid_id: number } | typeof AUTH_REQUIRED | null> => {
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
    if (res.status === 401) return AUTH_REQUIRED;
    const body = await readResponseBodySafe(res);
    console.error('[API] Toggle like failed:', res.status, body);
    return null;
  } catch (err) {
    console.error('[API] Toggle like error:', err);
    return null;
  }
};

// Helper: Fetch likes
export const fetchLikesApi = async (rowId?: number): Promise<unknown[]> => {
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
