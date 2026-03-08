/**
 * Vendor Bookmark API functions.
 * Global vendor favoriting — "Saved to Rolodex".
 */
import { fetchWithAuth, readResponseBodySafe, AUTH_REQUIRED } from './api-core';

export interface VendorBookmarkResponse {
  vendor_id: number;
  created_at: string;
}

export const toggleVendorBookmark = async (
  vendorId: number,
  isCurrentlyBookmarked: boolean,
  sourceRowId?: number,
): Promise<{ status: string; vendor_id: number } | typeof AUTH_REQUIRED | null> => {
  try {
    const method = isCurrentlyBookmarked ? 'DELETE' : 'POST';
    const url = `/api/bookmarks/vendors/${vendorId}${!isCurrentlyBookmarked && sourceRowId ? `?source_row_id=${sourceRowId}` : ''}`;
    const res = await fetchWithAuth(url, { method });
    if (res.ok) return await res.json();
    if (res.status === 401) return AUTH_REQUIRED;
    const body = await readResponseBodySafe(res);
    console.error('[API] Toggle vendor bookmark failed:', res.status, body);
    return null;
  } catch (err) {
    console.error('[API] Toggle vendor bookmark error:', err);
    return null;
  }
};

export const fetchVendorBookmarks = async (): Promise<VendorBookmarkResponse[]> => {
  try {
    const res = await fetchWithAuth('/api/bookmarks/vendors');
    if (res.ok) return await res.json();
    const body = await readResponseBodySafe(res);
    console.error('[API] Fetch vendor bookmarks failed:', res.status, body);
    return [];
  } catch (err) {
    console.error('[API] Fetch vendor bookmarks error:', err);
    return [];
  }
};
