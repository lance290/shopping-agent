'use client';

import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Chat from './components/Chat';
import ProcurementBoard from './components/Board';
import ReportBugModal from './components/ReportBugModal';
import { cn } from '../utils/cn';
import { useShoppingStore } from './store';
import { fetchSingleRowFromDb, runSearchApiWithStatus, createRowInDb, fetchRowsFromDb } from './utils/api';
import { MessageSquare, LayoutGrid } from 'lucide-react';

export default function Home() {
  const CHAT_MIN_PX = 360;
  const CHAT_MAX_PX = 700;
  const CHAT_DEFAULT_PX = 450;

  const searchParams = useSearchParams();
  const store = useShoppingStore();
  const [chatWidthPx, setChatWidthPx] = useState<number>(CHAT_DEFAULT_PX);
  const isDraggingRef = useRef(false);
  const dragStartXRef = useRef<number>(0);
  const dragStartWidthRef = useRef<number>(CHAT_DEFAULT_PX);
  const latestWidthRef = useRef<number>(CHAT_DEFAULT_PX);
  const hasHandledQueryRef = useRef(false);
  const [mobilePane, setMobilePane] = useState<'chat' | 'board'>('chat');
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

  useEffect(() => {
    try {
      const raw = localStorage.getItem('chatWidthPx');
      if (!raw) return;
      const parsed = Number(raw);
      if (!Number.isFinite(parsed)) return;
      setChatWidthPx(Math.min(CHAT_MAX_PX, Math.max(CHAT_MIN_PX, parsed)));
    } catch {
      // ignore
    }
  }, []);

  // Handle shared search link (query parameter)
  useEffect(() => {
    const queries = searchParams?.getAll('q') || [];
    if (queries.length === 0 || hasHandledQueryRef.current) return;

    hasHandledQueryRef.current = true;

    const handleSharedSearch = async () => {
      try {
        // Load rows first if not loaded
        if (store.rows.length === 0) {
          const rows = await fetchRowsFromDb();
          if (rows) {
            store.setRows(rows);
          }
        }

        // Process all queries (for board sharing with multiple searches)
        for (const query of queries) {
          // Find existing row or create new one
          let targetRow = store.rows.find((r) => r.title === query);

          if (!targetRow) {
            const created = await createRowInDb(query, null);
            if (created) {
              store.addRow(created);
              targetRow = created;
            }
          }

          if (targetRow) {
            // For single query, set as active; for multiple, just create them
            if (queries.length === 1) {
              store.setActiveRowId(targetRow.id);
              store.setCurrentQuery(query);
            }

            // Run search if no results exist
            const existingResults = store.rowResults[targetRow.id];
            if (!existingResults || existingResults.length === 0) {
              store.setIsSearching(true);
              const res = await runSearchApiWithStatus(null, targetRow.id);
              store.setRowResults(targetRow.id, res.results, res.providerStatuses);
              const freshRow = await fetchSingleRowFromDb(targetRow.id);
              if (freshRow) {
                store.updateRow(targetRow.id, freshRow);
              }
            }
          }
        }

        // For multiple queries, set the first one as active
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

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!isDraggingRef.current) return;
      const delta = e.clientX - dragStartXRef.current;
      const next = Math.min(CHAT_MAX_PX, Math.max(CHAT_MIN_PX, dragStartWidthRef.current + delta));
      latestWidthRef.current = next;
      setChatWidthPx(next);
    };

    const onUp = () => {
      if (!isDraggingRef.current) return;
      isDraggingRef.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      try {
        localStorage.setItem('chatWidthPx', String(latestWidthRef.current));
      } catch {
        // ignore
      }
    };

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, []);

  // Mobile layout: tabbed chat/board with bottom nav
  if (isMobile) {
    return (
      <main className="flex flex-col h-screen w-full bg-transparent text-onyx overflow-hidden font-sans selection:bg-agent-blurple/15 selection:text-agent-blurple">
        <div className="flex-1 min-h-0 overflow-hidden">
          {mobilePane === 'chat' ? <Chat /> : <ProcurementBoard />}
        </div>

        {/* Bottom Navigation */}
        <nav className="shrink-0 flex border-t border-warm-grey/60 bg-white safe-area-bottom">
          <button
            onClick={() => setMobilePane('chat')}
            className={cn(
              "flex-1 flex flex-col items-center gap-0.5 py-2.5 text-[10px] font-semibold transition-colors",
              mobilePane === 'chat'
                ? "text-agent-blurple"
                : "text-onyx-muted"
            )}
          >
            <MessageSquare size={20} />
            Chat
          </button>
          <button
            onClick={() => setMobilePane('board')}
            className={cn(
              "flex-1 flex flex-col items-center gap-0.5 py-2.5 text-[10px] font-semibold transition-colors",
              mobilePane === 'board'
                ? "text-agent-blurple"
                : "text-onyx-muted"
            )}
          >
            <LayoutGrid size={20} />
            Board
          </button>
        </nav>

        <ReportBugModal />
      </main>
    );
  }

  // Desktop layout: split pane
  return (
    <main className="flex h-screen w-full bg-transparent text-onyx overflow-hidden font-sans selection:bg-agent-blurple/15 selection:text-agent-blurple">
      {/* Chat Pane (Center Left) */}
      <div 
        style={{ width: `${chatWidthPx}px` }} 
        className="h-full shrink-0 z-10 relative"
      >
        <Chat />
      </div>

      {/* Draggable Handle */}
      <div
        className={cn(
          "w-px h-full cursor-col-resize z-30 transition-colors duration-200 relative group bg-warm-grey/70 hover:bg-onyx/40",
          isDraggingRef.current ? "bg-agent-blurple" : ""
        )}
        onMouseDown={(e) => {
          e.preventDefault();
          isDraggingRef.current = true;
          dragStartXRef.current = e.clientX;
          dragStartWidthRef.current = chatWidthPx;
          latestWidthRef.current = chatWidthPx;
          document.body.style.cursor = 'col-resize';
          document.body.style.userSelect = 'none';
        }}
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize chat"
      >
        <div className="absolute inset-y-0 -left-2 -right-2 z-30" />
      </div>
      
      {/* Board Pane (Right) */}
      <div className="flex-1 min-w-0 bg-transparent h-full relative z-0">
        <ProcurementBoard />
      </div>

      <ReportBugModal />
    </main>
  );
}
