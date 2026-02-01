import { create } from 'zustand';
import { BidWithProvenance, fetchBidWithProvenance } from '../utils/api';

interface DetailPanelState {
  // State
  selectedBidId: number | null;
  isOpen: boolean;
  bidData: BidWithProvenance | null;
  loading: boolean;
  error: string | null;
  retryCount: number;

  // Actions
  openPanel: (bidId: number) => Promise<void>;
  closePanel: () => void;
  fetchBidDetail: (bidId: number) => Promise<void>;
  retryFetch: () => Promise<void>;
  clearError: () => void;
}

const MAX_RETRIES = 3;

export const useDetailPanelStore = create<DetailPanelState>((set, get) => ({
  // Initial state
  selectedBidId: null,
  isOpen: false,
  bidData: null,
  loading: false,
  error: null,
  retryCount: 0,

  // Open panel and fetch bid data
  openPanel: async (bidId: number) => {
    set({
      selectedBidId: bidId,
      isOpen: true,
      loading: true,
      error: null,
      retryCount: 0,
      bidData: null,
    });

    await get().fetchBidDetail(bidId);
  },

  // Close panel and reset state
  closePanel: () => {
    set({
      isOpen: false,
      selectedBidId: null,
      bidData: null,
      loading: false,
      error: null,
      retryCount: 0,
    });
  },

  // Fetch bid detail with error handling
  fetchBidDetail: async (bidId: number) => {
    const state = get();

    if (state.retryCount >= MAX_RETRIES) {
      set({
        loading: false,
        error: 'Maximum retry attempts reached. Please try again later.',
      });
      return;
    }

    set({ loading: true, error: null });

    try {
      const data = await fetchBidWithProvenance(bidId);

      if (!data) {
        set({
          loading: false,
          error: 'Unable to load details. The item may no longer be available.',
        });
        return;
      }

      set({
        bidData: data,
        loading: false,
        error: null,
      });
    } catch (err) {
      console.error('[DetailPanelStore] Error fetching bid:', err);

      let errorMessage = 'Unable to load details. Please try again.';

      if (err instanceof Error) {
        if (err.name === 'TimeoutError') {
          errorMessage = 'Request timed out. Please check your connection and try again.';
        } else if (err.message.includes('Network')) {
          errorMessage = 'Network error. Please check your connection.';
        }
      }

      set({
        loading: false,
        error: errorMessage,
        retryCount: state.retryCount + 1,
      });
    }
  },

  // Retry fetch
  retryFetch: async () => {
    const { selectedBidId } = get();
    if (selectedBidId) {
      await get().fetchBidDetail(selectedBidId);
    }
  },

  // Clear error state
  clearError: () => {
    set({ error: null });
  },
}));
