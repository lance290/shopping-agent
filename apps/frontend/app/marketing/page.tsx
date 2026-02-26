'use client';

import Link from 'next/link';

const TRENDING = [
  { label: 'Robot lawn mowers', tag: 'Trending' },
  { label: 'Standing desks under $600', tag: 'Popular' },
  { label: 'Pellet grills', tag: 'Seasonal' },
  { label: 'Air purifiers for wildfire smoke', tag: 'Trending' },
  { label: 'Espresso machines under $500', tag: 'Popular' },
  { label: 'NAS storage for home office', tag: 'Rising' },
  { label: 'Portable power stations', tag: 'Trending' },
  { label: 'Ergonomic office chairs', tag: 'Popular' },
];

const EA_GUIDES = [
  {
    title: 'Private aviation: charter vs. fractional vs. jet card',
    desc: 'A practical breakdown of cost structures, availability trade-offs, and when each model makes sense for high-frequency travelers.',
    tag: 'Service',
  },
  {
    title: 'Sourcing bespoke menswear in 2025',
    desc: 'From Savile Row to Neapolitan houses — lead times, fitting travel requirements, and how to manage the process remotely.',
    tag: 'Luxury',
  },
  {
    title: 'Art acquisition for new collectors',
    desc: 'Primary vs. secondary market, gallery relationships, authentication basics, and what to ask before committing to a six-figure piece.',
    tag: 'Luxury',
  },
  {
    title: 'Home automation for estate properties',
    desc: 'Evaluating Crestron, Control4, and Savant across multi-structure properties — integrators, ongoing support costs, and resale impact.',
    tag: 'Service',
  },
  {
    title: 'Executive relocation: vendor vetting checklist',
    desc: 'How to evaluate moving firms, secure storage, and manage white-glove household goods transport across international moves.',
    tag: 'EA Guide',
  },
  {
    title: 'Luxury vehicle acquisition: new vs. pre-owned exotics',
    desc: 'Dealer relationships, CPO programs, independent inspection protocols, and where auctions fit into a serious buying strategy.',
    tag: 'Luxury',
  },
];

const TAG_STYLES: Record<string, string> = {
  'Trending': 'bg-red-500/15 text-red-400',
  'Popular': 'bg-agent-blurple/15 text-agent-camel',
  'Seasonal': 'bg-amber-500/15 text-amber-400',
  'Rising': 'bg-emerald-500/15 text-emerald-400',
  'Luxury': 'bg-purple-500/15 text-purple-300',
  'Service': 'bg-sky-500/15 text-sky-300',
  'EA Guide': 'bg-amber-500/15 text-amber-300',
};

export default function MarketingPage() {
  return (
    <main className="min-h-screen bg-[#151617] text-onyx">
      <section className="mx-auto flex w-full max-w-5xl flex-col gap-14 px-6 py-16">

        {/* Hero */}
        <header className="space-y-6">
          <p className="text-xs uppercase tracking-[0.4em] text-onyx/60">
            BuyAnything
          </p>
          <h1 className="text-4xl font-semibold leading-tight text-onyx md:text-5xl">
            Every purchase decision,<br className="hidden md:block" /> handled.
          </h1>
          <p className="max-w-2xl text-lg text-onyx/75">
            From everyday comparison shopping to sourcing private jets and bespoke services —
            describe what you need and the agent does the legwork across retailers, vendors,
            and specialists.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link className="btn-primary" href="/login">
              Start a request
            </Link>
            <Link className="btn-secondary" href="/sign-up">
              Create an account
            </Link>
          </div>
        </header>

        {/* Trending searches */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">What people are searching</h2>
            <span className="text-xs text-onyx/40 uppercase tracking-widest">Updated weekly</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {TRENDING.map((item) => (
              <Link
                key={item.label}
                href={`/login?q=${encodeURIComponent(item.label)}`}
                className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-onyx/80 transition hover:border-white/20 hover:bg-white/10 hover:text-onyx"
              >
                <span
                  className={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${TAG_STYLES[item.tag]}`}
                >
                  {item.tag}
                </span>
                {item.label}
              </Link>
            ))}
          </div>
        </section>

        {/* Feature cards */}
        <div className="grid gap-6 md:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
            <h3 className="text-lg font-semibold">Live offer comparison</h3>
            <p className="mt-3 text-sm text-onyx/70">
              The agent pulls real listings from Amazon, eBay, Google Shopping,
              and specialist vendors simultaneously — not cached results.
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
            <h3 className="text-lg font-semibold">Constraints that stick</h3>
            <p className="mt-3 text-sm text-onyx/70">
              Budget, brand preferences, deadlines, and deal-breakers are captured
              once and applied to every search in that row.
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
            <h3 className="text-lg font-semibold">Shareable decisions</h3>
            <p className="mt-3 text-sm text-onyx/70">
              Send a clean read-only link with the full shortlist, scoring,
              and your reasoning — no account required to view.
            </p>
          </div>
        </div>

        {/* Luxury & EA guides */}
        <section>
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-2xl font-semibold">For the discerning buyer</h2>
              <p className="mt-1 text-sm text-onyx/50">
                Sourcing guides for complex, high-consideration purchases — built for executives and the assistants who support them.
              </p>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {EA_GUIDES.map((guide) => (
              <div
                key={guide.title}
                className="group flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 p-6 transition hover:border-white/20 hover:bg-white/[0.07]"
              >
                <span
                  className={`w-fit rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${TAG_STYLES[guide.tag]}`}
                >
                  {guide.tag}
                </span>
                <h3 className="text-sm font-semibold leading-snug text-onyx group-hover:text-white transition">
                  {guide.title}
                </h3>
                <p className="text-xs text-onyx/55 leading-relaxed">{guide.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* EA tools callout */}
        <section className="rounded-3xl border border-white/10 bg-gradient-to-br from-white/5 via-white/0 to-white/5 p-10">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-onyx/40 mb-2">Coming soon</p>
              <h2 className="text-2xl font-semibold">Tools built for executive assistants</h2>
              <p className="mt-3 max-w-xl text-sm text-onyx/60 leading-relaxed">
                Multi-principal boards, delegation workflows, vendor relationship tracking, and
                approval chains — purpose-built for EAs who manage procurement across complex
                households and organizations.
              </p>
            </div>
            <Link
              href="/sign-up"
              className="btn-secondary shrink-0 self-start md:self-center"
            >
              Get early access
            </Link>
          </div>
        </section>

      </section>
    </main>
  );
}
