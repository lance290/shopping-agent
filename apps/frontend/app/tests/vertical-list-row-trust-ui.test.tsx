import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { useShoppingStore } from '../store';
import { AUTH_REQUIRED } from '../utils/api-core';

const { submitFeedbackMock, submitOutcomeMock } = vi.hoisted(() => ({
  submitFeedbackMock: vi.fn(),
  submitOutcomeMock: vi.fn(),
}));

vi.mock('../utils/api', () => {
  return {
    runSearchApiWithStatus: vi.fn(),
    fetchSingleRowFromDb: vi.fn(),
    toggleVendorBookmark: vi.fn(),
    toggleItemBookmark: vi.fn(),
    createShareLink: vi.fn(),
    createCommentApi: vi.fn(),
    fetchCommentsApi: vi.fn().mockResolvedValue([]),
    fetchWithAuth: vi.fn(),
    AUTH_REQUIRED,
    preferredSearchQueryForRow: vi.fn().mockReturnValue('test query'),
    submitFeedback: submitFeedbackMock,
    submitOutcome: submitOutcomeMock,
    FEEDBACK_OPTIONS: [
      { type: 'good_lead', label: 'Good Lead', emoji: '+' },
      { type: 'irrelevant', label: 'Irrelevant', emoji: '-' },
    ],
    RESOLUTION_OPTIONS: [
      { type: 'solved', label: 'Solved' },
      { type: 'not_solved', label: 'Not Solved' },
    ],
    QUALITY_OPTIONS: [
      { type: 'results_were_strong', label: 'Strong Results' },
      { type: 'results_were_noisy', label: 'Noisy Results' },
    ],
    OUTCOME_OPTIONS: [
      { type: 'solved', label: 'Solved' },
      { type: 'not_solved', label: 'Not Solved' },
      { type: 'results_were_strong', label: 'Strong Results' },
      { type: 'results_were_noisy', label: 'Noisy Results' },
    ],
  };
});

vi.mock('../components/sdui/DynamicRenderer', () => ({
  DynamicRenderer: () => null,
}));

vi.mock('../components/VendorContactModal', () => ({
  default: () => null,
}));

vi.mock('../components/OutreachQueue', () => ({
  default: () => null,
}));

import { VerticalListRow } from '../components/sdui/VerticalListRow';
import type { Row, Offer } from '../store';

function resetStore() {
  useShoppingStore.setState({
    currentQuery: '',
    activeRowId: null,
    targetProjectId: null,
    newRowAggressiveness: 50,
    rows: [],
    projects: [],
    rowResults: {},
    rowProviderStatuses: {},
    rowSearchErrors: {},
    rowOfferSort: {},
    moreResultsIncoming: {},
    streamingRowIds: {},
    isSearching: false,
    cardClickQuery: null,
    selectedProviders: { amazon: true, ebay: true, serpapi: true, vendor_directory: true },
    isSidebarOpen: false,
    isReportBugModalOpen: false,
    pendingRowDelete: null,
    expandedRowId: null,
    sduiFallbackCount: 0,
  });
}

const baseRow: Row = {
  id: 101,
  title: 'Find a luxury charter option',
  status: 'open',
  budget_max: null,
  currency: 'USD',
  row_outcome: null,
  row_quality_assessment: null,
};

const baseOffer: Offer = {
  title: 'Operator One',
  price: null,
  currency: 'USD',
  merchant: 'Operator One',
  url: 'https://operator.example.com',
  image_url: null,
  rating: null,
  reviews_count: null,
  shipping_info: null,
  source: 'vendor_directory',
  bid_id: 501,
  vendor_id: 33,
  is_selected: false,
};

describe('VerticalListRow trust UI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetStore();
    vi.stubGlobal('alert', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test('submits per-result feedback and reflects success state', async () => {
    submitFeedbackMock.mockResolvedValue({ id: 1, status: 'ok' });

    render(
      <VerticalListRow
        row={baseRow}
        offers={[baseOffer]}
        isActive
        isExpanded
        onSelect={vi.fn()}
        onToggleExpand={vi.fn()}
      />
    );

    fireEvent.click(screen.getByTitle('Rate this result'));
    fireEvent.click(screen.getByRole('button', { name: 'Good Lead' }));

    await waitFor(() => {
      expect(submitFeedbackMock).toHaveBeenCalledWith(101, {
        bid_id: 501,
        feedback_type: 'good_lead',
      });
    });

    await waitFor(() => {
      expect(screen.getByTitle('Feedback: good_lead')).toBeInTheDocument();
    });
  });

  test('does not update outcome label when outcome submission is unauthorized', async () => {
    submitOutcomeMock.mockResolvedValue(AUTH_REQUIRED);

    render(
      <VerticalListRow
        row={baseRow}
        offers={[baseOffer]}
        isActive
        isExpanded
        onSelect={vi.fn()}
        onToggleExpand={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Outcome/i }));
    fireEvent.click(screen.getByRole('button', { name: 'Solved' }));

    await waitFor(() => {
      expect(submitOutcomeMock).toHaveBeenCalledWith(101, { outcome: 'solved' });
    });

    expect(screen.getByRole('button', { name: /Outcome/i })).toBeInTheDocument();
    expect(globalThis.alert).toHaveBeenCalledWith('Sign in to rate this search');
  });
});
