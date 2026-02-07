'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  BarChart3,
  TrendingUp,
  MousePointerClick,
  DollarSign,
  Users,
  ArrowLeft,
  RefreshCw,
  AlertTriangle,
  Share2,
} from 'lucide-react';

interface MetricsData {
  period: { days: number; from: string; to: string };
  m1_avg_time_to_first_result_seconds: number;
  m2_offer_ctr: number;
  m3_clickout_success_rate: number;
  m4_affiliate_coverage: number;
  m4_handler_breakdown: Record<string, number>;
  m5_revenue_per_active_user: number;
  m8_referral_signups: number;
  m8_total_shares: number;
  m9_gmv_current_period: number;
  m9_gmv_previous_period: number;
  m9_gmv_growth_rate: number;
  funnel: {
    active_users: number;
    rows_created: number;
    bids_shown: number;
    clickouts: number;
    purchases: number;
    suspicious_clickouts: number;
  };
  revenue: {
    platform_total: number;
    active_users: number;
  };
}

function MetricCard({
  label,
  value,
  sublabel,
  icon: Icon,
  color = 'blue',
}: {
  label: string;
  value: string | number;
  sublabel?: string;
  icon: React.ElementType;
  color?: string;
}) {
  const colorClasses: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-emerald-50 text-emerald-600',
    amber: 'bg-amber-50 text-amber-600',
    purple: 'bg-purple-50 text-purple-600',
    red: 'bg-red-50 text-red-600',
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
      <div className="flex items-start justify-between mb-3">
        <div className={`p-2 rounded-lg ${colorClasses[color] || colorClasses.blue}`}>
          <Icon size={18} />
        </div>
      </div>
      <div className="text-2xl font-bold text-gray-900 mb-1">{value}</div>
      <div className="text-sm font-medium text-gray-600">{label}</div>
      {sublabel && <div className="text-xs text-gray-400 mt-1">{sublabel}</div>}
    </div>
  );
}

