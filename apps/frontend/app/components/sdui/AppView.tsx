'use client';

import { useState } from 'react';
import { useShoppingStore } from '../../store';
import type { Row } from '../../store';
import { DynamicRenderer } from './DynamicRenderer';
import { MinimumViableRow } from './MinimumViableRow';
import { validateUISchema } from '../../sdui/types';

interface AppViewProps {
  children?: React.ReactNode;
}

export function AppView({ children }: AppViewProps) {
  const rows = useShoppingStore((s) => s.rows);
  const activeRowId = useShoppingStore((s) => s.activeRowId);
  const setActiveRowId = useShoppingStore((s) => s.setActiveRowId);
  const [expandedRowId, setExpandedRowId] = useState<number | null>(null);

  return (
    <div className="flex flex-col lg:flex-row h-full min-h-0">
      {/* Chat Pane (left on desktop, top on mobile) */}
      <div className="flex-1 min-h-0 lg:max-w-[50%]">
        {children}
      </div>

      {/* List Pane (right on desktop, bottom tab on mobile) */}
      <div className="flex-1 border-t lg:border-t-0 lg:border-l border-gray-200 overflow-y-auto bg-gray-50/50">
        <div className="p-4">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Your List
          </h2>

          {rows.length === 0 && (
            <div className="text-center py-12 text-gray-400">
              <p className="text-sm">No items yet. Start a conversation to add items.</p>
            </div>
          )}

          <div className="space-y-3">
            {rows.map((row) => (
              <VerticalListRow
                key={row.id}
                row={row}
                isActive={row.id === activeRowId}
                isExpanded={row.id === expandedRowId}
                onSelect={() => setActiveRowId(row.id)}
                onToggleExpand={() => setExpandedRowId(expandedRowId === row.id ? null : row.id)}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

interface VerticalListRowProps {
  row: Row;
  isActive: boolean;
  isExpanded: boolean;
  onSelect: () => void;
  onToggleExpand: () => void;
}

function VerticalListRow({ row, isActive, isExpanded, onSelect, onToggleExpand }: VerticalListRowProps) {
  const hasSchema = row.ui_schema && validateUISchema(row.ui_schema);
  const bidCount = row.bids?.length ?? 0;

  return (
    <div
      className={`bg-white rounded-xl shadow-sm border transition-all ${
        isActive ? 'border-blue-400 ring-1 ring-blue-200' : 'border-gray-200'
      }`}
    >
      {/* Row Header — always visible */}
      <button
        className="w-full text-left px-4 py-3 flex items-center gap-3"
        onClick={() => {
          onSelect();
          onToggleExpand();
        }}
      >
        {/* Status indicator */}
        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
          row.status === 'sourcing' ? 'bg-yellow-400 animate-pulse' :
          row.status === 'closed' || row.status === 'delivered' ? 'bg-green-400' :
          'bg-blue-400'
        }`} />

        {/* Title + meta */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">{row.title}</p>
          <p className="text-xs text-gray-500">
            {row.status === 'sourcing' ? 'Searching...' :
             bidCount > 0 ? `${bidCount} option${bidCount !== 1 ? 's' : ''}` :
             row.status}
          </p>
        </div>

        {/* Expand chevron */}
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expanded Content — SDUI rendered */}
      {isExpanded && (
        <div className="border-t border-gray-100 px-4 py-3">
          {hasSchema ? (
            <DynamicRenderer
              schema={row.ui_schema}
              fallbackTitle={row.title}
              fallbackStatus={row.status}
            />
          ) : (
            <MinimumViableRow title={row.title} status={row.status} />
          )}
        </div>
      )}
    </div>
  );
}
