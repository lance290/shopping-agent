'use client';

import { useEffect, useRef, useState } from 'react';
import { Plus, ShoppingBag } from 'lucide-react';
import { useShoppingStore } from '../store';
import RowStrip from './RowStrip';
import { Button } from '../../components/ui/Button';
import { cn } from '../../utils/cn';

export default function ProcurementBoard() {
  const rows = useShoppingStore(state => state.rows);
  const activeRowId = useShoppingStore(state => state.activeRowId);
  const rowResults = useShoppingStore(state => state.rowResults);
  const setActiveRowId = useShoppingStore(state => state.setActiveRowId);
  const pendingRowDelete = useShoppingStore(state => state.pendingRowDelete);
  const undoDeleteRow = useShoppingStore(state => state.undoDeleteRow);
  const [toast, setToast] = useState<{ message: string; tone?: 'success' | 'error' } | null>(null);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showToast = (message: string, tone: 'success' | 'error' = 'success') => {
    setToast({ message, tone });
    if (toastTimerRef.current) {
      clearTimeout(toastTimerRef.current);
    }
    toastTimerRef.current = setTimeout(() => setToast(null), 2400);
  };

  useEffect(() => {
    return () => {
      if (toastTimerRef.current) {
        clearTimeout(toastTimerRef.current);
      }
    };
  }, []);

  return (
    <div className="flex-1 bg-canvas h-full flex flex-col overflow-hidden relative">
      {/* Header / Disclosure */}
      <div className="px-6 py-4 bg-white border-b border-warm-grey flex justify-between items-center z-10 shrink-0">
        <div className="text-xs text-onyx-muted">
          The agent may earn a commission from purchases.
        </div>
        <div className="flex items-center gap-4">
          <div className="text-xs font-semibold text-onyx uppercase tracking-wider">
            {rows.length} active request{rows.length !== 1 ? 's' : ''}
          </div>
          <Button
            size="sm"
            onClick={() => {
              setActiveRowId(null);
              const chatInput = document.querySelector('input[placeholder*="looking for"]') as HTMLInputElement;
              chatInput?.focus();
            }}
            className="flex items-center gap-2"
          >
            <Plus size={16} />
            New Request
          </Button>
        </div>
      </div>
      
      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-5">
        {rows.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-onyx-muted">
            <div className="w-16 h-16 mb-5 rounded-full bg-white border border-warm-grey flex items-center justify-center">
              <ShoppingBag className="w-7 h-7 text-onyx/50" />
            </div>
            <h3 className="text-xl font-semibold text-onyx mb-2">Your Board is Empty</h3>
            <p className="text-sm max-w-sm text-center">
              Start a conversation with the agent to begin finding products.
            </p>
          </div>
        ) : (
          rows.map(row => (
            <RowStrip
              key={row.id}
              row={row}
              offers={rowResults[row.id] || []}
              isActive={row.id === activeRowId}
              onSelect={() => setActiveRowId(row.id)}
              onToast={showToast}
            />
          ))
        )}
      </div>

      {toast && (
        <div className="absolute top-6 right-6 z-50">
          <div className={cn(
            "px-4 py-3 rounded-xl border text-sm font-medium flex items-center gap-2 bg-white shadow-[0_12px_24px_rgba(0,0,0,0.08)]",
            toast.tone === 'error'
              ? "border-status-error/40 text-status-error"
              : "border-status-success/40 text-status-success"
          )}>
            <span>{toast.message}</span>
          </div>
        </div>
      )}

      {pendingRowDelete && (
        <div className="absolute bottom-6 right-6 z-50 bg-white border border-warm-grey shadow-[0_16px_32px_rgba(0,0,0,0.1)] rounded-2xl px-6 py-4 w-[380px]">
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0">
              <div className="text-sm font-semibold text-onyx truncate">
                Archiving “{pendingRowDelete.row.title}”
              </div>
              <div className="text-xs text-onyx-muted mt-1">Undo available for a few seconds.</div>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={undoDeleteRow}
            >
              Undo
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
