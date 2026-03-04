'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useShoppingStore, mapBidToOffer } from '../../store';
import type { Row, Offer } from '../../store';
import { createProjectInDb, duplicateProjectInDb, runSearchApiWithStatus } from '../../utils/api';
import { Bug, FolderPlus, Trash2, RotateCw, Copy } from 'lucide-react';
import { DynamicRenderer } from './DynamicRenderer';
import { validateUISchema } from '../../sdui/types';
import VendorContactModal from '../VendorContactModal';
import { getMe } from '../../utils/auth';

interface AppViewProps {
  children?: React.ReactNode;
}

const TRENDING_SEARCHES = [
  'Robot lawn mowers',
  'Standing desks under $600',
  'Air purifiers for wildfire smoke',
  'Portable power stations',
  'Private jet charter',
  'Luxury yacht charter',
  'Bespoke menswear',
  'Executive relocation concierge',
];

const GUIDE_LINKS = [
  {
    title: 'Private aviation: charter vs. fractional vs. jet card',
    slug: 'private-aviation',
    image: 'https://images.unsplash.com/photo-1540962351504-03099e0a754b?auto=format&fit=crop&w=800&q=80',
  },
  {
    title: 'Sourcing bespoke menswear in 2025',
    slug: 'bespoke-menswear',
    image: 'https://images.unsplash.com/photo-1593030103066-0093718efeb9?auto=format&fit=crop&w=800&q=80',
  },
  {
    title: 'Art acquisition for new collectors',
    slug: 'art-acquisition',
    image: 'https://images.unsplash.com/photo-1544413158-b64db6e64ec6?auto=format&fit=crop&w=800&q=80',
  },
  {
    title: 'Executive relocation: vendor vetting checklist',
    slug: 'executive-relocation',
    image: 'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=800&q=80',
  },
];

