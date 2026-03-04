/**
 * Bug report API functions.
 */
import { fetchWithAuth } from './api-core';

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
  try {
    const res = await fetchWithAuth('/api/bugs', {
      method: 'POST',
      body: formData,
    });
    
    const duration = performance.now() - startTime;

    if (res.ok) {
      const data = await res.json();
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
