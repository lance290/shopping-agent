/**
 * Outreach API functions — email generation, sending, contact statuses, quote links.
 */
import { fetchWithAuth } from './api-core';

export const generateOutreachEmail = async (
  rowId: number,
  vendorEmail: string,
  vendorCompany: string,
  replyToEmail: string,
  senderName?: string,
  senderCompany?: string,
): Promise<{ subject: string; body: string } | null> => {
  try {
    const res = await fetchWithAuth(`/api/outreach/${rowId}/generate-email`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        vendor_email: vendorEmail,
        vendor_company: vendorCompany,
        reply_to_email: replyToEmail,
        sender_name: senderName || null,
        sender_company: senderCompany || null,
      }),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error('[API] Generate email error:', err);
    return null;
  }
};

export const sendOutreachEmail = async (
  rowId: number,
  vendorEmail: string,
  vendorCompany: string,
  replyToEmail: string,
  subject: string,
  body: string,
  vendorName?: string,
  senderName?: string,
  senderCompany?: string,
): Promise<{ status: string; message_id?: string; error?: string } | null> => {
  try {
    const res = await fetchWithAuth(`/api/outreach/${rowId}/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        vendor_email: vendorEmail,
        vendor_company: vendorCompany,
        vendor_name: vendorName || null,
        reply_to_email: replyToEmail,
        subject,
        body,
        sender_name: senderName || null,
        sender_company: senderCompany || null,
      }),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error('[API] Send outreach error:', err);
    return null;
  }
};

export const fetchContactStatuses = async (
  rowId: number,
): Promise<Record<string, { status: string; sent_at: string | null; quoted_at: string | null }> | null> => {
  try {
    const res = await fetchWithAuth(`/api/outreach/${rowId}/contact-statuses`);
    if (!res.ok) return null;
    const data = await res.json();
    return data.statuses || null;
  } catch (err) {
    console.error('[API] Fetch contact statuses error:', err);
    return null;
  }
};

export const createQuoteLink = async (
  rowId: number,
  vendorEmail: string,
  vendorCompany: string,
  vendorName?: string,
): Promise<{ token: string; quote_url: string } | null> => {
  try {
    const res = await fetchWithAuth(`/api/outreach/${rowId}/quote-link`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        vendor_email: vendorEmail,
        vendor_company: vendorCompany,
        vendor_name: vendorName || null,
      }),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error('[API] Create quote link error:', err);
    return null;
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