export function AppView({ children }: AppViewProps) {
  const rows = useShoppingStore((s) => s.rows);
  const projects = useShoppingStore((s) => s.projects);
  const activeRowId = useShoppingStore((s) => s.activeRowId);
  const setActiveRowId = useShoppingStore((s) => s.setActiveRowId);
  const rowResults = useShoppingStore((s) => s.rowResults);
  const addProject = useShoppingStore((s) => s.addProject);
  const setCardClickQuery = useShoppingStore((s) => s.setCardClickQuery);
  const setTargetProjectId = useShoppingStore((s) => s.setTargetProjectId);
  const setReportBugModalOpen = useShoppingStore((s) => s.setReportBugModalOpen);
  const pendingRowDelete = useShoppingStore((s) => s.pendingRowDelete);
  const undoDeleteRow = useShoppingStore((s) => s.undoDeleteRow);
  const [expandedRowId, setExpandedRowId] = useState<number | null>(null);
  const [collapsedProjects, setCollapsedProjects] = useState<Record<number | string, boolean>>({});
  const [isProd, setIsProd] = useState(true);
  const [isTipJarLoading, setIsTipJarLoading] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

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

  useEffect(() => {
    let mounted = true;
    getMe()
      .then((me) => {
        if (!mounted) return;
        setIsAuthenticated(Boolean(me?.authenticated));
      })
      .catch(() => {
        if (!mounted) return;
        setIsAuthenticated(false);
      });
    return () => {
      mounted = false;
    };
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

  const handleDuplicateProject = async (e: React.MouseEvent, projectId: number) => {
    e.stopPropagation();
    const newProject = await duplicateProjectInDb(projectId);
    if (newProject) {
      addProject(newProject);
      setTargetProjectId(newProject.id);
      // We trigger a full reload to get the newly duplicated rows
      // since the duplicate endpoint creates them all on the backend
      window.location.reload();
    } else {
      alert('Failed to duplicate list');
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

  const handleIntentClick = (query: string) => {
    setCardClickQuery(query);
  };

  return (
    <div className="flex flex-col lg:flex-row h-[100dvh] w-full overflow-hidden relative">
      {/* Undo Toast */}
      {pendingRowDelete && (
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-[100] bg-gray-900 text-white px-4 py-3 rounded-xl shadow-2xl flex items-center gap-4 animate-in fade-in slide-in-from-bottom-4">
          <div className="text-sm font-medium">
            Deleted &quot;{pendingRowDelete.row.title}&quot;
          </div>
          <button
            onClick={undoDeleteRow}
            className="text-sm font-bold text-blue-400 hover:text-blue-300 transition-colors bg-white/10 px-3 py-1.5 rounded-lg"
          >
            Undo
          </button>
        </div>
      )}

      {/* Chat Pane */}
      <div className="flex-[0_0_50vh] lg:flex-[0_0_400px] xl:flex-[0_0_500px] min-h-0 flex flex-col border-b lg:border-b-0 lg:border-r border-gray-200 z-10">
        {children}
      </div>

      {/* List Pane */}
      <div className="flex-1 min-w-0 overflow-y-auto bg-gray-50/50">
        {isAuthenticated !== true ? (
          <div className="p-6 space-y-8 bg-gradient-to-b from-[#111827] via-[#1f2937] to-[#111827] text-slate-100 min-h-full">
            <section className="rounded-3xl border border-white/10 bg-white/5 backdrop-blur-sm p-7 shadow-2xl">
              <p className="text-xs uppercase tracking-[0.35em] text-slate-400 mb-3">BuyAnything</p>
              <h2 className="text-3xl font-semibold text-white leading-tight">Every purchase decision, handled.</h2>
              <p className="mt-3 text-sm text-slate-300 max-w-2xl">
                Tell the chat what you need. We’ll infer intent, compare options, and keep your shortlist
                tidy once you sign in.
              </p>
              <div className="mt-5 grid gap-3 sm:grid-cols-3">
                <div className="rounded-2xl bg-gradient-to-br from-sky-500/20 to-cyan-500/10 border border-sky-300/20 p-4">
                  <p className="text-xs uppercase tracking-wider text-sky-200/80">Intent-first</p>
                  <p className="mt-1 text-sm font-medium text-white">Natural language prompts</p>
                </div>
                <div className="rounded-2xl bg-gradient-to-br from-violet-500/20 to-fuchsia-500/10 border border-violet-300/20 p-4">
                  <p className="text-xs uppercase tracking-wider text-violet-200/80">Multi-source</p>
                  <p className="mt-1 text-sm font-medium text-white">Retail + specialist vendors</p>
                </div>
                <div className="rounded-2xl bg-gradient-to-br from-emerald-500/20 to-green-500/10 border border-emerald-300/20 p-4">
                  <p className="text-xs uppercase tracking-wider text-emerald-200/80">Anonymous-first</p>
                  <p className="mt-1 text-sm font-medium text-white">Search now, save later</p>
                </div>
              </div>
              <div className="mt-5 flex flex-wrap gap-3">
                <Link className="btn-secondary" href="/guides">Browse guides</Link>
                <Link className="btn-secondary" href="/vendors">Explore vendors</Link>
              </div>
            </section>

            <section>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wide">Trending intents</h3>
                <span className="text-xs text-slate-500 uppercase tracking-widest">Tap to ask chat</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {TRENDING_SEARCHES.map((label) => (
                  <button
                    key={label}
                    type="button"
                    onClick={() => handleIntentClick(label)}
                    className="rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm text-slate-100 hover:bg-white/20"
                  >
                    {label}
                  </button>
                ))}
              </div>
            </section>

            <section>
              <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wide mb-3">Editorial guides</h3>
              <div className="grid gap-3 md:grid-cols-2">
                {GUIDE_LINKS.map((guide) => (
                  <div key={guide.slug} className="rounded-2xl border border-white/10 bg-white/5 overflow-hidden">
                    <div className="h-28 w-full bg-slate-800">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={guide.image} alt={guide.title} className="h-full w-full object-cover opacity-90" />
                    </div>
                    <div className="p-4">
                    <Link
                      href={`/guides/${guide.slug}`}
                      className="block text-sm font-medium text-white hover:text-sky-200"
                    >
                      {guide.title}
                    </Link>
                    <div className="mt-3 flex items-center gap-3 text-xs">
                      <Link href={`/guides/${guide.slug}`} className="text-sky-200 hover:text-sky-100">
                        Read guide
                      </Link>
                      <button
                        type="button"
                        onClick={() => handleIntentClick(guide.title)}
                        className="text-slate-300 hover:text-white"
                      >
                        Ask chat →
                      </button>
                    </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>
        ) : (
        <div className="p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
              Your List
            </h2>
            <div className="flex items-center gap-2">
              <button
                onClick={async () => {
                  if (isTipJarLoading) return;
                  setIsTipJarLoading(true);
                  try {
                    const res = await fetch('/api/tip-jar', { method: 'POST' });
                    const data = await res.json();
                    if (!res.ok) {
                      throw new Error(data?.detail || 'Failed to create tip jar session');
                    }
                    if (data?.checkout_url) {
                      window.location.href = data.checkout_url;
                    }
                  } catch (error) {
                    console.error('[tip-jar] failed to create session', error);
                  } finally {
                    setIsTipJarLoading(false);
                  }
                }}
                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-amber-900 bg-amber-100 rounded-lg hover:bg-amber-200 transition-colors disabled:opacity-60"
                title="Support our team"
                disabled={isTipJarLoading}
              >
                <span>☕️</span>
                {isTipJarLoading ? 'Opening…' : 'Tip Jar'}
              </button>
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
                    <button
                      onClick={(e) => handleDuplicateProject(e, project.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-blue-600 rounded transition-colors"
                      title="Duplicate List"
                    >
                      <Copy size={14} />
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
        )}
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
  
  const requestDeleteRow = useShoppingStore((s) => s.requestDeleteRow);
  const setIsSearching = useShoppingStore((s) => s.setIsSearching);
  const setRowResults = useShoppingStore((s) => s.setRowResults);

  const handleRerunSearch = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      setIsSearching(true);
      const res = await runSearchApiWithStatus(null, row.id);
      setRowResults(row.id, res.results, res.providerStatuses);
    } catch (err) {
      console.error('Failed to rerun search', err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    requestDeleteRow(row.id);
  };

  return (
    <div
      className={`bg-white rounded-xl shadow-sm border transition-all ${
        isActive ? 'border-blue-400 ring-1 ring-blue-200' : 'border-gray-200'
      }`}
    >
      {/* Row Header */}
      <button
        className="w-full text-left px-4 py-3 flex items-center gap-3 group"
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
        
        {/* Quick Actions (visible on hover) */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity pr-2">
          <div 
            onClick={handleRerunSearch}
            className="p-1.5 text-gray-400 hover:text-blue-600 rounded-md hover:bg-blue-50 transition-colors"
            title="Rerun Search"
          >
            <RotateCw size={14} />
          </div>
          <div 
            onClick={handleDelete}
            className="p-1.5 text-gray-400 hover:text-red-600 rounded-md hover:bg-red-50 transition-colors"
            title="Delete Request"
          >
            <Trash2 size={14} />
          </div>
        </div>

        <svg className={`w-4 h-4 text-gray-400 transition-transform flex-shrink-0 ${isExpanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
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
              <BidCard key={offer.bid_id ?? i} offer={offer} row={row} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const SOURCE_DISPLAY_NAMES: Record<string, string> = {
  rainforest_amazon: 'Amazon',
  amazon: 'Amazon',
  ebay_browse: 'eBay',
  ebay: 'eBay',
  serpapi: 'Google',
  google_cse: 'Google',
  kroger: 'Kroger',
  vendor_directory: 'Vendor',
  seller_quote: 'Quote',
  registered_merchant: 'Merchant',
};

function friendlySource(source: string): string {
  return SOURCE_DISPLAY_NAMES[source] || source.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function BidCard({ offer, row }: { offer: Offer; row: Row }) {
  const [showContactModal, setShowContactModal] = useState(false);
  const priceStr = offer.price !== null && offer.price !== undefined
    ? `$${offer.price.toFixed(2)}`
    : 'Request Quote';

  const isVendor = offer.source === 'vendor_directory' || offer.is_service_provider;

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
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-500">{friendlySource(offer.source)}</span>
          {offer.merchant && offer.merchant !== 'Unknown' && (
            <span className="text-[10px] text-gray-400">{offer.merchant}</span>
          )}
        </div>
      </div>
      {isVendor ? (
        <button
          onClick={() => setShowContactModal(true)}
          className="px-3 py-1.5 text-xs font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex-shrink-0"
        >
          Request Quote
        </button>
      ) : offer.url && offer.url !== '#' ? (
        <a
          href={offer.click_url || `/api/out?url=${encodeURIComponent(offer.url)}${offer.bid_id ? `&bid_id=${offer.bid_id}` : ''}&row_id=${row.id}&source=${offer.source}`}
          target="_blank"
          rel="noopener noreferrer"
          className="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex-shrink-0"
        >
          View Deal
        </a>
      ) : null}
      {showContactModal && (
        <VendorContactModal
          isOpen={showContactModal}
          onClose={() => setShowContactModal(false)}
          rowId={row.id}
          rowTitle={row.title}
          vendorName={offer.vendor_name || offer.merchant || ''}
          vendorCompany={offer.vendor_company || offer.title}
          vendorEmail={offer.vendor_email || ''}
          onSent={() => setShowContactModal(false)}
        />
      )}
    </div>
  );
}
