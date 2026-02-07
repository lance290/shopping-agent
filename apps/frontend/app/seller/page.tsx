'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { ArrowLeft, Inbox, FileText, User, RefreshCw } from 'lucide-react';
import { authHeaders } from '../utils/auth';

interface RFPSummary {
  row_id: number;
  title: string;
  status?: string;
  service_category?: string;
  choice_factors?: string;
  created_at?: string;
  quote_count: number;
}

interface QuoteSummary {
  id: number;
  row_id: number;
  row_title?: string;
  price?: number;
  description?: string;
  status: string;
  created_at?: string;
}

interface MerchantProfile {
  id: number;
  business_name: string;
  contact_name?: string;
  email?: string;
  phone?: string;
  categories?: string;
  service_areas?: string;
  website?: string;
}

type Tab = 'inbox' | 'quotes' | 'profile';

export default function SellerDashboard() {
  const [activeTab, setActiveTab] = useState<Tab>('inbox');
  const [inbox, setInbox] = useState<RFPSummary[]>([]);
  const [quotes, setQuotes] = useState<QuoteSummary[]>([]);
  const [profile, setProfile] = useState<MerchantProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData(activeTab);
  }, [activeTab]);

  async function loadData(tab: Tab) {
    setLoading(true);
    setError(null);
    try {
      if (tab === 'inbox') {
        const res = await fetch('/api/seller/inbox', { headers: authHeaders() });
        if (res.status === 403) {
          setError('No merchant profile found. Please register first.');
          return;
        }
        if (!res.ok) throw new Error('Failed to load inbox');
        setInbox(await res.json());
      } else if (tab === 'quotes') {
        const res = await fetch('/api/seller/quotes', { headers: authHeaders() });
        if (!res.ok) throw new Error('Failed to load quotes');
        setQuotes(await res.json());
      } else if (tab === 'profile') {
        const res = await fetch('/api/seller/profile', { headers: authHeaders() });
        if (res.status === 403) {
          setError('No merchant profile found. Please register first.');
          return;
        }
        if (!res.ok) throw new Error('Failed to load profile');
        setProfile(await res.json());
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  const statusBadge = (status: string) => {
    const colors: Record<string, string> = {
      submitted: 'bg-blue-100 text-blue-700',
      pending: 'bg-yellow-100 text-yellow-700',
      accepted: 'bg-green-100 text-green-700',
      rejected: 'bg-red-100 text-red-700',
    };
    return (
      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase ${colors[status] || 'bg-gray-100 text-gray-600'}`}>
        {status}
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-warm-light">
      <header className="bg-white border-b border-warm-grey/60 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="text-onyx-muted hover:text-onyx transition-colors">
              <ArrowLeft size={20} />
            </Link>
            <h1 className="text-xl font-bold text-onyx">Seller Dashboard</h1>
          </div>
          <div className="flex gap-2">
            {(['inbox', 'quotes', 'profile'] as Tab[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                  activeTab === tab
                    ? 'bg-agent-blurple text-white'
                    : 'text-onyx-muted hover:bg-warm-grey/30'
                }`}
              >
                {tab === 'inbox' && <Inbox size={14} className="inline mr-1.5" />}
                {tab === 'quotes' && <FileText size={14} className="inline mr-1.5" />}
                {tab === 'profile' && <User size={14} className="inline mr-1.5" />}
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {loading && (
          <div className="flex items-center justify-center py-20">
            <RefreshCw className="w-6 h-6 animate-spin text-onyx-muted" />
          </div>
        )}

        {error && (
          <Card className="p-6 text-center">
            <p className="text-onyx-muted mb-4">{error}</p>
            <a href="/merchants/register">
              <Button variant="primary">Register as Merchant</Button>
            </a>
          </Card>
        )}

        {!loading && !error && activeTab === 'inbox' && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-onyx">
              RFP Inbox ({inbox.length})
            </h2>
            {inbox.length === 0 ? (
              <Card className="p-8 text-center text-onyx-muted">
                No matching buyer requests yet. Check back soon!
              </Card>
            ) : (
              inbox.map((rfp) => (
                <Card key={rfp.row_id} className="p-4 hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="font-semibold text-onyx">{rfp.title}</h3>
                      <div className="flex items-center gap-2 mt-1">
                        {rfp.service_category && (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 uppercase">
                            {rfp.service_category}
                          </span>
                        )}
                        <span className="text-xs text-onyx-muted">
                          {rfp.quote_count} quote{rfp.quote_count !== 1 ? 's' : ''} submitted
                        </span>
                        {rfp.created_at && (
                          <span className="text-xs text-onyx-muted">
                            {new Date(rfp.created_at).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant="primary"
                      onClick={() => {
                        const price = window.prompt('Your quote price ($):');
                        const desc = window.prompt('Description / notes:');
                        if (!price) return;
                        fetch('/api/seller/quotes', {
                          method: 'POST',
                          headers: { ...authHeaders(), 'Content-Type': 'application/json' },
                          body: JSON.stringify({
                            row_id: rfp.row_id,
                            price: parseFloat(price),
                            description: desc || '',
                          }),
                        }).then(() => loadData('quotes'));
                      }}
                    >
                      Submit Quote
                    </Button>
                  </div>
                </Card>
              ))
            )}
          </div>
        )}

        {!loading && !error && activeTab === 'quotes' && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-onyx">
              My Quotes ({quotes.length})
            </h2>
            {quotes.length === 0 ? (
              <Card className="p-8 text-center text-onyx-muted">
                You haven&apos;t submitted any quotes yet.
              </Card>
            ) : (
              quotes.map((q) => (
                <Card key={q.id} className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold text-onyx">
                        {q.row_title || `Row #${q.row_id}`}
                      </h3>
                      {q.description && (
                        <p className="text-sm text-onyx-muted mt-1 line-clamp-2">
                          {q.description}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-3">
                      {q.price != null && (
                        <span className="text-lg font-bold text-onyx">
                          ${q.price.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                        </span>
                      )}
                      {statusBadge(q.status)}
                    </div>
                  </div>
                </Card>
              ))
            )}
          </div>
        )}

        {!loading && !error && activeTab === 'profile' && profile && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-onyx">Business Profile</h2>
            <Card className="p-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-onyx-muted uppercase">Company</label>
                  <p className="text-onyx font-semibold">{profile.business_name}</p>
                </div>
                <div>
                  <label className="text-xs font-medium text-onyx-muted uppercase">Contact</label>
                  <p className="text-onyx">{profile.contact_name || '—'}</p>
                </div>
                <div>
                  <label className="text-xs font-medium text-onyx-muted uppercase">Email</label>
                  <p className="text-onyx">{profile.email || '—'}</p>
                </div>
                <div>
                  <label className="text-xs font-medium text-onyx-muted uppercase">Phone</label>
                  <p className="text-onyx">{profile.phone || '—'}</p>
                </div>
                <div>
                  <label className="text-xs font-medium text-onyx-muted uppercase">Categories</label>
                  <p className="text-onyx">{profile.categories || '—'}</p>
                </div>
                <div>
                  <label className="text-xs font-medium text-onyx-muted uppercase">Service Areas</label>
                  <p className="text-onyx">{profile.service_areas || '—'}</p>
                </div>
                <div className="col-span-2">
                  <label className="text-xs font-medium text-onyx-muted uppercase">Website</label>
                  <p className="text-onyx">{profile.website || '—'}</p>
                </div>
              </div>
            </Card>
          </div>
        )}
      </main>
    </div>
  );
}
