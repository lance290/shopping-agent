'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';

interface CampaignInfo {
  id: number;
  brand_name: string;
  category: string;
  target_product: string | null;
  intent_count: number;
}

function BrandClaimForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get('token');

  const [campaign, setCampaign] = useState<CampaignInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Form state
  const [swapProductName, setSwapProductName] = useState('');
  const [savingsCents, setSavingsCents] = useState('');
  const [offerDescription, setOfferDescription] = useState('');
  const [swapProductUrl, setSwapProductUrl] = useState('');
  const [terms, setTerms] = useState('');

  useEffect(() => {
    if (!token) {
      setError('Missing token. Please use the link from your email.');
      setLoading(false);
      return;
    }

    async function verifyToken() {
      try {
        const res = await fetch(`/api/pop/brands/claim?token=${encodeURIComponent(token!)}`);
        if (res.status === 410) {
          setError('This link has expired or already been used.');
        } else if (!res.ok) {
          setError('Invalid link. Please check your email for the correct URL.');
        } else {
          const data = await res.json();
          setCampaign(data.campaign);
        }
      } catch {
        setError('Unable to verify your link. Please try again.');
      } finally {
        setLoading(false);
      }
    }
    verifyToken();
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !swapProductName.trim() || !savingsCents) return;

    setSubmitting(true);
    try {
      const res = await fetch('/api/pop/brands/claim', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token,
          swap_product_name: swapProductName.trim(),
          savings_cents: parseInt(savingsCents, 10),
          offer_description: offerDescription.trim() || null,
          swap_product_url: swapProductUrl.trim() || null,
          terms: terms.trim() || null,
        }),
      });

      if (res.ok) {
        setSubmitted(true);
      } else {
        const data = await res.json();
        setError(data.detail || 'Submission failed');
      }
    } catch {
      setError('Network error. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-white flex flex-col items-center justify-center gap-4 px-4">
        <span className="text-4xl">😕</span>
        <p className="text-gray-600 text-center">{error}</p>
        <Link href="/" className="text-green-600 hover:text-green-700 font-medium">
          Go to PopSavings
        </Link>
      </div>
    );
  }

  if (submitted) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-green-50 to-white flex flex-col items-center justify-center gap-6 px-4">
        <span className="text-5xl">🎉</span>
        <h1 className="text-2xl font-bold text-gray-900">Coupon Published!</h1>
        <p className="text-gray-600 text-center max-w-md">
          Your coupon is now live and will appear on shopping lists that include{' '}
          <strong>{campaign?.target_product || campaign?.category}</strong>.
        </p>
        <p className="text-sm text-gray-400">
          {campaign?.intent_count ? `${campaign.intent_count.toLocaleString()} shoppers` : 'Shoppers'} are looking for this product.
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-green-50 to-white">
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-2xl mx-auto px-4 h-14 flex items-center gap-2">
          <Image src="/pop-avatar.png" alt="Pop" width={32} height={32} className="rounded-full" />
          <span className="text-lg font-bold text-green-700">Pop Brand Portal</span>
        </div>
      </nav>

      <div className="max-w-xl mx-auto px-4 py-8">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <h1 className="text-xl font-bold text-gray-900 mb-1">Add a Coupon</h1>
          <p className="text-sm text-gray-500 mb-6">
            {campaign?.intent_count
              ? `${campaign.intent_count.toLocaleString()} PopSavings shoppers want`
              : 'PopSavings shoppers want'}{' '}
            <strong>{campaign?.target_product || campaign?.category}</strong>.
            Add a coupon to reach them directly on their shopping lists.
          </p>

          <div className="bg-green-50 rounded-lg px-4 py-3 mb-6">
            <div className="text-xs text-green-600 font-medium">Campaign for</div>
            <div className="text-sm font-semibold text-gray-900">{campaign?.brand_name}</div>
            <div className="text-xs text-gray-500">
              {campaign?.category}{campaign?.target_product ? ` — ${campaign.target_product}` : ''}
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Product Name *
              </label>
              <input
                type="text"
                value={swapProductName}
                onChange={(e) => setSwapProductName(e.target.value)}
                placeholder="e.g. Tide Pods 42ct"
                required
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-gray-900"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Discount Amount (cents) *
              </label>
              <input
                type="number"
                value={savingsCents}
                onChange={(e) => setSavingsCents(e.target.value)}
                placeholder="e.g. 100 for $1.00 off"
                required
                min={1}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-gray-900"
              />
              {savingsCents && parseInt(savingsCents, 10) > 0 && (
                <p className="text-xs text-green-600 mt-1">
                  = ${(parseInt(savingsCents, 10) / 100).toFixed(2)} off
                </p>
              )}
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Offer Description
              </label>
              <input
                type="text"
                value={offerDescription}
                onChange={(e) => setOfferDescription(e.target.value)}
                placeholder="e.g. Save $1.00 on Tide Pods"
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-gray-900"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Coupon/Landing Page URL
              </label>
              <input
                type="url"
                value={swapProductUrl}
                onChange={(e) => setSwapProductUrl(e.target.value)}
                placeholder="https://..."
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-gray-900"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Terms & Conditions
              </label>
              <textarea
                value={terms}
                onChange={(e) => setTerms(e.target.value)}
                placeholder="Optional fine print..."
                rows={2}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-gray-900 resize-none"
              />
            </div>

            <button
              type="submit"
              disabled={submitting || !swapProductName.trim() || !savingsCents}
              className="w-full bg-green-600 text-white font-medium py-3 rounded-xl hover:bg-green-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              {submitting ? 'Publishing...' : 'Publish Coupon'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default function BrandClaimPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600" />
      </div>
    }>
      <BrandClaimForm />
    </Suspense>
  );
}
