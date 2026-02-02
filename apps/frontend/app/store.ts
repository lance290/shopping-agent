import { create } from 'zustand';

export interface Offer {
  title: string;
  price: number;
  currency: string;
  merchant: string;
  url: string;
  image_url: string | null;
  rating: number | null;
  reviews_count: number | null;
  shipping_info: string | null;
  source: string;
  // New fields
  merchant_domain?: string;
  click_url?: string;
  match_score?: number;
  bid_id?: number;
  is_selected?: boolean;
  is_liked?: boolean;
  liked_at?: string; // ISO timestamp when liked
  comment_preview?: string;
  // Vendor/service provider fields
  is_service_provider?: boolean;
  vendor_email?: string;
  vendor_name?: string;
  vendor_company?: string;
}

export type ProviderStatusType = 'ok' | 'error' | 'timeout' | 'exhausted' | 'rate_limited';

export interface ProviderStatusSnapshot {
  provider_id: string;
  status: ProviderStatusType;
  result_count: number;
  latency_ms?: number;
  message?: string;
}

export interface Bid {
  id: number;
  price: number;
  currency: string;
  item_title: string;
  item_url: string | null;
  image_url: string | null;
  source: string;
  is_selected: boolean;
  seller?: {
    name: string;
    domain: string | null;
  };
}

export interface Row {
  id: number;
  title: string;
  status: string;
  budget_max: number | null;
  currency: string;
  choice_factors?: string;   // JSON string
  choice_answers?: string;   // JSON string
  bids?: Bid[];              // Persisted bids from DB
  project_id?: number | null;
  last_engaged_at?: number;  // Client-side timestamp for ordering
}

export interface Project {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

interface PendingRowDelete {
  row: Row;
  rowIndex: number;
  results: Offer[];
  timeoutId: ReturnType<typeof setTimeout>;
  expiresAt: number;
}

// Helper to convert DB Bid to Offer
export function mapBidToOffer(bid: Bid): Offer {
  return {
    title: bid.item_title,
    price: bid.price,
    currency: bid.currency,
    merchant: bid.seller?.name || 'Unknown',
    url: bid.item_url || '#',
    image_url: bid.image_url,
    rating: null, // Not persisted yet
    reviews_count: null,
    shipping_info: null,
    source: bid.source,
    merchant_domain: bid.seller?.domain || undefined,
    click_url: `/api/clickout?url=${encodeURIComponent(bid.item_url || '')}`,
    bid_id: bid.id,
    is_selected: bid.is_selected,
  };
}

// Helper to parse factors
export function parseChoiceFactors(row: Row): any[] {
  if (!row.choice_factors) return [];
  try {
    const parsed = JSON.parse(row.choice_factors);
    if (Array.isArray(parsed)) return parsed;
    if (parsed && typeof parsed === 'object') {
      return Object.entries(parsed).map(([name, value]) => ({
        name,
        ...(value as Record<string, any>),
      }));
    }
    return [];
  } catch {
    return [];
  }
}

export function parseChoiceAnswers(row: Row): Record<string, any> {
  if (!row.choice_answers) return {};
  try {
    return JSON.parse(row.choice_answers);
  } catch {
    return {};
  }
}

export interface ChoiceFactor {
  name: string;
  label: string;
  type: 'number' | 'select' | 'text' | 'boolean';
  options?: string[];
  required: boolean;
}

export type OfferSortMode = 'original' | 'price_asc' | 'price_desc';

// Social features
export interface CommentData {
  id: number;
  user_id: number;
  body: string;
  created_at: string;
}

export interface BidSocialData {
  bid_id: number;
  like_count: number;
  is_liked: boolean;
  comment_count: number;
  comments: CommentData[];
}

// The source of truth state
interface ShoppingState {
  // Core state - SOURCE OF TRUTH
  currentQuery: string;           // The current search query
  activeRowId: number | null;     // The currently selected row ID
  targetProjectId: number | null; // The project ID to create new rows in
  newRowAggressiveness: number;   // 0..100: higher => more likely to start a new row
  rows: Row[];                    // All rows from database
  projects: Project[];            // All projects
  searchResults: Offer[];         // Current search results (legacy view)
  rowResults: Record<number, Offer[]>; // Per-row cached results
  rowProviderStatuses: Record<number, ProviderStatusSnapshot[]>; // Per-row provider statuses
  rowOfferSort: Record<number, OfferSortMode>; // Per-row UI sort mode
  moreResultsIncoming: Record<number, boolean>; // Per-row flag for streaming results
  isSearching: boolean;           // Loading state for search
  cardClickQuery: string | null;  // Query from card click (triggers chat append)

