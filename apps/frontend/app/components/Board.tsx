'use client';

import { useEffect, useRef, useState } from 'react';
import { Plus, FolderPlus, Trash2, Share2, Store, ArrowLeft, User, LogOut } from 'lucide-react';
import { useShoppingStore, Row } from '../store';
import { createProjectInDb, deleteProjectFromDb } from '../utils/api';
import RowStrip from './RowStrip';
import { Button } from '../../components/ui/Button';
import { cn } from '../../utils/cn';
import { TileDetailPanel } from './TileDetailPanel';
import Link from 'next/link';
import { getMe, logout } from '../utils/auth';

const ACCOUNT_DETAILS_KEY = 'sa_account_details';

type AccountDetails = {
  name: string;
  email: string;
  phone: string;
};

export default function ProcurementBoard() {
  const rows = useShoppingStore(state => state.rows);
  const projects = useShoppingStore(state => state.projects);
  const activeRowId = useShoppingStore(state => state.activeRowId);
  const rowResults = useShoppingStore(state => state.rowResults);
  const targetProjectId = useShoppingStore(state => state.targetProjectId);
  const setTargetProjectId = useShoppingStore(state => state.setTargetProjectId);
  const setActiveRowId = useShoppingStore(state => state.setActiveRowId);
  const addProject = useShoppingStore(state => state.addProject);
  const removeProject = useShoppingStore(state => state.removeProject);
  const pendingRowDelete = useShoppingStore(state => state.pendingRowDelete);
  const undoDeleteRow = useShoppingStore(state => state.undoDeleteRow);
  const [dismissing, setDismissing] = useState(false);
  const [toast, setToast] = useState<{ message: string; tone?: 'success' | 'error' } | null>(null);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [accountDetails, setAccountDetails] = useState<AccountDetails>({
    name: '',
    email: '',
    phone: '',
  });
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const accountMenuRef = useRef<HTMLDivElement | null>(null);

  const handlePillClick = (query: string) => {
    setDismissing(true);
    setTimeout(() => {
      useShoppingStore.getState().setCardClickQuery(query);
    }, 800);
  };

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

  useEffect(() => {
    try {
      if (typeof window !== 'undefined' && typeof window.localStorage?.getItem === 'function') {
        const savedRaw = window.localStorage.getItem(ACCOUNT_DETAILS_KEY);
        if (savedRaw) {
          const saved = JSON.parse(savedRaw);
          setAccountDetails(prev => ({
            ...prev,
            name: typeof saved?.name === 'string' ? saved.name : prev.name,
            email: typeof saved?.email === 'string' ? saved.email : prev.email,
            phone: typeof saved?.phone === 'string' ? saved.phone : prev.phone,
          }));
        }
      }
    } catch (err) {
      console.error('Failed to load account details', err);
    }

    let cancelled = false;
    const canCallAuthApi =
      typeof window !== 'undefined' &&
      /^https?:/i.test(window.location?.origin || '') &&
      process.env.NODE_ENV !== 'test';

    if (canCallAuthApi) {
      getMe().then(user => {
        if (cancelled) return;
        if (!user?.authenticated) {
          setIsAuthenticated(false);
          return;
        }
        setIsAuthenticated(true);
        setAccountDetails(prev => ({
          ...prev,
          email: user.email || prev.email,
          phone: user.phone_number || prev.phone,
        }));
      });
    }

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!accountMenuOpen) return;
    const onMouseDown = (event: MouseEvent) => {
      if (!accountMenuRef.current) return;
      if (!accountMenuRef.current.contains(event.target as Node)) {
        setAccountMenuOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setAccountMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', onMouseDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onMouseDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [accountMenuOpen]);

  // Auto-scroll to center the selected row when activeRowId changes
  useEffect(() => {
    if (activeRowId && scrollContainerRef.current) {
      // Find the row element by its data attribute
      const rowElement = scrollContainerRef.current.querySelector(`[data-row-id="${activeRowId}"]`);
      if (rowElement) {
        // Scroll the row into view, centering it in the viewport
        rowElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [activeRowId]);

  const handleCreateProject = async () => {
    const title = window.prompt('Enter project name:');
    if (!title || !title.trim()) return;

    const newProject = await createProjectInDb(title.trim());
    if (newProject) {
      addProject(newProject);
      setTargetProjectId(newProject.id);
      showToast(`Project "${newProject.title}" created`);
    } else {
      showToast('Failed to create project', 'error');
    }
  };

  const handleDeleteProject = async (id: number, title: string) => {
    if (!window.confirm(`Delete project "${title}"? Associated requests will be ungrouped.`)) return;
    
    const success = await deleteProjectFromDb(id);
    if (success) {
      removeProject(id);
      showToast(`Project "${title}" deleted`);
      // Optionally refresh rows to reflect ungrouping? The store might need a refresh or we optimistically update rows?
      // For now, let's rely on eventual consistency or manual refresh, or we could update local rows.
      // Ideally we should refetch rows or update store.
      // Let's implement optimistic update for rows:
      // const updatedRows = rows.map(r => r.project_id === id ? { ...r, project_id: null } : r);
      // setRows(updatedRows); 
      // But we don't have setRows exposed conveniently here without prop drilling or re-fetching.
      // Re-fetching is safer.
      // We can rely on the user refreshing or the next poll.
    } else {
      showToast('Failed to delete project', 'error');
    }
  };

  const handleSelectProject = (projectId: number) => {
    setTargetProjectId(projectId);

    const project = projects.find(p => p.id === projectId);
    showToast(`Selected "${project?.title || 'project'}"`);
  };

  const handleAddRequestToProject = (projectId: number) => {
    // Set the target project for new rows.
    setTargetProjectId(projectId);

    // Clear the active row so chat creates a new request rather than refining the current row.
    setActiveRowId(null);

    // Just focus the chat input - the chat will create the row when user types
    const chatInput = document.querySelector('input[placeholder*="looking for"], input[placeholder*="Refine"]') as HTMLInputElement | null;
    chatInput?.focus();

    const project = projects.find(p => p.id === projectId);
    showToast(`Adding to "${project?.title || 'project'}"...`);
  };

  const handleShareBoard = async () => {
    if (rows.length === 0) {
      showToast('No requests to share', 'error');
      return;
    }

    try {
      // Create a URL with all search queries as parameters
      const url = new URL(window.location.origin);

      // Add all row titles as 'q' parameters (supporting multiple values)
      rows.forEach(row => {
        url.searchParams.append('q', row.title);
      });

      await navigator.clipboard.writeText(url.toString());
      showToast(`Board link copied! (${rows.length} request${rows.length !== 1 ? 's' : ''})`);
    } catch (err) {
      console.error('Failed to copy board link:', err);
      showToast('Failed to copy link', 'error');
    }
  };

  const handleAccountFieldChange = (field: keyof AccountDetails, value: string) => {
    setAccountDetails(prev => ({ ...prev, [field]: value }));
  };

  const handleSaveAccount = () => {
    try {
      if (typeof window !== 'undefined' && typeof window.localStorage?.setItem === 'function') {
        window.localStorage.setItem(ACCOUNT_DETAILS_KEY, JSON.stringify(accountDetails));
      }
      showToast('Account details saved');
      setAccountMenuOpen(false);
    } catch (err) {
      console.error('Failed to save account details', err);
      showToast('Failed to save account details', 'error');
    }
  };

  const handleAccountLogout = async () => {
    try {
      await logout();
    } catch (err) {
      console.error('Logout failed', err);
    }
    window.location.href = '/login';
  };

  // Grouping logic with sorting by last_engaged_at (most recent first)
  const groupedRows: Record<number, Row[]> = {};
  const ungroupedRows: Row[] = [];

  rows.forEach(row => {
    if (row.project_id) {
      if (!groupedRows[row.project_id]) {
        groupedRows[row.project_id] = [];
      }
      groupedRows[row.project_id].push(row);
    } else {
      ungroupedRows.push(row);
    }
  });

  // Sort each group by last_engaged_at (most recent first)
  Object.keys(groupedRows).forEach(projectId => {
    groupedRows[Number(projectId)].sort((a, b) => {
      const aTime = a.last_engaged_at || 0;
      const bTime = b.last_engaged_at || 0;
      return bTime - aTime;
    });
  });

  // Sort ungrouped rows by last_engaged_at (most recent first)
  ungroupedRows.sort((a, b) => {
    const aTime = a.last_engaged_at || 0;
    const bTime = b.last_engaged_at || 0;
    return bTime - aTime;
  });

  return (
    <div className="flex-1 bg-transparent h-full flex flex-col overflow-hidden relative">
      {/* Header / Disclosure */}
      <div className="h-20 px-8 bg-warm-light border-b border-warm-grey/70 flex justify-between items-center z-10 shrink-0">
        <div className="flex items-center gap-6">
          <div>
            <div className="text-[10px] font-medium uppercase tracking-[0.16em] text-onyx-muted/80">
              Board
            </div>
            <div className="text-xl font-medium text-onyx">Requests</div>
          </div>
          <div className="text-xs text-onyx-muted max-w-[220px]">
            The agent may earn a commission from purchases.
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-[10px] font-medium text-onyx uppercase tracking-[0.16em]">
            {projects.length} project{projects.length !== 1 ? 's' : ''}, {rows.length} active request{rows.length !== 1 ? 's' : ''}
          </div>
          <a href="/merchants/register">
            <Button
              variant="secondary"
              size="sm"
              className="flex items-center gap-2"
            >
              <Store size={16} />
              Become a Seller
            </Button>
          </a>
          {/* <Button
            variant="secondary"
            size="sm"
            onClick={() => setReportBugModalOpen(true)}
            className="flex items-center gap-2"
          >
            <Bug size={16} />
            Report Bug
          </Button> */}
          <Button
            variant="secondary"
            size="sm"
            onClick={handleShareBoard}
            className="flex items-center gap-2"
          >
            <Share2 size={16} />
            Share Board
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleCreateProject}
            className="flex items-center gap-2"
          >
            <FolderPlus size={16} />
            New Project
          </Button>
          <div ref={accountMenuRef} className="relative">
            <Button
              size="sm"
              onClick={() => setAccountMenuOpen(open => !open)}
              className="flex items-center gap-2"
            >
              <User size={16} />
              Account
            </Button>
            {accountMenuOpen && (
              <div className="absolute right-0 top-12 w-[320px] rounded-2xl border border-warm-grey/70 bg-white shadow-[0_18px_40px_rgba(0,0,0,0.16)] p-4 space-y-3">
                <div>
                  <div className="text-xs uppercase tracking-[0.14em] text-onyx-muted/80">Account</div>
                  <div className="text-sm text-onyx-muted mt-0.5">
                    Update your contact details for quotes and follow-ups.
                  </div>
                </div>

                <label className="block space-y-1">
                  <span className="text-xs font-medium uppercase tracking-wider text-onyx-muted">Name</span>
                  <input
                    type="text"
                    value={accountDetails.name}
                    onChange={(e) => handleAccountFieldChange('name', e.target.value)}
                    placeholder="Your full name"
                    className="w-full h-10 px-3 rounded-xl border border-warm-grey/70 text-sm text-onyx bg-warm-light focus:outline-none focus:ring-2 focus:ring-agent-blurple/35 focus:border-agent-blurple/40"
                  />
                </label>

                <label className="block space-y-1">
                  <span className="text-xs font-medium uppercase tracking-wider text-onyx-muted">Email</span>
                  <input
                    type="email"
                    value={accountDetails.email}
                    onChange={(e) => handleAccountFieldChange('email', e.target.value)}
                    placeholder="you@example.com"
                    className="w-full h-10 px-3 rounded-xl border border-warm-grey/70 text-sm text-onyx bg-warm-light focus:outline-none focus:ring-2 focus:ring-agent-blurple/35 focus:border-agent-blurple/40"
                  />
                </label>

                <label className="block space-y-1">
                  <span className="text-xs font-medium uppercase tracking-wider text-onyx-muted">Phone</span>
                  <input
                    type="tel"
                    value={accountDetails.phone}
                    onChange={(e) => handleAccountFieldChange('phone', e.target.value)}
                    placeholder="+1 (555) 555-5555"
                    className="w-full h-10 px-3 rounded-xl border border-warm-grey/70 text-sm text-onyx bg-warm-light focus:outline-none focus:ring-2 focus:ring-agent-blurple/35 focus:border-agent-blurple/40"
                  />
                </label>

                <div className="flex items-center gap-2 pt-1">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setAccountMenuOpen(false)}
                    className="flex-1"
                  >
                    Close
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleSaveAccount}
                    className="flex-1"
                  >
                    Save
                  </Button>
                </div>

                {isAuthenticated ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleAccountLogout}
                    className="w-full justify-center gap-2 text-onyx-muted hover:text-agent-blurple"
                  >
                    <LogOut size={16} />
                    Sign Out
                  </Button>
                ) : (
                  <a
                    href="/login"
                    className="block text-center text-sm font-medium text-agent-blurple hover:text-agent-blurple/80 transition-colors"
                  >
                    Sign In
                  </a>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* Scrollable Content */}
      <div ref={scrollContainerRef} className="flex-1 overflow-y-auto p-8 space-y-8">
        {rows.length === 0 && projects.length === 0 ? (
          <div className={cn(
            "space-y-8 max-w-3xl mx-auto pb-12 transition-all duration-[800ms] ease-out",
            dismissing && "opacity-0 translate-y-8 scale-95 pointer-events-none"
          )}>
            {/* Chat instruction */}
            <div className={cn(
              "flex items-center gap-3 bg-agent-blurple/10 border border-agent-blurple/20 rounded-xl p-4 transition-all duration-[600ms] ease-out",
              dismissing && "opacity-0 -translate-x-12"
            )}>
              <ArrowLeft className="w-5 h-5 text-agent-blurple shrink-0" />
              <div>
                <p className="text-sm font-medium text-onyx">Type in the chat to search for anything</p>
                <p className="text-xs text-onyx-muted mt-0.5">
                  Ask our AI agent to find products, compare prices, or connect you with vendors.
                </p>
              </div>
            </div>

            {/* Account CTA */}
            <div className={cn(
              "flex items-center justify-between bg-warm-light border border-warm-grey/50 rounded-xl p-4 transition-all duration-[600ms] ease-out delay-150",
              dismissing && "opacity-0 translate-x-12"
            )}>
              <div>
                <p className="text-sm font-medium text-onyx">Save your searches &amp; track prices</p>
                <p className="text-xs text-onyx-muted mt-0.5">Create a free account to organize requests, get price alerts, and request vendor quotes.</p>
              </div>
              <a
                href="/login"
                className="shrink-0 ml-4 px-4 py-2 text-xs font-semibold rounded-lg bg-agent-blurple text-white hover:bg-agent-blurple/90 transition-colors"
              >
                Sign Up Free
              </a>
            </div>

            {/* Trending Searches — buyable content for affiliate reviewers */}
            <div>
              <h3 className="text-sm font-semibold text-onyx mb-3 uppercase tracking-wider">Trending Searches</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {[
                  { q: 'Roblox gift cards', emoji: '🎮', desc: 'Digital codes from $10–$200' },
                  { q: 'running shoes', emoji: '👟', desc: 'Nike, Asics, Brooks & more' },
                  { q: 'wireless earbuds', emoji: '🎧', desc: 'AirPods, Sony, Samsung' },
                  { q: 'standing desk', emoji: '🖥️', desc: 'Electric sit-stand desks' },
                  { q: 'coffee maker', emoji: '☕', desc: 'Drip, espresso, pour-over' },
                  { q: 'luggage set', emoji: '🧳', desc: 'Carry-on & checked bags' },
                ].map((item) => (
                  <button
                    key={item.q}
                    onClick={() => handlePillClick(item.q)}
                    className="group bg-warm-light border border-warm-grey/50 rounded-lg p-3 hover:border-agent-blurple/40 transition-colors text-left"
                  >
                    <div className="text-2xl mb-1">{item.emoji}</div>
                    <div className="text-sm font-medium text-onyx group-hover:text-agent-blurple transition-colors">{item.q}</div>
                    <div className="text-[11px] text-onyx-muted mt-0.5">{item.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Vendor categories */}
            <div>
              <h3 className="text-sm font-semibold text-onyx mb-3 uppercase tracking-wider">Find Local Vendors</h3>
              <div className="flex flex-wrap gap-2">
                {['caterers', 'photographers', 'florists', 'DJs & entertainment', 'custom jewelry', 'private chefs'].map((v) => (
                  <button
                    key={v}
                    onClick={() => handlePillClick(v)}
                    className="text-xs px-3 py-1.5 rounded-full border border-warm-grey/60 text-onyx-muted hover:text-onyx hover:border-agent-blurple/40 transition-colors"
                  >
                    {v}
                  </button>
                ))}
                <Link href="/vendors" className="text-xs px-3 py-1.5 rounded-full bg-agent-blurple/10 text-agent-blurple hover:bg-agent-blurple/20 transition-colors">
                  Browse all vendors →
                </Link>
              </div>
            </div>

            {/* Guide previews — editorial content for affiliate approval */}
            <div>
              <h3 className="text-sm font-semibold text-onyx mb-3 uppercase tracking-wider">Buying Guides</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {[
                  { title: 'How BuyAnything Works', slug: 'how-buyanything-works', desc: 'Your complete guide to finding anything — from gift cards to private jets.' },
                  { title: 'Gift Vault: Tech Lovers', slug: 'gift-vault-tech-lovers', desc: 'Curated tech gifts for every budget, from $25 stocking stuffers to premium gear.' },
                  { title: 'Best Luggage for Travel', slug: 'best-luggage-for-travel', desc: 'Top-rated luggage reviewed and compared — carry-ons, checked bags, and sets.' },
                  { title: 'Home Office Setup Guide', slug: 'home-office-setup-guide', desc: 'Everything you need for a productive workspace, from desks to monitors.' },
                ].map((guide) => (
                  <a
                    key={guide.slug}
                    href={`/guides/${guide.slug}`}
                    className="group bg-warm-light border border-warm-grey/50 rounded-lg p-4 hover:border-agent-blurple/40 transition-colors"
                  >
                    <h4 className="text-sm font-medium text-onyx group-hover:text-agent-blurple transition-colors">{guide.title}</h4>
                    <p className="text-[11px] text-onyx-muted mt-1 line-clamp-2">{guide.desc}</p>
                  </a>
                ))}
              </div>
            </div>

            {/* Legal footer */}
            <div className="pt-4 border-t border-warm-grey/30 text-center space-y-2">
              <p className="text-[11px] text-onyx-muted/70">
                As an Amazon Associate, BuyAnything earns from qualifying purchases. We may earn commissions from other affiliate partners.
              </p>
              <div className="text-[10px] text-onyx-muted/50">
                <a href="/disclosure" className="hover:underline">Affiliate Disclosure</a> · <a href="/privacy" className="hover:underline">Privacy Policy</a> · <a href="/terms" className="hover:underline">Terms of Service</a> · <a href="/about" className="hover:underline">About</a> · <a href="/contact" className="hover:underline">Contact</a>
              </div>
            </div>
          </div>
        ) : (
          <>
            {/* Projects */}
            {projects.map(project => (
              <div key={project.id} className="space-y-4">
                <div className="flex items-center gap-3 pb-2 border-b border-warm-grey/50">
                  <button
                    type="button"
                    onClick={() => handleSelectProject(project.id)}
                    className={cn(
                      "flex items-center gap-2 text-onyx font-medium hover:text-agent-blurple",
                      targetProjectId === project.id ? "text-agent-blurple" : ""
                    )}
                  >
                    <FolderPlus size={18} className="text-agent-blurple" />
                    {project.title}
                  </button>
                  <div className="flex-1" />
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleAddRequestToProject(project.id)}
                    className="h-7 text-xs text-onyx-muted hover:text-agent-blurple"
                  >
                    <Plus size={14} className="mr-1" />
                    Add Request
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDeleteProject(project.id, project.title)}
                    className="h-7 w-7 p-0 text-onyx-muted hover:text-status-error"
                  >
                    <Trash2 size={14} />
                  </Button>
                </div>
                
                <div className="pl-6 border-l-2 border-warm-grey/30 space-y-6">
                  {(groupedRows[project.id] || []).length > 0 ? (
                    groupedRows[project.id].map(row => (
                      <RowStrip
                        key={row.id}
                        row={row}
                        offers={rowResults[row.id] || []}
                        isActive={row.id === activeRowId}
                        onSelect={() => setActiveRowId(row.id)}
                        onToast={showToast}
                      />
                    ))
                  ) : (
                    <div className="text-sm text-onyx-muted italic py-2">
                      No requests in this project yet.
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Ungrouped Rows */}
            {ungroupedRows.length > 0 && (
              <div className="space-y-6">
                {projects.length > 0 && (
                  <div className="text-xs font-medium text-onyx-muted uppercase tracking-wider pb-2 border-b border-warm-grey/50">
                    Other Requests
                  </div>
                )}
                {ungroupedRows.map(row => (
                  <RowStrip
                    key={row.id}
                    row={row}
                    offers={rowResults[row.id] || []}
                    isActive={row.id === activeRowId}
                    onSelect={() => setActiveRowId(row.id)}
                    onToast={showToast}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {toast && (
        toast.tone === 'error' ? (
          <div className="fixed inset-0 z-50 flex items-start justify-center pointer-events-none" style={{ paddingTop: '120px' }}>
            <div className="pointer-events-auto px-6 py-4 rounded-2xl border-2 border-status-error/50 bg-white text-status-error shadow-[0_16px_48px_rgba(0,0,0,0.15)] text-base font-semibold flex items-center gap-3 animate-in fade-in slide-in-from-top-2 duration-300 max-w-md">
              <span>{toast.message}</span>
              <button
                onClick={() => setToast(null)}
                className="ml-2 text-status-error/60 hover:text-status-error transition-colors text-lg font-bold leading-none"
              >
                ✕
              </button>
            </div>
          </div>
        ) : (
          <div className="absolute top-20 right-6 z-50">
            <div className="px-4 py-3 rounded-xl border text-sm font-medium flex items-center gap-2 bg-white shadow-[0_12px_24px_rgba(0,0,0,0.08)] border-status-success/40 text-status-success">
              <span>{toast.message}</span>
            </div>
          </div>
        )
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

      {/* Tile Detail Panel Overlay */}
      <TileDetailPanel />
    </div>
  );
}