export default function AdminMetricsPage() {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(30);
  const [fetchCount, setFetchCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function doFetch() {
      setLoading(true);
      setError(null);
      try {
        const token = localStorage.getItem('session_token') || '';
        const res = await fetch(`/api/admin/metrics?days=${days}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(`Failed to load metrics (${res.status})`);
        const data = await res.json();
        if (!cancelled) setMetrics(data);
      } catch (err: unknown) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    doFetch();
    return () => { cancelled = true; };
  }, [days, fetchCount]);

  const fetchMetrics = () => {
    setFetchCount((c) => c + 1);
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <Link
              href="/admin"
              className="p-2 rounded-lg border border-gray-200 hover:bg-white transition-colors"
            >
              <ArrowLeft size={16} />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Platform Metrics</h1>
              <p className="text-sm text-gray-500">PRD 09 — Analytics & Success Metrics</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white"
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
            <button
              onClick={fetchMetrics}
              disabled={loading}
              className="p-2 rounded-lg border border-gray-200 hover:bg-white transition-colors disabled:opacity-50"
            >
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-red-700 text-sm">
            {error}
          </div>
        )}

        {loading && !metrics && (
          <div className="flex items-center justify-center py-20">
            <RefreshCw size={24} className="animate-spin text-gray-400" />
          </div>
        )}

        {metrics && (
          <>
            {/* Core Metrics */}
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Core Success Metrics</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <MetricCard
                label="Avg Time to First Result"
                value={`${metrics.m1_avg_time_to_first_result_seconds.toFixed(1)}s`}
                sublabel="M1 — Target: < 5s"
                icon={TrendingUp}
                color="blue"
              />
              <MetricCard
                label="Offer Click-Through Rate"
                value={`${(metrics.m2_offer_ctr * 100).toFixed(1)}%`}
                sublabel="M2 — Clickouts / Bids"
                icon={MousePointerClick}
                color="green"
              />
              <MetricCard
                label="Affiliate Coverage"
                value={`${(metrics.m4_affiliate_coverage * 100).toFixed(1)}%`}
                sublabel="M4 — Tagged / Total Clickouts"
                icon={DollarSign}
                color="amber"
              />
              <MetricCard
                label="Revenue per Active User"
                value={`$${metrics.m5_revenue_per_active_user.toFixed(2)}`}
                sublabel="M5 — Platform fees"
                icon={DollarSign}
                color="purple"
              />
            </div>

            {/* Growth & GMV */}
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Growth</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <MetricCard
                label="GMV This Period"
                value={`$${metrics.m9_gmv_current_period.toLocaleString()}`}
                sublabel={`Growth: ${(metrics.m9_gmv_growth_rate * 100).toFixed(1)}%`}
                icon={BarChart3}
                color="green"
              />
              <MetricCard
                label="GMV Previous Period"
                value={`$${metrics.m9_gmv_previous_period.toLocaleString()}`}
                icon={BarChart3}
                color="blue"
              />
              <MetricCard
                label="Referral Signups"
                value={metrics.m8_referral_signups}
                sublabel={`From ${metrics.m8_total_shares} shares`}
                icon={Share2}
                color="purple"
              />
              <MetricCard
                label="Clickout Success Rate"
                value={`${(metrics.m3_clickout_success_rate * 100).toFixed(1)}%`}
                sublabel={`${metrics.funnel.suspicious_clickouts} suspicious`}
                icon={AlertTriangle}
                color={metrics.funnel.suspicious_clickouts > 0 ? 'red' : 'green'}
              />
            </div>

            {/* Funnel */}
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Conversion Funnel</h2>
            <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm mb-8">
              <div className="flex items-end gap-4 h-40">
                {[
                  { label: 'Active Users', value: metrics.funnel.active_users },
                  { label: 'Rows Created', value: metrics.funnel.rows_created },
                  { label: 'Bids Shown', value: metrics.funnel.bids_shown },
                  { label: 'Clickouts', value: metrics.funnel.clickouts },
                  { label: 'Purchases', value: metrics.funnel.purchases },
                ].map((step, i, arr) => {
                  const maxVal = arr[0].value || 1;
                  const height = Math.max(8, (step.value / maxVal) * 100);
                  return (
                    <div key={step.label} className="flex-1 flex flex-col items-center gap-2">
                      <div className="text-sm font-bold text-gray-900">{step.value}</div>
                      <div
                        className="w-full bg-blue-500 rounded-t-lg transition-all"
                        style={{ height: `${height}%`, opacity: 1 - i * 0.15 }}
                      />
                      <div className="text-xs text-gray-500 text-center">{step.label}</div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Handler Breakdown */}
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Affiliate Handler Breakdown</h2>
            <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm mb-8">
              {Object.entries(metrics.m4_handler_breakdown).length > 0 ? (
                <div className="space-y-3">
                  {Object.entries(metrics.m4_handler_breakdown)
                    .sort(([, a], [, b]) => b - a)
                    .map(([handler, count]) => {
                      const total = Object.values(metrics.m4_handler_breakdown).reduce(
                        (s, v) => s + v,
                        0,
                      );
                      const pct = total > 0 ? (count / total) * 100 : 0;
                      return (
                        <div key={handler} className="flex items-center gap-3">
                          <div className="w-32 text-sm font-medium text-gray-700 truncate">
                            {handler}
                          </div>
                          <div className="flex-1 bg-gray-100 rounded-full h-4 overflow-hidden">
                            <div
                              className="bg-blue-500 h-full rounded-full"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                          <div className="text-sm text-gray-500 w-16 text-right">
                            {count} ({pct.toFixed(0)}%)
                          </div>
                        </div>
                      );
                    })}
                </div>
              ) : (
                <div className="text-sm text-gray-400 text-center py-4">No clickout data yet</div>
              )}
            </div>

            {/* Revenue */}
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Revenue</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <MetricCard
                label="Platform Revenue"
                value={`$${metrics.revenue.platform_total.toLocaleString()}`}
                sublabel={`${metrics.revenue.active_users} active users`}
                icon={DollarSign}
                color="green"
              />
              <MetricCard
                label="Active Users"
                value={metrics.revenue.active_users}
                sublabel={`Last ${days} days`}
                icon={Users}
                color="blue"
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
