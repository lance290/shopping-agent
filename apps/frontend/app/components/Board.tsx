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
    <div className="flex-1 bg-warm-light/50 h-full flex flex-col overflow-hidden relative">
      {/* Header / Disclosure */}
      <div className="px-6 py-4 bg-white/80 backdrop-blur-md border-b border-warm-grey/50 flex justify-between items-center shadow-sm z-10 shrink-0">
        <div className="flex items-center gap-4">
          <div className="text-xs font-serif italic text-onyx-muted">
            The Agent may earn a commission from purchases.
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-xs font-medium text-onyx uppercase tracking-wider">
            {rows.length} active request{rows.length !== 1 ? 's' : ''}
          </div>
          <Button
            size="sm"
            onClick={() => {
              setActiveRowId(null);
              const chatInput = document.querySelector('input[placeholder*="looking for"]') as HTMLInputElement;
              chatInput?.focus();
            }}
            className="flex items-center gap-2 rounded-lg"
          >
            <Plus size={16} />
            New Request
          </Button>
        </div>
      </div>
      
      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {rows.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-onyx-muted">
            <div className="w-20 h-20 mb-6 rounded-full bg-white border border-warm-grey flex items-center justify-center shadow-sm">
              <ShoppingBag className="w-8 h-8 text-onyx/50" />
            </div>
            <h3 className="text-2xl font-serif text-onyx mb-2">Your Board is Empty</h3>
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
        <div className="absolute top-6 right-6 z-50 animate-in fade-in slide-in-from-top-4 duration-300">
          <div className={cn(
            "px-4 py-3 rounded-lg shadow-lg border text-sm font-medium flex items-center gap-2 backdrop-blur-md",
            toast.tone === 'error'
              ? "bg-status-error/10 border-status-error/20 text-status-error"
              : "bg-status-success/10 border-status-success/20 text-status-success"
          )}>
            <span>{toast.message}</span>
          </div>
        </div>
      )}

      {pendingRowDelete && (
        <div className="absolute bottom-6 right-6 z-50 bg-onyx text-white shadow-xl rounded-xl px-6 py-4 w-[400px] animate-in slide-in-from-bottom-4 duration-300">
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0">
              <div className="text-sm font-medium truncate">
                Archiving “{pendingRowDelete.row.title}”
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={undoDeleteRow}
              className="text-agent-blurple hover:text-white hover:bg-white/10"
            >
              Undo
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
