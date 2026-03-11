/**
 * Trust Metrics API — feedback, outcomes, and event logging.
 * Backend endpoints: POST /rows/{id}/feedback, /rows/{id}/outcome, /rows/{id}/events
 */
import { fetchWithAuth, AUTH_REQUIRED } from './api-core';

export type FeedbackType =
  | 'good_lead'
  | 'irrelevant'
  | 'wrong_geography'
  | 'not_premium_enough'
  | 'too_expensive'
  | 'missing_contact_info'
  | 'duplicate_of_known_option'
  | 'unsafe_or_low_trust'
  | 'saved_me_time';

export type ResolutionType =
  | 'solved'
  | 'partially_solved'
  | 'not_solved';

export type QualityType =
  | 'results_were_strong'
  | 'results_were_noisy'
  | 'had_to_search_manually'
  | 'routing_was_wrong';

export type OutcomeType = ResolutionType | QualityType;

export interface FeedbackPayload {
  bid_id?: number;
  feedback_type: FeedbackType;
  score?: number;
  comment?: string;
  metadata?: Record<string, unknown>;
}

export interface OutcomePayload {
  outcome?: ResolutionType;
  quality?: QualityType;
  note?: string;
}

export interface EventPayload {
  bid_id?: number;
  event_type: string;
  event_value?: string;
  metadata?: Record<string, unknown>;
}

export async function submitFeedback(
  rowId: number,
  payload: FeedbackPayload,
): Promise<{ id: number; status: string } | typeof AUTH_REQUIRED | null> {
  try {
    const res = await fetchWithAuth(`/api/rows/${rowId}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (res.status === 401) return AUTH_REQUIRED;
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error('[API] submitFeedback error:', err);
    return null;
  }
}

export async function submitOutcome(
  rowId: number,
  payload: OutcomePayload,
): Promise<{ row_id: number; outcome: string | null; quality: string | null; status: string } | typeof AUTH_REQUIRED | null> {
  try {
    const res = await fetchWithAuth(`/api/rows/${rowId}/outcome`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (res.status === 401) return AUTH_REQUIRED;
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error('[API] submitOutcome error:', err);
    return null;
  }
}

export async function logEvent(
  rowId: number,
  payload: EventPayload,
): Promise<{ id: number; status: string } | typeof AUTH_REQUIRED | null> {
  try {
    const res = await fetchWithAuth(`/api/rows/${rowId}/events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (res.status === 401) return AUTH_REQUIRED;
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error('[API] logEvent error:', err);
    return null;
  }
}

export const FEEDBACK_OPTIONS: { type: FeedbackType; label: string; emoji: string }[] = [
  { type: 'good_lead', label: 'Good Lead', emoji: '+' },
  { type: 'saved_me_time', label: 'Saved Me Time', emoji: '⏱' },
  { type: 'irrelevant', label: 'Irrelevant', emoji: '-' },
  { type: 'too_expensive', label: 'Too Expensive', emoji: '$' },
  { type: 'not_premium_enough', label: 'Not Premium', emoji: '!' },
  { type: 'missing_contact_info', label: 'No Contact', emoji: '?' },
  { type: 'wrong_geography', label: 'Wrong Area', emoji: 'x' },
  { type: 'duplicate_of_known_option', label: 'Duplicate', emoji: '2' },
  { type: 'unsafe_or_low_trust', label: 'Low Trust', emoji: '⚠' },
];

export const RESOLUTION_OPTIONS: { type: ResolutionType; label: string }[] = [
  { type: 'solved', label: 'Solved' },
  { type: 'partially_solved', label: 'Partially Solved' },
  { type: 'not_solved', label: 'Not Solved' },
];

export const QUALITY_OPTIONS: { type: QualityType; label: string }[] = [
  { type: 'results_were_strong', label: 'Strong Results' },
  { type: 'results_were_noisy', label: 'Noisy Results' },
  { type: 'had_to_search_manually', label: 'Had to Search Manually' },
  { type: 'routing_was_wrong', label: 'Wrong Route' },
];

export const OUTCOME_OPTIONS: { type: OutcomeType; label: string }[] = [
  ...RESOLUTION_OPTIONS,
  ...QUALITY_OPTIONS,
];
