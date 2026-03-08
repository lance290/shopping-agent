'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useShoppingStore } from '../../store';
import type { Row } from '../../store';
import { createProjectInDb, duplicateProjectInDb, fetchSingleRowFromDb, fundDealEscrowInDb } from '../../utils/api';
import { Bug, FolderPlus, Copy, ChevronLeft, ChevronRight, ArrowRight } from 'lucide-react';
import { VerticalListRow } from './VerticalListRow';
import { getMe } from '../../utils/auth';
import MobileBottomSheet from '../MobileBottomSheet';
import type { SnapPoint } from '../MobileBottomSheet';

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
    image: 'https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=800&q=80',
  },
  {
    title: 'Executive relocation: vendor vetting checklist',
    slug: 'executive-relocation',
    image: 'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=800&q=80',
  },
];

const HERO_SLIDES = [
  {
    eyebrow: 'AI Chief of Staff',
    title: 'Delegate your hardest procurement projects.',
    description:
      'We source, negotiate, and organize high-end vendors for events, real estate, and corporate needs. Just drop in your requirements.',
    cta: 'I need to plan a corporate retreat',
    image: 'https://images.unsplash.com/photo-1497366216548-37526070297c?q=80&w=2938&auto=format&fit=crop',
  },
  {
    eyebrow: 'Apples-to-Apples Comparison',
    title: 'Compare vendors in one clean dashboard.',
    description:
      'Stop digging through your inbox. We extract the line items, specs, and safety records so you can review three perfect bids in 60 seconds.',
    cta: 'Find private jet charter quotes',
    image: 'https://images.unsplash.com/photo-1540569014015-19a7be504e3a?q=80&w=2940&auto=format&fit=crop',
  },
  {
    eyebrow: 'Zero Platform Fees',
    title: 'Pay the vendor, not the middleman.',
    description:
      'We are an introduction and sourcing layer. Review quotes with your Principal, approve the best one, and handle payment directly.',
    cta: 'Find architects for a kitchen remodel',
    image: 'https://images.unsplash.com/photo-1600607686527-6fb886090705?q=80&w=2938&auto=format&fit=crop',
  },
];