  // Social features state
  bidSocialData: Record<number, BidSocialData>; // Social data by bid_id
  socialDataLoading: Record<number, boolean>;    // Loading state for social data

  // Actions
  setCurrentQuery: (query: string) => void;
  setActiveRowId: (id: number | null) => void;
  setTargetProjectId: (id: number | null) => void;
  setNewRowAggressiveness: (value: number) => void;
  setRows: (rows: Row[]) => void;
  setProjects: (projects: Project[]) => void;
  addProject: (project: Project) => void;
  removeProject: (id: number) => void;
  addRow: (row: Row) => void;
  updateRow: (id: number, updates: Partial<Row>) => void;
  removeRow: (id: number) => void;
  setSearchResults: (results: Offer[]) => void;
  setRowResults: (rowId: number, results: Offer[], providerStatuses?: ProviderStatusSnapshot[], moreIncoming?: boolean) => void;
  appendRowResults: (rowId: number, results: Offer[], providerStatuses?: ProviderStatusSnapshot[], moreIncoming?: boolean) => void;
  clearRowResults: (rowId: number) => void;
  setRowOfferSort: (rowId: number, sort: OfferSortMode) => void;
  setIsSearching: (searching: boolean) => void;
  clearSearch: () => void;
  setCardClickQuery: (query: string | null) => void;  // For card click -> chat append

  // Social actions
  loadBidSocial: (bidId: number) => Promise<void>;
  toggleLike: (bidId: number) => Promise<void>;
  addComment: (bidId: number, body: string) => Promise<void>;
  deleteComment: (bidId: number, commentId: number) => Promise<void>;

  // UI State
  isSidebarOpen: boolean;
  setSidebarOpen: (isOpen: boolean) => void;
  toggleSidebar: () => void;

  isReportBugModalOpen: boolean;
  setReportBugModalOpen: (isOpen: boolean) => void;

  pendingRowDelete: PendingRowDelete | null;
  requestDeleteRow: (rowId: number, undoWindowMs?: number) => void;
  undoDeleteRow: () => void;
  
