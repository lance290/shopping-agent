'use client';

import { useState, useEffect } from 'react';
import { useShoppingStore, mapBidToOffer } from '../../store';
import type { Row, Offer } from '../../store';
import { createProjectInDb } from '../../utils/api';
import { Bug, FolderPlus } from 'lucide-react';
import { DynamicRenderer } from './DynamicRenderer';
import { validateUISchema } from '../../sdui/types';

interface AppViewProps {
  children?: React.ReactNode;
}

export function AppView({ children }: AppViewProps) {
  const rows = useShoppingStore((s) => s.rows);
  const projects = useShoppingStore((s) => s.projects);
  const activeRowId = useShoppingStore((s) => s.activeRowId);
  const setActiveRowId = useShoppingStore((s) => s.setActiveRowId);
  const rowResults = useShoppingStore((s) => s.rowResults);
  const addProject = useShoppingStore((s) => s.addProject);
  const setTargetProjectId = useShoppingStore((s) => s.setTargetProjectId);
  const setReportBugModalOpen = useShoppingStore((s) => s.setReportBugModalOpen);
  const [expandedRowId, setExpandedRowId] = useState<number | null>(null);
  const [collapsedProjects, setCollapsedProjects] = useState<Record<number | string, boolean>>({});
  const [isProd, setIsProd] = useState(true);

  // Check environment on mount
  useEffect(() => {
    const hostname = window.location.hostname;
    // Show bug reporter on localhost, dev, staging, etc.
    if (
      hostname === 'localhost' ||
      hostname === '127.0.0.1' ||
      hostname.includes('dev') ||
      hostname.includes('staging')
    ) {
      setIsProd(false);
    } else {
      setIsProd(true);
    }
  }, []);

  const targetProjectId = useShoppingStore((s) => s.targetProjectId);

  // Filter out archived/cancelled rows
  const activeRows = rows.filter((r) => r.status !== 'archived' && r.status !== 'cancelled');

  // Group rows by project_id
  const grouped: Record<number, Row[]> = {};
  const ungrouped: Row[] = [];
  for (const row of activeRows) {
    if (row.project_id) {
      if (!grouped[row.project_id]) grouped[row.project_id] = [];
      grouped[row.project_id].push(row);
    } else {
      ungrouped.push(row);
    }
  }

  const handleCreateProject = async () => {
    const title = window.prompt('Enter project name:');
    if (!title || !title.trim()) return;

    const newProject = await createProjectInDb(title.trim());
    if (newProject) {
      addProject(newProject);
      setTargetProjectId(newProject.id);
    } else {
      alert('Failed to create project');
    }
  };

  const renderRow = (row: Row) => (
    <VerticalListRow
      key={row.id}
      row={row}
      offers={rowResults[row.id] || []}
      isActive={row.id === activeRowId}
      isExpanded={row.id === expandedRowId}
      onSelect={() => setActiveRowId(row.id)}
      onToggleExpand={() => setExpandedRowId(expandedRowId === row.id ? null : row.id)}
    />
  );

  return (
    <div className="flex flex-col lg:flex-row h-[100dvh] w-full overflow-hidden">
      {/* Chat Pane */}
      <div className="flex-[0_0_50vh] lg:flex-[0_0_400px] xl:flex-[0_0_500px] min-h-0 flex flex-col border-b lg:border-b-0 lg:border-r border-gray-200 z-10">
        {children}
      </div>

      {/* List Pane */}
      <div className="flex-1 min-w-0 overflow-y-auto bg-gray-50/50">
        <div className="p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
              Your List
            </h2>
            <div className="flex items-center gap-2">
              <button
                onClick={handleCreateProject}
                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
              >
                <FolderPlus size={14} />
                New Project
              </button>
              {!isProd && (
                <button
                  onClick={() => setReportBugModalOpen(true)}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
                  title="Report Bug"
                >
                  <Bug size={14} />
                  Report Bug
                </button>
              )}
            </div>
          </div>

          {activeRows.length === 0 && (
            <div className="text-center py-12 text-gray-400">
              <p className="text-sm">No items yet. Start a conversation to add items.</p>
            </div>
          )}

          {/* Project-grouped rows */}
          {projects.map((project) => {
            const projectRows = grouped[project.id];
            if (!projectRows || projectRows.length === 0) return null;
            const isCollapsed = collapsedProjects[project.id];
            
            return (
              <div key={project.id} className="mb-4">
                <button
                  onClick={() => setCollapsedProjects(prev => ({ ...prev, [project.id]: !isCollapsed }))}
                  className="w-full flex items-center justify-between mb-2 pb-1 border-b border-gray-200 group hover:border-blue-300 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                    </svg>
                    <span className="text-xs font-semibold text-gray-700 uppercase tracking-wide group-hover:text-blue-700 transition-colors">{project.title}</span>
                    <span className="text-xs text-gray-400">{projectRows.length} item{projectRows.length !== 1 ? 's' : ''}</span>
                    {targetProjectId === project.id && (
                      <span className="ml-2 px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 text-[10px] font-bold uppercase tracking-wider">
                        Active
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (targetProjectId === project.id) {
                          setTargetProjectId(null);
                        } else {
                          setTargetProjectId(project.id);
                        }
                      }}
                      className="opacity-0 group-hover:opacity-100 px-2 py-1 text-xs text-blue-600 hover:bg-blue-50 rounded transition-all"
                    >
                      {targetProjectId === project.id ? 'Cancel Add' : '+ Add Item'}
                    </button>
                    <svg className={`w-4 h-4 text-gray-400 transition-transform ${isCollapsed ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                </button>
                {!isCollapsed && (
                  <div className="space-y-2 pl-2 border-l-2 border-blue-100">
                    {projectRows.map(renderRow)}
                  </div>
                )}
              </div>
            );
          })}

          {/* Ungrouped rows */}
          {ungrouped.length > 0 && (() => {
            const isCollapsed = collapsedProjects['ungrouped'];
            return (
              <div className="mb-4">
                {projects.length > 0 && (
                  <button
                    onClick={() => setCollapsedProjects(prev => ({ ...prev, ungrouped: !isCollapsed }))}
                    className="w-full flex items-center justify-between mb-2 pb-1 border-b border-gray-200 group hover:border-blue-300 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide group-hover:text-blue-700 transition-colors">Other Requests</span>
                      <span className="text-xs text-gray-400">{ungrouped.length} item{ungrouped.length !== 1 ? 's' : ''}</span>
                    </div>
                    <svg className={`w-4 h-4 text-gray-400 transition-transform ${isCollapsed ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                )}
                {(!isCollapsed || projects.length === 0) && (
                  <div className="space-y-2">
                    {ungrouped.map(renderRow)}
                  </div>
                )}
              </div>
            );
          })()}
        </div>
      </div>
    </div>
  );
}

