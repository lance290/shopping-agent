/**
 * Tests for bug #117: unhandled AbortError when user dismisses clipboard/share prompt.
 *
 * When navigator.clipboard.writeText() throws AbortError (e.g., the user cancels
 * the browser permission prompt), the error must be swallowed silently — no
 * "Unhandled Rejection" in the console and no error toast shown to the user.
 */

import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import React from 'react';
import ProcurementBoard from '../components/Board';
import RowStrip from '../components/RowStrip';
import { useShoppingStore, Row } from '../store';

vi.mock('../utils/api', () => ({
  fetchSingleRowFromDb: vi.fn().mockResolvedValue(null),
  runSearchApiWithStatus: vi.fn().mockResolvedValue({ results: [], providerStatuses: [], userMessage: null }),
  selectOfferForRow: vi.fn().mockResolvedValue(true),
  toggleLikeApi: vi.fn().mockResolvedValue(null),
  createCommentApi: vi.fn().mockResolvedValue(true),
  fetchCommentsApi: vi.fn().mockResolvedValue([]),
  fetchRowsFromDb: vi.fn().mockResolvedValue([]),
}));

const makeAbortError = () => {
  const err = new DOMException('Share canceled', 'AbortError');
  return err;
};

describe('Share AbortError handling (bug #117)', () => {
  const mockRow: Row = {
    id: 1,
    title: 'Test Product',
    status: 'sourcing',
    budget_max: null,
    currency: 'USD',
  };

  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
    useShoppingStore.getState().setRows([mockRow]);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('Share Board button does not show error toast when clipboard is aborted', async () => {
    // Arrange: clipboard throws AbortError (user dismissed permission prompt)
    vi.stubGlobal('navigator', {
      ...navigator,
      clipboard: { writeText: vi.fn().mockRejectedValue(makeAbortError()) },
    });

    render(React.createElement(ProcurementBoard));

    const shareBtn = screen.getByTitle ? undefined : undefined; // title attr not set on Share Board
    const shareBoardBtn = screen.getByText('Share Board');
    expect(shareBoardBtn).toBeDefined();

    await act(async () => {
      fireEvent.click(shareBoardBtn);
      // give the async handler time to settle
      await new Promise(r => setTimeout(r, 50));
    });

    // No error toast should appear
    expect(screen.queryByText(/Failed to copy/i)).toBeNull();
    expect(screen.queryByText(/Could not copy/i)).toBeNull();
  });

  test('Share Board button shows error toast for non-abort clipboard failures', async () => {
    vi.stubGlobal('navigator', {
      ...navigator,
      clipboard: { writeText: vi.fn().mockRejectedValue(new Error('Permission denied')) },
    });

    render(React.createElement(ProcurementBoard));

    const shareBoardBtn = screen.getByText('Share Board');

    await act(async () => {
      fireEvent.click(shareBoardBtn);
      await new Promise(r => setTimeout(r, 50));
    });

    // Error toast should appear for non-abort errors
    expect(screen.queryByText(/Failed to copy link/i)).toBeDefined();
  });

  test('RowStrip copy link button does not show error toast when clipboard is aborted', async () => {
    // Arrange: fetch fails (to reach clipboard fallback), clipboard throws AbortError
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 500 })));
    vi.stubGlobal('navigator', {
      ...navigator,
      clipboard: { writeText: vi.fn().mockRejectedValue(makeAbortError()) },
    });

    const onToast = vi.fn();
    render(React.createElement(RowStrip, {
      row: mockRow,
      offers: [],
      isActive: false,
      onSelect: vi.fn(),
      onToast,
    }));

    const copyLinkBtn = screen.getByTitle('Copy search link');
    expect(copyLinkBtn).toBeDefined();

    await act(async () => {
      fireEvent.click(copyLinkBtn);
      await new Promise(r => setTimeout(r, 50));
    });

    // onToast must NOT have been called with 'error' for AbortError
    const errorCalls = onToast.mock.calls.filter(([, tone]) => tone === 'error');
    expect(errorCalls).toHaveLength(0);
  });

  test('RowStrip copy link button shows error toast for non-abort clipboard failures', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 500 })));
    vi.stubGlobal('navigator', {
      ...navigator,
      clipboard: { writeText: vi.fn().mockRejectedValue(new Error('NotAllowedError')) },
    });

    const onToast = vi.fn();
    render(React.createElement(RowStrip, {
      row: mockRow,
      offers: [],
      isActive: false,
      onSelect: vi.fn(),
      onToast,
    }));

    const copyLinkBtn = screen.getByTitle('Copy search link');

    await act(async () => {
      fireEvent.click(copyLinkBtn);
      await new Promise(r => setTimeout(r, 50));
    });

    // onToast SHOULD have been called with 'error' for other errors
    await waitFor(() => {
      const errorCalls = onToast.mock.calls.filter(([, tone]) => tone === 'error');
      expect(errorCalls.length).toBeGreaterThan(0);
    }, { timeout: 500 });
  });
});
