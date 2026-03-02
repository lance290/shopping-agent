'use client';

import { useEffect, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import Chat from './components/Chat';
import { AppView } from './components/sdui';
import ReportBugModal from './components/ReportBugModal';
import { useShoppingStore } from './store';
import { fetchSingleRowFromDb, runSearchApiWithStatus, createRowInDb, fetchRowsFromDb } from './utils/api';

export default function Home() {
  const searchParams = useSearchParams();
  const store = useShoppingStore();
  const hasHandledQueryRef = useRef(false);

  // Handle shared search link (query parameter)
  useEffect(() => {
    const queries = searchParams?.getAll('q') || [];
    if (queries.length === 0 || hasHandledQueryRef.current) return;

    hasHandledQueryRef.current = true;

    const handleSharedSearch = async () => {
      try {
        if (store.rows.length === 0) {
          const rows = await fetchRowsFromDb();
          if (rows) store.setRows(rows);
        }

        for (const query of queries) {
          let targetRow = store.rows.find((r) => r.title === query);
          if (!targetRow) {
            const created = await createRowInDb(query, null);
            if (created) {
              store.addRow(created);
              targetRow = created;
            }
          }
          if (targetRow) {
            if (queries.length === 1) {
              store.setActiveRowId(targetRow.id);
              store.setCurrentQuery(query);
            }
            const existingResults = store.rowResults[targetRow.id];
            if (!existingResults || existingResults.length === 0) {
              store.setIsSearching(true);
              const res = await runSearchApiWithStatus(null, targetRow.id);
              store.setRowResults(targetRow.id, res.results, res.providerStatuses);
              const freshRow = await fetchSingleRowFromDb(targetRow.id);
              if (freshRow) store.updateRow(targetRow.id, freshRow);
            }
          }
        }

        if (queries.length > 1) {
          const firstRow = store.rows.find((r) => r.title === queries[0]);
          if (firstRow) {
            store.setActiveRowId(firstRow.id);
            store.setCurrentQuery(queries[0]);
          }
        }
      } catch (err) {
        console.error('[Home] Failed to handle shared search:', err);
      } finally {
        store.setIsSearching(false);
      }
    };

    handleSharedSearch();
  }, [searchParams, store]);

  return (
    <main className="h-[100dvh] w-full overflow-hidden font-sans">
      <AppView>
        <Chat />
      </AppView>
      <ReportBugModal />
    </main>
  );
}