  // Combined actions for the flow
  selectOrCreateRow: (query: string, existingRows: Row[]) => Row | null;
}

export const useShoppingStore = create<ShoppingState>((set, get) => ({
  // Initial state
  currentQuery: '',
  activeRowId: null,
  targetProjectId: null,
  newRowAggressiveness: 50,
  rows: [],
  projects: [],
  searchResults: [],
  rowResults: {},
  rowProviderStatuses: {},
  rowOfferSort: {},
  moreResultsIncoming: {},
  isSearching: false,
  cardClickQuery: null,
  bidSocialData: {},
  socialDataLoading: {},
  isSidebarOpen: false, // Default closed

  pendingRowDelete: null,
  
  // Basic setters
  setCurrentQuery: (query) => set({ currentQuery: query }),
  setTargetProjectId: (id) => set({ targetProjectId: id }),
  setNewRowAggressiveness: (value) => set({ newRowAggressiveness: Math.max(0, Math.min(100, Math.round(value))) }),
  setActiveRowId: (id) => set((state) => {
    if (id === null) return { activeRowId: id };

    const updatedRows = state.rows.map((row) =>
      row.id === id ? { ...row, last_engaged_at: Date.now() } : row
    );

    return { activeRowId: id, rows: updatedRows };
  }),
  setSidebarOpen: (isOpen) => set({ isSidebarOpen: isOpen }),
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),

  isReportBugModalOpen: false,
  setReportBugModalOpen: (isOpen) => set({ isReportBugModalOpen: isOpen }),

  setProjects: (projects) => set({ projects }),
  addProject: (project) => set((state) => ({ projects: [project, ...state.projects] })),
  removeProject: (id) => set((state) => ({ projects: state.projects.filter((p) => p.id !== id) })),

  requestDeleteRow: (rowId, undoWindowMs = 7000) => {
    const existingPending = get().pendingRowDelete;
    if (existingPending) {
      clearTimeout(existingPending.timeoutId);
      fetch(`/api/rows?id=${existingPending.row.id}`, { method: 'DELETE' }).catch(() => {});
      set((s) => {
        const id = existingPending.row.id;
        const nextRows = s.rows.filter(r => r.id !== id);
        const { [id]: _, ...restResults } = s.rowResults;
        const { [id]: __, ...restStatuses } = s.rowProviderStatuses;
        const nextActive = s.activeRowId === id ? null : s.activeRowId;
        return {
          rows: nextRows,
          rowResults: restResults,
          rowProviderStatuses: restStatuses,
          activeRowId: nextActive,
          pendingRowDelete: null,
        };
      });
    }

    const state = get();
    const rowIndex = state.rows.findIndex(r => r.id === rowId);
    if (rowIndex === -1) return;

    const row = state.rows[rowIndex];
    const results = state.rowResults[rowId] || [];

    const timeoutId = setTimeout(async () => {
      const pending = get().pendingRowDelete;
      if (!pending || pending.row.id !== rowId) return;

      try {
        const res = await fetch(`/api/rows?id=${rowId}`, { method: 'DELETE' });
        if (!res.ok) return;
      } catch {
        return;
      }

      set((s) => {
        const nextRows = s.rows.filter(r => r.id !== rowId);
        const { [rowId]: _, ...restResults } = s.rowResults;
        const { [rowId]: __, ...restStatuses } = s.rowProviderStatuses;
        const nextActive = s.activeRowId === rowId ? null : s.activeRowId;
        return {
          rows: nextRows,
          rowResults: restResults,
          rowProviderStatuses: restStatuses,
          activeRowId: nextActive,
          pendingRowDelete: null,
        };
      });
    }, undoWindowMs);

    set({
      pendingRowDelete: {
        row,
        rowIndex,
        results,
        timeoutId,
        expiresAt: Date.now() + undoWindowMs,
      },
    });
  },

  undoDeleteRow: () => {
    const pending = get().pendingRowDelete;
    if (!pending) return;
    clearTimeout(pending.timeoutId);

    set({ pendingRowDelete: null });
  },
  
  setRows: (rows) => set((state) => {
    // Debug: Log incoming rows and their bids
    console.log('[Store] setRows called with', rows.length, 'rows');
    rows.forEach(r => {
      console.log(`[Store] Row ${r.id} "${r.title}" has ${r.bids?.length || 0} bids`);
    });

    // Preserve last_engaged_at timestamps from existing state
    const existingEngagement = new Map<number, number>();
    state.rows.forEach((r) => {
      if (r.last_engaged_at) {
        existingEngagement.set(r.id, r.last_engaged_at);
      }
    });

    // Merge incoming rows with preserved engagement timestamps
    const mergedRows = rows.map((row) => ({
      ...row,
      last_engaged_at: existingEngagement.get(row.id) || row.last_engaged_at,
    }));

    const orderedRows = [...mergedRows];

    // Automatically hydrate rowResults from persisted bids
    // IMPORTANT: Merge bids with existing rowResults to preserve search results
    const rowIds = new Set(orderedRows.map((row) => row.id));
    const prunedRowResults = Object.fromEntries(
      Object.entries(state.rowResults).filter(([id]) => rowIds.has(Number(id)))
    ) as Record<number, Offer[]>;
    const newRowResults = { ...prunedRowResults };
    const prunedProviderStatuses = Object.fromEntries(
      Object.entries(state.rowProviderStatuses).filter(([id]) => rowIds.has(Number(id)))
    ) as Record<number, ProviderStatusSnapshot[]>;
    orderedRows.forEach(row => {
      if (row.bids && row.bids.length > 0) {
        const bidsAsOffers = row.bids.map(mapBidToOffer);
        const existingResults = newRowResults[row.id] || [];

        // Create a map of existing offers by bid_id for deduplication
        const existingByBidId = new Map<number, Offer>();
        const existingWithoutBidId: Offer[] = [];

        existingResults.forEach(offer => {
          if (offer.bid_id) {
            existingByBidId.set(offer.bid_id, offer);
          } else {
            existingWithoutBidId.push(offer);
          }
        });

        // Update existing offers with fresh bid data or add new bids
        bidsAsOffers.forEach(bidOffer => {
          if (bidOffer.bid_id) {
            existingByBidId.set(bidOffer.bid_id, bidOffer);
          }
        });

        // Merge: bids first (in order), then other search results
        newRowResults[row.id] = [
          ...Array.from(existingByBidId.values()),
          ...existingWithoutBidId
        ];
      }
    });

    return { rows: orderedRows, rowResults: newRowResults, rowProviderStatuses: prunedProviderStatuses };
  }),
  addRow: (row) => set((state) => {
    const newRow = { ...row, last_engaged_at: Date.now() };
    const { [newRow.id]: _, ...restResults } = state.rowResults;
    const { [newRow.id]: __, ...restStatuses } = state.rowProviderStatuses;
    // Add new row at the beginning (most recent)
    return { rows: [newRow, ...state.rows], rowResults: restResults, rowProviderStatuses: restStatuses };
  }),
  updateRow: (id, updates) => set((state) => ({
    rows: state.rows.map((row) => (row.id === id ? { ...row, ...updates } : row)),
  })),
  removeRow: (id) => set((state) => ({
    rows: state.rows.filter((row) => row.id !== id),
    activeRowId: state.activeRowId === id ? null : state.activeRowId,
  })),
  setSearchResults: (results) => set({ searchResults: results, isSearching: false }),
  setRowResults: (rowId, results, providerStatuses, moreIncoming = false) => set((state) => ({
    rowResults: { ...state.rowResults, [rowId]: results },
    rowProviderStatuses: providerStatuses ? { ...state.rowProviderStatuses, [rowId]: providerStatuses } : state.rowProviderStatuses,
    moreResultsIncoming: { ...state.moreResultsIncoming, [rowId]: moreIncoming },
    isSearching: moreIncoming, // Keep searching state while more results incoming
  })),
  appendRowResults: (rowId, results, providerStatuses, moreIncoming = false) => set((state) => {
    const existingResults = state.rowResults[rowId] || [];
    const existingStatuses = state.rowProviderStatuses[rowId] || [];
    // Dedupe by URL
    const seenUrls = new Set(existingResults.map(r => r.url));
    const newResults = results.filter(r => !seenUrls.has(r.url));
    return {
      rowResults: { ...state.rowResults, [rowId]: [...existingResults, ...newResults] },
      rowProviderStatuses: providerStatuses 
        ? { ...state.rowProviderStatuses, [rowId]: [...existingStatuses, ...providerStatuses] }
        : state.rowProviderStatuses,
      moreResultsIncoming: { ...state.moreResultsIncoming, [rowId]: moreIncoming },
      isSearching: moreIncoming,
    };
  }),
  clearRowResults: (rowId) => set((state) => {
    const { [rowId]: _, ...rest } = state.rowResults;
    const { [rowId]: __, ...restStatuses } = state.rowProviderStatuses;
    return { rowResults: rest, rowProviderStatuses: restStatuses };
  }),
  setRowOfferSort: (rowId, sort) => set((state) => {
    if (sort === 'original') {
      const { [rowId]: _, ...rest } = state.rowOfferSort;
      return { rowOfferSort: rest };
    }
    return { rowOfferSort: { ...state.rowOfferSort, [rowId]: sort } };
  }),
  setIsSearching: (searching) => set({ isSearching: searching }),
  clearSearch: () => set({ searchResults: [], rowResults: {}, currentQuery: '', isSearching: false, activeRowId: null, cardClickQuery: null }),
  setCardClickQuery: (query) => set({ cardClickQuery: query }),
  
  // Find a row that matches the query, or return null if we need to create one
  selectOrCreateRow: (query, existingRows) => {
    const lowerQuery = query.toLowerCase().trim();
    const activeRowId = get().activeRowId;
    const targetProjectId = get().targetProjectId;

    const candidateRows = targetProjectId
      ? existingRows.filter((r) => r.project_id === targetProjectId)
      : existingRows;

    // 1. If there's an active row, check if it's a good match for the new query
    // This allows continuing a conversation within the same card.
    if (activeRowId) {
      const activeRow = existingRows.find((r) => r.id === activeRowId);
      if (activeRow) {
        if (!targetProjectId || activeRow.project_id === targetProjectId) {
          const rowTitle = activeRow.title.toLowerCase().trim();
          const rowWords = rowTitle.split(/\s+/).filter((w) => w.length > 3);
          const queryWords = lowerQuery.split(/\s+/).filter((w) => w.length > 3);

          // Check for significant word overlap (at least 2 matching words > 3 chars)
          const overlap = rowWords.filter((w) => queryWords.some((qw) => qw.includes(w) || w.includes(qw)));

          if (lowerQuery.includes(rowTitle) || rowTitle.includes(lowerQuery) || overlap.length >= 2) {
            return activeRow;
          }
        }
      }
    }

    // 2. Try exact match across all rows
    let match = candidateRows.find((r) => r.title.toLowerCase().trim() === lowerQuery);
    if (match) return match;

    // 3. Try partial match (is an existing row title contained in the new query?)
    match = candidateRows.find((r) => {
      const rowTitle = r.title.toLowerCase().trim();
      return lowerQuery.includes(rowTitle);
    });
    if (match) return match;

    // 4. Try reverse partial match (is the new query contained in an existing row title?)
    match = candidateRows.find((r) => {
      const rowTitle = r.title.toLowerCase().trim();
      return rowTitle.includes(lowerQuery);
    });

    return match || null;
  },

  // Social actions
  loadBidSocial: async (bidId) => {
    set((state) => ({
      socialDataLoading: { ...state.socialDataLoading, [bidId]: true },
    }));

    try {
      const res = await fetch(`/api/bids/${bidId}/social`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('session_token') || ''}`,
        },
      });

      if (!res.ok) throw new Error('Failed to load social data');

      const data: BidSocialData = await res.json();
      set((state) => ({
        bidSocialData: { ...state.bidSocialData, [bidId]: data },
        socialDataLoading: { ...state.socialDataLoading, [bidId]: false },
      }));
    } catch (error) {
      console.error('Failed to load social data:', error);
      set((state) => ({
        socialDataLoading: { ...state.socialDataLoading, [bidId]: false },
      }));
    }
  },

  toggleLike: async (bidId) => {
    const currentData = get().bidSocialData[bidId];
    if (!currentData) return;

    // Optimistic update
    const optimisticData: BidSocialData = {
      ...currentData,
      is_liked: !currentData.is_liked,
      like_count: currentData.is_liked
        ? currentData.like_count - 1
        : currentData.like_count + 1,
    };

    set((state) => ({
      bidSocialData: { ...state.bidSocialData, [bidId]: optimisticData },
    }));

    try {
      const res = await fetch(`/api/likes/${bidId}/toggle`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('session_token') || ''}`,
          'Content-Type': 'application/json',
        },
      });

      if (!res.ok) throw new Error('Failed to toggle like');

      const data = await res.json();

      // Update with server response
      set((state) => {
        const current = state.bidSocialData[bidId];
        if (!current) return state;

        return {
          bidSocialData: {
            ...state.bidSocialData,
            [bidId]: {
              ...current,
              is_liked: data.is_liked,
              like_count: data.like_count,
            },
          },
        };
      });
    } catch (error) {
      console.error('Failed to toggle like:', error);
      // Revert optimistic update
      set((state) => ({
        bidSocialData: { ...state.bidSocialData, [bidId]: currentData },
      }));
    }
  },

  addComment: async (bidId, body) => {
    try {
      const res = await fetch(`/api/comments`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('session_token') || ''}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          bid_id: bidId,
          body,
          row_id: 0, // Will be set by backend
        }),
      });

      if (!res.ok) throw new Error('Failed to add comment');

      // Reload social data to get the new comment
      await get().loadBidSocial(bidId);
    } catch (error) {
      console.error('Failed to add comment:', error);
      throw error;
    }
  },

  deleteComment: async (bidId, commentId) => {
    try {
      const res = await fetch(`/api/comments/${commentId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('session_token') || ''}`,
        },
      });

      if (!res.ok) throw new Error('Failed to delete comment');

      // Reload social data to reflect deletion
      await get().loadBidSocial(bidId);
    } catch (error) {
      console.error('Failed to delete comment:', error);
      throw error;
    }
  },
}));

export function shouldForceNewRow(params: {
  message: string;
  activeRowTitle?: string | null;
  aggressiveness: number;
}): boolean {
  const msg = (params.message || '').toLowerCase().trim();
  const activeTitle = (params.activeRowTitle || '').toLowerCase().trim();
  const aggressiveness = Math.max(0, Math.min(100, params.aggressiveness));

  if (!msg || !activeTitle) return false;

  if (aggressiveness < 60) return false;

  const refinementRegex = /\b(over|under|below|above|cheaper|more|less|budget|price)\b|\$\s*\d+|\b\d+\s*(usd|dollars)\b/;
  if (refinementRegex.test(msg)) return false;

  const aWords = new Set(activeTitle.split(/\s+/).filter((w) => w.length > 2));
  const mWords = msg.split(/\s+/).filter((w) => w.length > 2);
  const overlap = mWords.filter((w) => aWords.has(w)).length;
  const denom = Math.max(1, Math.min(aWords.size, mWords.length));
  const similarity = overlap / denom;

  const normalized = (aggressiveness - 60) / 40;
  const threshold = 0.1 + normalized * 0.4;
  return similarity < threshold;
}
