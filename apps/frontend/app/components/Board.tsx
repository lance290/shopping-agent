'use client';

import { useShoppingStore } from '../store';
import RowStrip from './RowStrip';

export default function ProcurementBoard() {
  const rows = useShoppingStore(state => state.rows);
  const activeRowId = useShoppingStore(state => state.activeRowId);
  const rowResults = useShoppingStore(state => state.rowResults);
  const setActiveRowId = useShoppingStore(state => state.setActiveRowId);
  const pendingRowDelete = useShoppingStore(state => state.pendingRowDelete);
  const undoDeleteRow = useShoppingStore(state => state.undoDeleteRow);

  return (
    <div className="flex-1 bg-gray-50 h-full flex flex-col overflow-hidden">
      {/* Header / Disclosure */}
      <div className="p-3 bg-white border-b border-gray-200 flex justify-between items-center shadow-sm z-10 shrink-0">
        <div className="text-xs text-gray-500">
          <strong>Disclosure:</strong> We may earn a commission from qualifying purchases. 
          <a href="/disclosure" className="ml-1 text-blue-500 hover:underline" target="_blank">Learn more</a>
        </div>
        <div className="text-xs font-medium text-gray-600">
          {rows.length} active request{rows.length !== 1 ? 's' : ''}
        </div>
      </div>
      
      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {rows.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-gray-400">
            <div className="w-16 h-16 mb-4 rounded-full bg-gray-100 flex items-center justify-center">
              <span className="text-2xl">🛍️</span>
            </div>
            <p className="text-lg font-medium text-gray-600">Your Procurement Board is Empty</p>
            <p className="text-sm mt-2 max-w-xs text-center">
              Tell the agent what you need in the chat on the left to start a new procurement request.
            </p>
          </div>
        ) : (
          /* Render rows in reverse order (newest top) */
          [...rows].reverse().map(row => (
            <RowStrip
              key={row.id}
              row={row}
              offers={rowResults[row.id] || []}
              isActive={row.id === activeRowId}
              onSelect={() => setActiveRowId(row.id)}
            />
          ))
        )}
      </div>

      {pendingRowDelete && (
        <div className="fixed bottom-4 right-4 z-50 bg-white border border-gray-200 shadow-lg rounded-lg px-4 py-3 w-[360px]">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="text-sm font-medium text-gray-900 truncate">
                Archived “{pendingRowDelete.row.title}”
              </div>
              <div className="text-xs text-gray-500 mt-0.5">
                Undo available for a few seconds.
              </div>
            </div>
            <button
              onClick={undoDeleteRow}
              className="shrink-0 text-sm font-semibold text-blue-600 hover:text-blue-700"
            >
              Undo
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
