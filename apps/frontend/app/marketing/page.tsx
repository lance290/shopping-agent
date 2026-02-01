'use client';

import Link from 'next/link';

export default function MarketingPage() {
  return (
    <main className="min-h-screen bg-[#151617] text-onyx">
      <section className="mx-auto flex w-full max-w-5xl flex-col gap-12 px-6 py-16">
        <header className="space-y-6">
          <p className="text-xs uppercase tracking-[0.4em] text-onyx/60">
            Shopping Agent
          </p>
          <h1 className="text-4xl font-semibold leading-tight text-onyx md:text-5xl">
            A single place to turn messy buying requests into real options.
          </h1>
          <p className="max-w-2xl text-lg text-onyx/75">
            Describe what you need, capture constraints, and let the agent collect offers
            across stores. Keep every request organized so you can decide faster.
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

        <div className="grid gap-6 md:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
            <h3 className="text-lg font-semibold">Turn intent into rows</h3>
            <p className="mt-3 text-sm text-onyx/70">
              Each request becomes a live workspace with queries, notes, and decisions
              captured in one place.
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
            <h3 className="text-lg font-semibold">Compare real offers</h3>
            <p className="mt-3 text-sm text-onyx/70">
              The agent pulls options from multiple retailers and keeps the best choices
              visible as you refine criteria.
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
            <h3 className="text-lg font-semibold">Share decisions easily</h3>
            <p className="mt-3 text-sm text-onyx/70">
              Send a clean link to teammates or clients with a full trail of options and
              reasoning.
            </p>
          </div>
        </div>

        <section className="rounded-3xl border border-white/10 bg-gradient-to-br from-white/5 via-white/0 to-white/5 p-10">
          <h2 className="text-2xl font-semibold">What makes it different</h2>
          <ul className="mt-6 grid gap-4 text-sm text-onyx/70 md:grid-cols-2">
            <li>• AI-guided questions that capture the right constraints up front.</li>
            <li>• A single board for multi-category procurement instead of scattered tabs.</li>
            <li>• Real-time offer refresh when requirements shift.</li>
            <li>• Lightweight reporting for approvals and documentation.</li>
          </ul>
        </section>
      </section>
    </main>
  );
}