interface VerticalListRowProps {
  row: Row;
  offers: Offer[];
  isActive: boolean;
  isExpanded: boolean;
  onSelect: () => void;
  onToggleExpand: () => void;
}

function VerticalListRow({ row, offers, isActive, isExpanded, onSelect, onToggleExpand }: VerticalListRowProps) {
  const hasSchema = !!(row.ui_schema && validateUISchema(row.ui_schema));
  const bidCount = row.bids?.length ?? 0;
  const displayOffers = offers.length > 0 ? offers : (row.bids || []).map(mapBidToOffer);

  return (
    <div
      className={`bg-white rounded-xl shadow-sm border transition-all ${
        isActive ? 'border-blue-400 ring-1 ring-blue-200' : 'border-gray-200'
      }`}
    >
      {/* Row Header */}
      <button
        className="w-full text-left px-4 py-3 flex items-center gap-3"
        onClick={() => { onSelect(); onToggleExpand(); }}
      >
        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
          row.status === 'sourcing' ? 'bg-yellow-400 animate-pulse' :
          row.status === 'closed' || row.status === 'delivered' ? 'bg-green-400' :
          'bg-blue-400'
        }`} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">{row.title}</p>
          <p className="text-xs text-gray-500">
            {row.status === 'sourcing' ? 'Searching...' :
             bidCount > 0 ? `${bidCount} option${bidCount !== 1 ? 's' : ''}` :
             row.status}
          </p>
        </div>
        <svg className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expanded: show SDUI schema + ALL bids as cards */}
      {isExpanded && (
        <div className="border-t border-gray-100 px-4 py-3 space-y-4 max-h-[600px] overflow-y-auto">
          {hasSchema && (
            <div className="mb-4">
              <DynamicRenderer
                schema={row.ui_schema}
                fallbackTitle={row.title}
                fallbackStatus={row.status}
              />
            </div>
          )}
          
          <div className="space-y-2">
            {displayOffers.length === 0 && !hasSchema && (
              <p className="text-sm text-gray-400 italic">No options found yet.</p>
            )}
            {displayOffers.map((offer, i) => (
              <BidCard key={offer.bid_id ?? i} offer={offer} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function BidCard({ offer }: { offer: Offer }) {
  const priceStr = offer.price !== null && offer.price !== undefined
    ? `$${offer.price.toFixed(2)}`
    : 'Request Quote';

  return (
    <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors">
      {offer.image_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={offer.image_url} alt={offer.title} className="w-12 h-12 rounded-md object-cover bg-gray-100 flex-shrink-0" />
      ) : (
        <div className="w-12 h-12 rounded-md bg-gray-100 flex-shrink-0 flex items-center justify-center">
          <svg className="w-5 h-5 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        </div>
      )}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-800 truncate">{offer.title}</p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-sm font-semibold text-gray-900">{priceStr}</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-500">{offer.source}</span>
          {offer.merchant && offer.merchant !== 'Unknown' && (
            <span className="text-[10px] text-gray-400">{offer.merchant}</span>
          )}
        </div>
      </div>
      {offer.url && offer.url !== '#' && (
        <a
          href={offer.click_url || `/api/out?url=${encodeURIComponent(offer.url)}`}
          target="_blank"
          rel="noopener noreferrer"
          className="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex-shrink-0"
        >
          View Deal
        </a>
      )}
    </div>
  );
}
