'use client';

import { useState, useEffect } from 'react';
import { Search, Store, ExternalLink, Loader2 } from 'lucide-react';

interface VendorCard {
  id?: number;
  slug?: string;
  name: string;
  tagline?: string | null;
  description?: string | null;
  category?: string | null;
  specialties?: string | null;
  website?: string | null;
  image_url?: string | null;
  is_verified?: boolean;
}

export default function VendorsPage() {
  const [query, setQuery] = useState('');
  const [vendors, setVendors] = useState<VendorCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);

  // Load initial vendor list
  useEffect(() => {
    const loadVendors = async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/proxy/public-vendors?page=${page}&page_size=24`);
        if (res.ok) {
          const data = await res.json();
          setVendors(data.vendors || []);
          setTotal(data.total || 0);
        }
      } catch (err) {
        console.error('Failed to load vendors:', err);
      } finally {
        setLoading(false);
      }
    };
    if (!query.trim()) {
      loadVendors();
    }
  }, [page, query]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;

    setSearching(true);
    try {
      const res = await fetch(`/api/proxy/public-vendors/search?q=${encodeURIComponent(trimmed)}&limit=24`);
      if (res.ok) {
        const data = await res.json();
        setVendors(data.vendors || []);
        setTotal(data.count || 0);
      }
    } catch (err) {
      console.error('Vendor search failed:', err);
    } finally {
      setSearching(false);
    }
  };

  const clearSearch = () => {
    setQuery('');
    setPage(1);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="text-center mb-10">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">Vendor Directory</h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto mb-8">
          Search our network of 3,000+ vendors — from local artisans to specialized service providers.
        </p>

        <form onSubmit={handleSearch} className="max-w-xl mx-auto">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search vendors (e.g., caterers in San Francisco)"
              className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-full text-base focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </form>

        {query.trim() && (
          <button onClick={clearSearch} className="mt-3 text-sm text-blue-600 hover:underline">
            Clear search — show all vendors
          </button>
        )}
      </div>

      {(loading || searching) && (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
        </div>
      )}

      {!loading && !searching && vendors.length === 0 && (
        <div className="text-center py-12">
          <Store className="mx-auto h-12 w-12 text-gray-300 mb-4" />
          <p className="text-gray-500">No vendors found. Try a different search.</p>
        </div>
      )}

      {!loading && !searching && vendors.length > 0 && (
        <>
          <p className="text-sm text-gray-500 mb-6">
            {query.trim()
              ? `${total} vendors matching "${query}"`
              : `${total} vendors in our network`}
          </p>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {vendors.map((vendor, idx) => (
              <a
                key={vendor.slug || vendor.id || idx}
                href={vendor.slug ? `/vendors/${vendor.slug}` : '#'}
                className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col"
              >
                <div className="flex items-center gap-2 mb-2">
                  <Store size={14} className="text-blue-600 shrink-0" />
                  {vendor.category && (
                    <span className="text-[10px] font-medium uppercase tracking-wider text-blue-600">{vendor.category}</span>
                  )}
                </div>
                <h3 className="font-semibold text-gray-900 text-sm mb-1">{vendor.name}</h3>
                {vendor.tagline && (
                  <p className="text-xs text-gray-500 mb-2 line-clamp-2">{vendor.tagline}</p>
                )}
                {vendor.description && !vendor.tagline && (
                  <p className="text-xs text-gray-500 mb-2 line-clamp-2">{vendor.description}</p>
                )}
                <div className="mt-auto pt-2">
                  {vendor.website && (
                    <span className="text-xs text-blue-600 inline-flex items-center gap-1">
                      Visit website <ExternalLink size={10} />
                    </span>
                  )}
                </div>
              </a>
            ))}
          </div>

          {!query.trim() && total > 24 && (
            <div className="flex justify-center gap-2 mt-8">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page <= 1}
                className="px-4 py-2 text-sm border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50"
              >
                Previous
              </button>
              <span className="px-4 py-2 text-sm text-gray-600">
                Page {page} of {Math.ceil(total / 24)}
              </span>
              <button
                onClick={() => setPage(page + 1)}
                disabled={page >= Math.ceil(total / 24)}
                className="px-4 py-2 text-sm border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