export function AppView({ children }: AppViewProps) {
  const rows = useShoppingStore((s) => s.rows);
  const projects = useShoppingStore((s) => s.projects);
  const activeRowId = useShoppingStore((s) => s.activeRowId);
  const setActiveRowId = useShoppingStore((s) => s.setActiveRowId);
  const updateRow = useShoppingStore((s) => s.updateRow);
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
  const [activeHeroIndex, setActiveHeroIndex] = useState(0);
  const [dealBanner, setDealBanner] = useState<{ tone: 'success' | 'warning' | 'error'; message: string } | null>(null);

  // Mobile bottom sheet state
  const [mobileSheetSnap, setMobileSheetSnap] = useState<SnapPoint>('peek');

  // Chat panel resize state (desktop only)
  const [chatWidth, setChatWidth] = useState(400);
  const [isDesktop, setIsDesktop] = useState(false);
  const isDragging = useRef(false);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(0);
  const handledDealLinkRef = useRef<string | null>(null);

  // Auto-expand the active row when it changes so users immediately see results
  useEffect(() => {
    if (activeRowId) {
      setExpandedRowId(activeRowId);
    }
  }, [activeRowId]);

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

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const rowParam = params.get('row');
    const dealParam = params.get('deal');
    const fundParam = params.get('fund');
    const checkoutState = params.get('deal_checkout');
    const rowId = rowParam ? Number(rowParam) : null;
    const dealId = dealParam ? Number(dealParam) : null;

    if (rowId && Number.isFinite(rowId)) {
      setActiveRowId(rowId);
      setExpandedRowId(rowId);
    }

    if (checkoutState && rowId && Number.isFinite(rowId)) {
      void fetchSingleRowFromDb(rowId).then((freshRow) => {
        if (freshRow) {
          updateRow(rowId, freshRow);
        }
      });
      if (checkoutState === 'success') {
        setDealBanner({ tone: 'success', message: 'Escrow funding completed. The row has been refreshed.' });
      } else {
        setDealBanner({ tone: 'warning', message: 'Checkout was canceled. The deal is still ready to fund.' });
      }
      window.history.replaceState({}, '', '/app');
      return;
    }

    const dealLinkKey = `${dealId ?? 'none'}:${rowId ?? 'none'}:${fundParam ?? '0'}:${isAuthenticated}`;
    if (handledDealLinkRef.current === dealLinkKey) return;
    if (fundParam !== '1') {
      handledDealLinkRef.current = dealLinkKey;
      return;
    }
    if (!dealId || !Number.isFinite(dealId)) return;
    if (isAuthenticated !== true) {
      if (isAuthenticated === false) {
        handledDealLinkRef.current = dealLinkKey;
        setDealBanner({ tone: 'error', message: 'Sign in to fund this deal.' });
      }
      return;
    }

    handledDealLinkRef.current = dealLinkKey;
    void fundDealEscrowInDb(dealId).then((result) => {
      if (result?.checkout_url) {
        window.location.assign(result.checkout_url);
        return;
      }
      setDealBanner({ tone: 'error', message: 'Unable to launch checkout for this deal.' });
      window.history.replaceState({}, '', '/app');
    });
  }, [isAuthenticated, setActiveRowId, updateRow]);

  useEffect(() => {
    if (!isDesktop || isAuthenticated === true || activeRowId) return;
    const interval = window.setInterval(() => {
      setActiveHeroIndex((current) => (current + 1) % HERO_SLIDES.length);
    }, 12000);
    return () => window.clearInterval(interval);
  }, [activeRowId, isAuthenticated, isDesktop]);

  // Detect desktop breakpoint for resize handle visibility
  useEffect(() => {
    const checkDesktop = () => setIsDesktop(window.innerWidth >= 1024);
    checkDesktop();
    window.addEventListener('resize', checkDesktop);
    return () => window.removeEventListener('resize', checkDesktop);
  }, []);

  // Global drag handlers for chat panel resize
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging.current) return;
      const delta = e.clientX - dragStartX.current;
      setChatWidth(Math.max(280, Math.min(800, dragStartWidth.current + delta)));
    };
    const handleMouseUp = () => {
      if (!isDragging.current) return;
      isDragging.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  const handleResizeStart = (e: React.MouseEvent) => {
    isDragging.current = true;
    dragStartX.current = e.clientX;
    dragStartWidth.current = chatWidth;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    e.preventDefault();
  };

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
      onSelect={() => {
        setActiveRowId(row.id);
      }}
      onToggleExpand={() => {
        const willExpand = expandedRowId !== row.id;
        setExpandedRowId(willExpand ? row.id : null);
        // On mobile, snap sheet to full when expanding so results get max space
        if (!isDesktop && willExpand) {
          setMobileSheetSnap('full');
        }
      }}
    />
  );

  const handleIntentClick = (query: string) => {
    setCardClickQuery(query);
  };

  const activeHero = HERO_SLIDES[activeHeroIndex];

  // Peek label: show active row info or generic label
  const activeRowForLabel = rows.find(r => r.id === activeRowId);
  const peekLabel = activeRowForLabel
    ? activeRowForLabel.title
    : activeRows.length > 0
      ? 'Your Lists'
      : 'No items yet';
  const peekSublabel = activeRows.length > 0
    ? `${activeRows.length} item${activeRows.length !== 1 ? 's' : ''}`
    : undefined;

  // Extracted list content — rendered in desktop pane or mobile sheet
  const listContent = (
    <>
      {dealBanner && (
        <div
          className={`mx-4 mt-4 rounded-xl border px-4 py-3 text-sm ${dealBanner.tone === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : dealBanner.tone === 'warning' ? 'border-amber-200 bg-amber-50 text-amber-800' : 'border-rose-200 bg-rose-50 text-rose-800'}`}
        >
          {dealBanner.message}
        </div>
      )}
      {isAuthenticated !== true && !activeRowId ? (
        isDesktop ? (
          <div className="p-6 space-y-6 bg-gradient-to-b from-[#0b1220] via-[#0f1a2e] to-[#162236] text-white min-h-full">
            <section className="relative overflow-hidden rounded-[28px] border border-white/10 shadow-2xl">
              <div className="absolute inset-0">
                <img src={activeHero.image} alt={activeHero.title} className="h-full w-full object-cover" />
                <div className="absolute inset-0 bg-gradient-to-r from-[#09111d] via-[#09111d]/92 to-[#09111d]/55" />
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(245,158,11,0.22),transparent_28%),radial-gradient(circle_at_bottom_left,rgba(96,165,250,0.18),transparent_28%)]" />
              </div>
              <div className="relative grid gap-6 xl:grid-cols-[1.3fr_0.7fr] p-7 xl:p-8">
                <div className="max-w-3xl">
                  <p className="text-[11px] uppercase tracking-[0.35em] text-white/55">{activeHero.eyebrow}</p>
                  <h2 className="mt-4 text-4xl font-semibold leading-tight text-white xl:text-5xl">
                    {activeHero.title}
                  </h2>
                  <p className="mt-4 max-w-2xl text-base leading-7 text-white/75">
                    {activeHero.description}
                  </p>
                  <div className="mt-6 flex flex-wrap gap-3">
                    <button
                      type="button"
                      onClick={() => handleIntentClick(activeHero.cta)}
                      className="inline-flex items-center gap-2 rounded-2xl bg-gold px-5 py-3 text-sm font-semibold text-navy transition hover:bg-gold-dark"
                    >
                      Ask chat now
                      <ArrowRight size={16} />
                    </button>
                    <Link className="inline-flex items-center rounded-2xl border border-white/15 bg-white/10 px-5 py-3 text-sm font-medium text-white transition hover:bg-white/15" href="/guides">
                      Browse guides
                    </Link>
                    <Link className="inline-flex items-center rounded-2xl border border-white/15 bg-white/10 px-5 py-3 text-sm font-medium text-white transition hover:bg-white/15" href="/vendors">
                      Explore vendors
                    </Link>
                  </div>
                  <div className="mt-6 flex flex-wrap gap-3">
                    <button
                      type="button"
                      onClick={() => handleIntentClick(activeHero.cta)}
                      className="rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm text-white transition hover:bg-white/15"
                    >
                      {activeHero.cta}
                    </button>
                  </div>
                </div>
                <div className="rounded-[24px] border border-slate-400/20 bg-[#0c1629]/80 p-5 backdrop-blur-sm">
                  <p className="text-[11px] uppercase tracking-[0.3em] text-white/55">Why people use BuyAnything</p>
                  <div className="mt-4 space-y-3">
                    <div className="rounded-2xl border border-sky-400/25 bg-sky-500/15 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wider text-sky-200">Ask once, compare everywhere</p>
                      <p className="mt-1 text-sm text-white/80">Search retail listings, specialist vendors, and guides in one workflow.</p>
                    </div>
                    <div className="rounded-2xl border border-violet-400/25 bg-violet-500/15 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wider text-violet-200">Keep everything organized</p>
                      <p className="mt-1 text-sm text-white/80">Put multiple searches inside a project like a trip, event, or shopping mission.</p>
                    </div>
                    <div className="rounded-2xl border border-emerald-400/25 bg-emerald-500/15 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wider text-emerald-200">Share before you decide</p>
                      <p className="mt-1 text-sm text-white/80">Send a project or search to a spouse, teammate, or client for review.</p>
                    </div>
                    <div className="rounded-2xl border border-amber-400/25 bg-amber-500/15 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wider text-amber-200">Save your favorites as you go</p>
                      <p className="mt-1 text-sm text-white/80">Like, comment on, and select the options worth revisiting.</p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="absolute right-4 top-4 flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setActiveHeroIndex((current) => (current - 1 + HERO_SLIDES.length) % HERO_SLIDES.length)}
                  className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/15 bg-[#09111d]/60 text-white transition hover:bg-[#09111d]/80"
                  aria-label="Previous hero"
                >
                  <ChevronLeft size={16} />
                </button>
                <button
                  type="button"
                  onClick={() => setActiveHeroIndex((current) => (current + 1) % HERO_SLIDES.length)}
                  className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/15 bg-[#09111d]/60 text-white transition hover:bg-[#09111d]/80"
                  aria-label="Next hero"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
              <div className="absolute bottom-4 left-7 flex items-center gap-2">
                {HERO_SLIDES.map((slide, index) => (
                  <button
                    key={slide.title}
                    type="button"
                    onClick={() => setActiveHeroIndex(index)}
                    className={`h-2.5 rounded-full transition-all ${index === activeHeroIndex ? 'w-8 bg-gold' : 'w-2.5 bg-white/35 hover:bg-white/55'}`}
                    aria-label={`Show hero ${index + 1}`}
                  />
                ))}
              </div>
            </section>

            <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
              <div className="rounded-3xl border border-slate-500/25 bg-[#0e1b30]/80 p-5">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-semibold uppercase tracking-wide text-white/85">Start faster</h3>
                    <p className="mt-1 text-sm text-white/60">Turn merchandising into action with one click into chat.</p>
                  </div>
                  <span className="text-[10px] uppercase tracking-[0.25em] text-white/35">Tap to ask</span>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  {TRENDING_SEARCHES.slice(0, 4).map((label) => (
                    <button
                      key={label}
                      type="button"
                      onClick={() => handleIntentClick(label)}
                      className="group rounded-2xl border border-white/10 bg-[#0d1728] px-4 py-4 text-left transition hover:border-gold/40 hover:bg-[#12203a]"
                    >
                      <div className="text-[10px] uppercase tracking-[0.22em] text-white/40">Popular prompt</div>
                      <div className="mt-2 text-sm font-medium text-white group-hover:text-gold-light">{label}</div>
                    </button>
                  ))}
                </div>
              </div>
              <div className="rounded-3xl border border-slate-400/20 bg-[#0c1629]/60 p-5">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-white/85">Start with a real project</h3>
                <p className="mt-1 text-sm text-white/55">A project groups multiple searches together — like a trip, event, or shopping mission.</p>
                <div className="mt-4 grid gap-3">
                  {[
                    { name: 'Executive Home Office', prompt: 'I need to compare high-end AV equipment, custom sit-stand desks, and ergonomic chairs', desc: 'Source premium office setups and secure IT networking.', border: 'border-amber-400/20 hover:border-amber-400/40', bg: 'bg-amber-500/10 hover:bg-amber-500/20', title: 'text-amber-200' },
                    { name: 'Corporate Retreat', prompt: 'I need to compare private aviation options and estate rentals for a 15-person corporate retreat', desc: 'Track private flights, luxury lodging, and catering bids.', border: 'border-violet-400/20 hover:border-violet-400/40', bg: 'bg-violet-500/10 hover:bg-violet-500/20', title: 'text-violet-200' },
                    { name: 'Estate Renovations', prompt: 'I need to compare contractors and architects for a luxury kitchen remodel', desc: 'Compare verified contractor bids and architectural quotes.', border: 'border-sky-400/20 hover:border-sky-400/40', bg: 'bg-sky-500/10 hover:bg-sky-500/20', title: 'text-sky-200' },
                  ].map((example) => (
                    <button
                      key={example.name}
                      type="button"
                      onClick={async () => {
                        const project = await createProjectInDb(example.name);
                        if (project) {
                          addProject(project);
                          setTargetProjectId(project.id);
                        }
                        handleIntentClick(example.prompt);
                      }}
                      className={`group rounded-2xl border ${example.border} ${example.bg} p-4 text-left transition`}
                    >
                      <p className={`text-sm font-semibold ${example.title}`}>{example.name}</p>
                      <p className="mt-1 text-sm text-white/65">{example.desc}</p>
                      <p className="mt-2 text-xs font-medium text-gold group-hover:text-gold-light">Start this project &rarr;</p>
                    </button>
                  ))}
                </div>
              </div>
            </section>

            <section>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wide">Trending intents</h3>
                <span className="text-xs text-white/40 uppercase tracking-widest">Tap to ask chat</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {TRENDING_SEARCHES.map((label) => (
                  <button
                    key={label}
                    type="button"
                    onClick={() => handleIntentClick(label)}
                    className="rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm text-white hover:bg-white/20"
                  >
                    {label}
                  </button>
                ))}
              </div>
            </section>

            <section>
              <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wide mb-3">Editorial guides</h3>
              <div className="grid gap-3 md:grid-cols-2">
                {GUIDE_LINKS.map((guide) => (
                  <div key={guide.slug} className="rounded-2xl border border-white/10 bg-white/5 overflow-hidden">
                    <div className="h-28 w-full bg-navy">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={guide.image} alt={guide.title} className="h-full w-full object-cover opacity-90" />
                    </div>
                    <div className="p-4">
                      <Link href={`/guides/${guide.slug}`} className="block text-sm font-medium text-white hover:text-sky-200">
                        {guide.title}
                      </Link>
                      <div className="mt-3 flex items-center gap-3 text-xs">
                        <Link href={`/guides/${guide.slug}`} className="text-sky-200 hover:text-sky-100">Read guide</Link>
                        <button type="button" onClick={() => handleIntentClick(guide.title)} className="text-white/70 hover:text-white">
                          Ask chat →
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>
        ) : null
      ) : (
        <div className="p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-ink-muted uppercase tracking-wide">Your List</h2>
            {isDesktop && (
              <div className="flex items-center gap-2">
                <button
                  onClick={async () => {
                    if (isTipJarLoading) return;
                    setIsTipJarLoading(true);
                    try {
                      const res = await fetch('/api/tip-jar', { method: 'POST' });
                      const data = await res.json();
                      if (!res.ok) throw new Error(data?.detail || 'Failed to create tip jar session');
                      if (data?.checkout_url) window.location.href = data.checkout_url;
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
                  className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-accent-blue bg-accent-blue/10 rounded-lg hover:bg-accent-blue/20 transition-colors"
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
            )}
          </div>

          {activeRows.length === 0 && (
            <div className="text-center py-12 text-onyx-muted">
              <p className="text-sm">No items yet. Start a conversation to add items.</p>
            </div>
          )}

          {projects.map((project) => {
            const projectRows = grouped[project.id];
            if (!projectRows || projectRows.length === 0) return null;
            const isCollapsed = collapsedProjects[project.id];
            return (
              <div key={project.id} className="mb-4">
                <div role="group" className="w-full flex items-center justify-between mb-2 pb-1 border-b border-warm-grey group hover:border-gold transition-colors">
                  <button onClick={() => setCollapsedProjects(prev => ({ ...prev, [project.id]: !isCollapsed }))} className="flex items-center gap-2 text-left">
                    <svg className="w-4 h-4 text-gold-dark" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                    </svg>
                    <span className="text-xs font-semibold text-ink uppercase tracking-wide group-hover:text-gold-dark transition-colors">{project.title}</span>
                    <span className="text-xs text-onyx-muted">{projectRows.length} item{projectRows.length !== 1 ? 's' : ''}</span>
                    {targetProjectId === project.id && (
                      <span className="ml-2 px-1.5 py-0.5 rounded bg-gold/20 text-gold-dark text-[10px] font-bold uppercase tracking-wider">Active</span>
                    )}
                    <svg className={`w-4 h-4 text-onyx-muted transition-transform ${isCollapsed ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => { if (targetProjectId === project.id) { setTargetProjectId(null); } else { setTargetProjectId(project.id); } }}
                      className="opacity-0 group-hover:opacity-100 px-2 py-1 text-xs text-accent-blue hover:bg-accent-blue/10 rounded transition-all"
                    >
                      {targetProjectId === project.id ? 'Cancel Add' : '+ Add Item'}
                    </button>
                    <button
                      onClick={(e) => handleDuplicateProject(e, project.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 text-onyx-muted hover:text-accent-blue rounded transition-colors"
                      title="Duplicate List"
                    >
                      <Copy size={14} />
                    </button>
                  </div>
                </div>
                {!isCollapsed && (
                  <div className="space-y-2 pl-2 border-l-2 border-gold/30">
                    {projectRows.map(renderRow)}
                  </div>
                )}
              </div>
            );
          })}

          {ungrouped.length > 0 && (() => {
            const isCollapsed = collapsedProjects['ungrouped'];
            return (
              <div className="mb-4">
                {projects.length > 0 && (
                  <button
                    onClick={() => setCollapsedProjects(prev => ({ ...prev, ungrouped: !isCollapsed }))}
                    className="w-full flex items-center justify-between mb-2 pb-1 border-b border-warm-grey group hover:border-gold transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-onyx-muted uppercase tracking-wide group-hover:text-gold-dark transition-colors">Other Requests</span>
                      <span className="text-xs text-onyx-muted">{ungrouped.length} item{ungrouped.length !== 1 ? 's' : ''}</span>
                    </div>
                    <svg className={`w-4 h-4 text-onyx-muted transition-transform ${isCollapsed ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
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
    </>
  );

  return (
    <div className="flex flex-col lg:flex-row h-[100dvh] w-full overflow-hidden relative" style={{ ['--sheet-peek-height' as string]: '72px' }}>
      {/* Undo Toast */}
      {pendingRowDelete && (
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-[100] bg-navy text-white px-4 py-3 rounded-xl shadow-2xl flex items-center gap-4 animate-in fade-in slide-in-from-bottom-4">
          <div className="text-sm font-medium">
            Deleted &quot;{pendingRowDelete.row.title}&quot;
          </div>
          <button
            onClick={undoDeleteRow}
            className="text-sm font-bold text-gold hover:text-gold-dark transition-colors bg-white/10 px-3 py-1.5 rounded-lg"
          >
            Undo
          </button>
        </div>
      )}

      {/* Chat Pane — full-screen on mobile, resizable on desktop */}
      <div
        className="flex-1 lg:flex-none min-h-0 flex flex-col z-10"
        style={isDesktop ? { width: chatWidth, flexBasis: chatWidth } : { paddingBottom: 72 }}
      >
        <div className={isDesktop ? 'h-full' : undefined} style={!isDesktop ? { height: 'calc(100dvh - var(--sheet-peek-height, 72px))' } : undefined}>
          {children}
        </div>
      </div>

      {/* Resize Handle - desktop only */}
      <div
        className="hidden lg:flex flex-shrink-0 w-1 cursor-col-resize z-20 group items-center justify-center bg-warm-grey hover:bg-gold active:bg-gold-dark transition-colors"
        onMouseDown={handleResizeStart}
        title="Drag to resize"
      >
        <div className="w-0.5 h-8 rounded-full bg-onyx-muted group-hover:bg-gold-dark transition-colors" />
      </div>

      {/* Desktop List Pane — hidden on mobile */}
      <div className="hidden lg:block flex-1 min-w-0 overflow-y-auto bg-canvas-dark/50">
        {listContent}
      </div>

      {/* Mobile Bottom Sheet — hidden on desktop */}
      {!isDesktop && (
        <MobileBottomSheet
          peekLabel={peekLabel}
          peekSublabel={peekSublabel}
          snapTo={mobileSheetSnap}
          onSnapChange={setMobileSheetSnap}
        >
          {listContent}
        </MobileBottomSheet>
      )}
    </div>
  );
}
