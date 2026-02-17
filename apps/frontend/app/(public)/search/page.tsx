'use client';

import { useSearchParams } from 'next/navigation';
import { useEffect, useState, Suspense } from 'react';
import PublicOfferCard from '../../../components/PublicOfferCard';
import AffiliateDisclosure from '../../../components/AffiliateDisclosure';
import type { PublicOffer } from '../../../components/PublicOfferCard';
import { Search, Loader2 } from 'lucide-react';

interface SearchResponse {
  results: PublicOffer[];
  provider_statuses: Array<{
    provider_id: string;
    status: string;
    result_count: number;
    latency_ms: number | null;
    message: string | null;
  }>;
  query_optimized: string | null;
  desire_tier: string | null;
  result_count: number;
}

function SearchResults() {
  const searchParams = useSearchParams();
  const query = searchParams?.get('q') || '';
  const [results, setResults] = useState<PublicOffer[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchInfo, setSearchInfo] = useState<{ optimized: string | null; tier: string | null }>({ optimized: null, tier: null });

  useEffect(() => {
    if (!query.trim()) return;

    const runSearch = async () => {
      setLoading(true);
      setError(null);
      setResults([]);

      try {
        const res = await fetch('/api/proxy/public-search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: query.trim() }),
        });

        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || data.error || `Search failed (${res.status})`);
        }

        const data: SearchResponse = await res.json();
        setResults(data.results || []);
        setSearchInfo({ optimized: data.query_optimized, tier: data.desire_tier });
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Search failed';
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    runSearch();
  }, [query]);

  const handleRequestQuote = (offer: PublicOffer) => {
    // Fire quote intent tracking
    fetch('/api/proxy/quote-intent', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        vendor_slug: offer.vendor_company?.toLowerCase().replace(/\s+/g, '-') || null,
        vendor_name: offer.vendor_company || offer.vendor_name || offer.title,
      }),
    }).catch(() => {}); // fire-and-forget

    // Open mailto with pre-filled template
    const vendorName = offer.vendor_company || offer.vendor_name || 'Vendor';
    const subject = `Quote request — ${query}`;
    const body = `Hi ${vendorName},\n\nI found you on BuyAnything and I'm looking for: ${query}\n\nCould you provide a quote?\n\nThank you`;
    const params = new URLSearchParams();
    params.set('subject', subject);
    params.set('body', body);

    // If we have vendor email from raw_data, use it; otherwise open generic
    if (offer.vendor_website) {
      window.open(offer.vendor_website, '_blank', 'noopener');
    }
  };

  if (!query.trim()) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-20 text-center">
        <Search className="mx-auto h-12 w-12 text-gray-300 mb-4" />
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Search for anything</h1>
        <p className="text-gray-500">Enter a query in the search bar above to find products and vendors.</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          Results for &ldquo;{query}&rdquo;
        </h1>
        {searchInfo.optimized && searchInfo.optimized !== query && (
          <p className="text-sm text-gray-500 mt-1">
            Searched as: &ldquo;{searchInfo.optimized}&rdquo;
          </p>
        )}
      </div>

      <AffiliateDisclosure className="mb-6" />

      {loading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="h-8 w-8 text-blue-600 animate-spin mb-4" />
          <p className="text-gray-500">Searching all providers...</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {!loading && !error && results.length === 0 && (
        <div className="text-center py-20">
          <p className="text-gray-500 text-lg">No results found. Try a different search.</p>
        </div>
      )}

      {results.length > 0 && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {results.map((offer, idx) => (
              <PublicOfferCard
                key={`${offer.source}-${offer.url || idx}`}
                offer={offer}
                onRequestQuote={handleRequestQuote}
              />
            ))}
          </div>

          <div className="mt-8 text-center">
            <p className="text-sm text-gray-500 mb-4">
              {results.length} results from multiple sources
            </p>
            <div className="inline-flex items-center gap-2 bg-gray-50 rounded-full px-4 py-2">
              <span className="text-sm text-gray-600">Want to save and track results?</span>
              <a href="/login" className="text-sm font-medium text-blue-600 hover:text-blue-700">
                Sign in
              </a>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
      </div>
    }>
      <SearchResults />
    </Suspense>
  );
}
