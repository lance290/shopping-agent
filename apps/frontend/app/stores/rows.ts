/**
 * Row CRUD store: manages rows, projects, and selection logic
 */

import { create } from 'zustand';
import { Row, Project } from './types';

interface PendingRowDelete {
  row: Row;
  rowIndex: number;
  results: any[];
  timeoutId: ReturnType<typeof setTimeout>;
  expiresAt: number;
}

interface RowStoreState {
  // Core state
  activeRowId: number | null;
  targetProjectId: number | null;
  newRowAggressiveness: number;
  rows: Row[];
  projects: Project[];
  pendingRowDelete: PendingRowDelete | null;

  // Actions
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
  requestDeleteRow: (rowId: number, undoWindowMs?: number) => void;
  undoDeleteRow: () => void;
  selectOrCreateRow: (query: string, existingRows: Row[]) => Row | null;
}

export const useRowStore = create<RowStoreState>((set, get) => ({
  // Initial state
  activeRowId: null,
  targetProjectId: null,
  newRowAggressiveness: 50,
  rows: [],
  projects: [],
  pendingRowDelete: null,

  setActiveRowId: (id) => set((state) => {
    if (id === null) return { activeRowId: id };

    const updatedRows = state.rows.map((row) =>
      row.id === id ? { ...row, last_engaged_at: Date.now() } : row
    );

    return { activeRowId: id, rows: updatedRows };
  }),

  setTargetProjectId: (id) => set({ targetProjectId: id }),

  setNewRowAggressiveness: (value) => set({
    newRowAggressiveness: Math.max(0, Math.min(100, Math.round(value)))
  }),

  setProjects: (projects) => set({ projects }),
  addProject: (project) => set((state) => ({ projects: [project, ...state.projects] })),
  removeProject: (id) => set((state) => ({ projects: state.projects.filter((p) => p.id !== id) })),

  setRows: (rows) => set((state) => {
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

    return { rows: [...mergedRows] };
  }),

  addRow: (row) => set((state) => {
    const newRow = { ...row, last_engaged_at: Date.now() };
    return { rows: [newRow, ...state.rows] };
  }),

  updateRow: (id, updates) => set((state) => ({
    rows: state.rows.map((row) => (row.id === id ? { ...row, ...updates } : row)),
  })),

  removeRow: (id) => set((state) => ({
    rows: state.rows.filter((row) => row.id !== id),
    activeRowId: state.activeRowId === id ? null : state.activeRowId,
  })),

  requestDeleteRow: (rowId, undoWindowMs = 7000) => {
    const existingPending = get().pendingRowDelete;
    if (existingPending) {
      clearTimeout(existingPending.timeoutId);
      fetch(`/api/rows?id=${existingPending.row.id}`, { method: 'DELETE' }).catch(() => {});
      set((s) => ({
        rows: s.rows.filter(r => r.id !== existingPending.row.id),
        activeRowId: s.activeRowId === existingPending.row.id ? null : s.activeRowId,
        pendingRowDelete: null,
      }));
    }

    const state = get();
    const rowIndex = state.rows.findIndex(r => r.id === rowId);
    if (rowIndex === -1) return;

    const row = state.rows[rowIndex];

    const timeoutId = setTimeout(async () => {
      const pending = get().pendingRowDelete;
      if (!pending || pending.row.id !== rowId) return;

      try {
        const res = await fetch(`/api/rows?id=${rowId}`, { method: 'DELETE' });
        if (!res.ok) return;
      } catch {
        return;
      }

      set((s) => ({
        rows: s.rows.filter(r => r.id !== rowId),
        activeRowId: s.activeRowId === rowId ? null : s.activeRowId,
        pendingRowDelete: null,
      }));
    }, undoWindowMs);

    set({
      pendingRowDelete: {
        row,
        rowIndex,
        results: [],
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

  selectOrCreateRow: (query, existingRows) => {
    const lowerQuery = query.toLowerCase().trim();
    const activeRowId = get().activeRowId;
    const targetProjectId = get().targetProjectId;

    const candidateRows = targetProjectId
      ? existingRows.filter((r) => r.project_id === targetProjectId)
      : existingRows;

    // 1. If there's an active row, check if it's a good match for the new query
    if (activeRowId) {
      const activeRow = existingRows.find((r) => r.id === activeRowId);
      if (activeRow) {
        if (!targetProjectId || activeRow.project_id === targetProjectId) {
          const rowTitle = activeRow.title.toLowerCase().trim();
          const rowWords = rowTitle.split(/\s+/).filter((w) => w.length > 3);
          const queryWords = lowerQuery.split(/\s+/).filter((w) => w.length > 3);

          const overlap = rowWords.filter((w) => queryWords.some((qw) => qw.includes(w) || w.includes(qw)));

          if (lowerQuery.includes(rowTitle) || rowTitle.includes(lowerQuery) || overlap.length >= 2) {
            return activeRow;
          }
        }
      }
    }

    // 2. Try exact match
    let match = candidateRows.find((r) => r.title.toLowerCase().trim() === lowerQuery);
    if (match) return match;

    // 3. Try partial match
    match = candidateRows.find((r) => {
      const rowTitle = r.title.toLowerCase().trim();
      return lowerQuery.includes(rowTitle);
    });
    if (match) return match;

    // 4. Try reverse partial match
    match = candidateRows.find((r) => {
      const rowTitle = r.title.toLowerCase().trim();
      return rowTitle.includes(lowerQuery);
    });

    return match || null;
  },
}));
