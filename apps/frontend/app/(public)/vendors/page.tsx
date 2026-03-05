'use client';

import { useState, useEffect } from 'react';
import { Search, Store, ExternalLink, Loader2, MapPin } from 'lucide-react';

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

interface FacetCombo {
  city: string;
  category: string;
}

function toSlug(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80);
}

export default function VendorsPage() {
  const [query, setQuery] = useState('');
  const [vendors, setVendors] = useState<VendorCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [facets, setFacets] = useState<FacetCombo[]>([]);

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

  // Load geo facets for internal links
  useEffect(() => {
    const loadFacets = async () => {
      try {
        const res = await fetch('/api/proxy/public-vendors/facets');
        if (res.ok) {
          const data = await res.json();
          setFacets((data.combos || []).slice(0, 60));
        }
      } catch { /* non-critical */ }
    };
    loadFacets();
  }, []);

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
    <div className="bg-canvas-dark min-h-screen">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold text-ink mb-3">Vendor Directory</h1>
          <p className="text-base text-ink-muted max-w-2xl mx-auto mb-6">
            Browse our network of 3,000+ vendors — from local artisans to specialized service providers.
          </p>

          <form onSubmit={handleSearch} className="max-w-xl mx-auto">
            <div className="flex">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search vendors (e.g., caterers in San Francisco)"
                className="flex-1 pl-4 pr-4 py-2.5 border border-warm-grey rounded-l-md text-sm text-ink bg-white focus:outline-none focus:ring-2 focus:ring-gold focus:border-transparent placeholder:text-onyx-muted"
              />
              <button
                type="submit"
                className="px-5 py-2.5 bg-gold hover:bg-gold-dark rounded-r-md transition-colors"
                aria-label="Search"
              >
                <Search className="h-5 w-5 text-navy" />
              </button>
            </div>
          </form>

          {query.trim() && (
            <button onClick={clearSearch} className="mt-3 text-sm text-accent-blue hover:underline">
              Clear search — show all vendors
            </button>
          )}
        </div>

        {(loading || searching) && (
          <div className="flex justify-center py-12">
            <Loader2 className="h-8 w-8 text-gold animate-spin" />
          </div>
        )}

        {!loading && !searching && vendors.length === 0 && (
          <div className="text-center py-12">
            <Store className="mx-auto h-12 w-12 text-onyx-muted mb-4" />
            <p className="text-ink-muted">No vendors found. Try a different search.</p>
          </div>
        )}

        {!loading && !searching && vendors.length > 0 && (
          <>
            <p className="text-sm text-ink-muted mb-4">
              {query.trim()
                ? `${total} vendors matching "${query}"`
                : `${total} vendors in our network`}
            </p>

            <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {vendors.map((vendor, idx) => (
                <a
                  key={vendor.slug || vendor.id || idx}
                  href={vendor.slug ? `/vendors/${vendor.slug}` : '#'}
                  className="bg-white rounded-lg border border-warm-grey p-4 hover:shadow-md hover:border-border-hover transition-all flex flex-col"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Store size={14} className="text-gold-dark shrink-0" />
                    {vendor.category && (
                      <span className="text-[10px] font-medium uppercase tracking-wider text-ink-muted">{vendor.category}</span>
                    )}
                    {vendor.is_verified && (
                      <span className="text-[10px] font-medium bg-status-success/10 text-status-success px-1.5 py-0.5 rounded">Verified</span>
                    )}
                  </div>
                  <h3 className="font-semibold text-ink text-sm mb-1">{vendor.name}</h3>
                  {vendor.tagline && (
                    <p className="text-xs text-ink-muted mb-2 line-clamp-2">{vendor.tagline}</p>
                  )}
                  {vendor.description && !vendor.tagline && (
                    <p className="text-xs text-ink-muted mb-2 line-clamp-2">{vendor.description}</p>
                  )}
                  <div className="mt-auto pt-2">
                    {vendor.website && (
                      <span className="text-xs text-accent-blue inline-flex items-center gap-1">
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
                  className="px-4 py-2 text-sm border border-warm-grey rounded-lg disabled:opacity-50 hover:bg-white hover:border-border-hover transition-colors"
                >
                  Previous
                </button>
                <span className="px-4 py-2 text-sm text-ink-muted">
                  Page {page} of {Math.ceil(total / 24)}
                </span>
                <button
                  onClick={() => setPage(page + 1)}
                  disabled={page >= Math.ceil(total / 24)}
                  className="px-4 py-2 text-sm border border-warm-grey rounded-lg disabled:opacity-50 hover:bg-white hover:border-border-hover transition-colors"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
        {!query.trim() && facets.length > 0 && (
          <div className="mt-12 border-t border-warm-grey pt-8">
            <h2 className="text-lg font-semibold text-ink mb-4 flex items-center gap-2">
              <MapPin size={18} className="text-gold-dark" /> Browse by Location &amp; Category
            </h2>
            <div className="flex flex-wrap gap-2">
              {facets.map((f, i) => (
                <a
                  key={i}
                  href={`/locations/${toSlug(f.city)}/${toSlug(f.category)}/vendors`}
                  className="px-3 py-1.5 text-xs bg-white border border-warm-grey hover:border-gold hover:bg-gold/5 text-ink-muted hover:text-ink rounded-full transition-colors"
                >
                  {f.category} in {f.city}
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
