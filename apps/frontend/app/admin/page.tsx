'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card } from '../../components/ui/Card';
import { ArrowLeft, RefreshCw, Users, ShoppingCart, MousePointerClick, DollarSign, Store, Mail, Bug } from 'lucide-react';
import { getToken } from '../utils/auth';

interface AdminStats {
  users: { total: number; last_7_days: number };
  rows: { total: number; active: number };
  bids: { total: number };
  clickouts: { total: number; last_7_days: number };
  purchases: { total: number; gmv: number };
  merchants: { total: number };
  outreach: { sent: number; quoted: number };
  bugs: { total: number; open: number };
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
  }, []);

  async function loadStats() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/admin/stats', {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.status === 403) {
        setError('Admin access required.');
        return;
      }
      if (!res.ok) throw new Error('Failed to load stats');
      setStats(await res.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  const StatCard = ({
    icon: Icon,
    label,
    value,
    sub,
  }: {
    icon: React.ElementType;
    label: string;
    value: string | number;
    sub?: string;
  }) => (
    <Card className="p-5">
      <div className="flex items-center gap-3 mb-2">
        <div className="w-9 h-9 rounded-lg bg-agent-blurple/10 flex items-center justify-center">
          <Icon size={18} className="text-agent-blurple" />
        </div>
        <span className="text-xs font-medium text-onyx-muted uppercase tracking-wide">{label}</span>
      </div>
      <div className="text-2xl font-bold text-onyx">{value}</div>
      {sub && <div className="text-xs text-onyx-muted mt-1">{sub}</div>}
    </Card>
  );

  return (
    <div className="min-h-screen bg-warm-light">
      <header className="bg-white border-b border-warm-grey/60 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="text-onyx-muted hover:text-onyx transition-colors">
              <ArrowLeft size={20} />
            </Link>
            <h1 className="text-xl font-bold text-onyx">Admin Dashboard</h1>
          </div>
          <button
            onClick={loadStats}
            className="text-onyx-muted hover:text-onyx transition-colors"
            title="Refresh"
          >
            <RefreshCw size={18} />
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {loading && (
          <div className="flex items-center justify-center py-20">
            <RefreshCw className="w-6 h-6 animate-spin text-onyx-muted" />
          </div>
        )}

        {error && (
          <Card className="p-6 text-center">
            <p className="text-onyx-muted">{error}</p>
          </Card>
        )}

        {!loading && !error && stats && (
          <div className="space-y-8">
            <section>
              <h2 className="text-sm font-semibold text-onyx-muted uppercase tracking-wide mb-4">
                Platform Overview
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard
                  icon={Users}
                  label="Users"
                  value={stats.users.total}
                  sub={`+${stats.users.last_7_days} this week`}
                />
                <StatCard
                  icon={ShoppingCart}
                  label="Rows"
                  value={stats.rows.total}
                  sub={`${stats.rows.active} active`}
                />
                <StatCard
                  icon={ShoppingCart}
                  label="Bids"
                  value={stats.bids.total}
                />
                <StatCard
                  icon={Store}
                  label="Merchants"
                  value={stats.merchants.total}
                />
              </div>
            </section>

            <section>
              <h2 className="text-sm font-semibold text-onyx-muted uppercase tracking-wide mb-4">
                Monetization
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <StatCard
                  icon={MousePointerClick}
                  label="Clickouts"
                  value={stats.clickouts.total}
                  sub={`+${stats.clickouts.last_7_days} this week`}
                />
                <StatCard
                  icon={DollarSign}
                  label="Purchases"
                  value={stats.purchases.total}
                  sub={`GMV: $${stats.purchases.gmv.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
                />
                <StatCard
                  icon={Mail}
                  label="Outreach"
                  value={stats.outreach.sent}
                  sub={`${stats.outreach.quoted} quotes received`}
                />
              </div>
            </section>

            <section>
              <h2 className="text-sm font-semibold text-onyx-muted uppercase tracking-wide mb-4">
                Health
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <StatCard
                  icon={Bug}
                  label="Bug Reports"
                  value={stats.bugs.total}
                  sub={`${stats.bugs.open} open`}
                />
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
