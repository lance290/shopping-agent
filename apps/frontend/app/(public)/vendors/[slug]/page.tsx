'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Store, ExternalLink, Tag, ArrowLeft, Loader2 } from 'lucide-react';
import Link from 'next/link';

interface VendorSeoContent {
  summary?: string;
  services_list?: string[];
  features_matrix?: Array<{ feature?: string; details?: string }>;
  pricing_model?: string;
  pros?: string[];
  cons?: string[];
}

interface VendorDetail {
  id: number;
  slug: string;
  name: string;
  tagline?: string | null;
  description?: string | null;
  category?: string | null;
  specialties?: string | null;
  website?: string | null;
  image_url?: string | null;
  is_verified: boolean;
  tier_affinity?: string | null;
  seo_content?: VendorSeoContent | null;
  schema_markup?: Record<string, unknown> | null;
}

function normalizeToStringArray(val: unknown): string[] {
  if (!val) return [];
  if (Array.isArray(val)) return val.map((v) => String(v)).filter(Boolean);
  if (typeof val === 'string') {
    try {
      const parsed = JSON.parse(val);
      if (Array.isArray(parsed)) return parsed.map((v) => String(v)).filter(Boolean);
    } catch {
      return val.split(',').map((s) => s.trim()).filter(Boolean);
    }
    return val.split(',').map((s) => s.trim()).filter(Boolean);
  }
  if (typeof val === 'object') {
    return [JSON.stringify(val)];
  }
  return [String(val)];
}

export default function VendorDetailPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const [vendor, setVendor] = useState<VendorDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
    fetch(`/api/proxy/public-vendors/slug/${encodeURIComponent(slug)}`)
      .then(async (res) => {
        if (res.status === 404 || !res.ok) {
          setNotFound(true);
          return;
        }
        const data = await res.json();
        setVendor(data);
        if (data.name) {
          document.title = `${data.name} | Vendor Directory`;
        }
      })
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
        <Loader2 className="w-8 h-8 animate-spin text-navy mx-auto mb-4" />
        <p className="text-ink-muted">Loading vendor details...</p>
      </div>
    );
  }

  if (notFound || !vendor) {
    return (
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
        <Store className="w-12 h-12 text-ink-muted mx-auto mb-4" />
        <h1 className="text-xl font-bold text-navy mb-2">Vendor Not Found</h1>
        <p className="text-ink-muted mb-6">The vendor you&apos;re looking for doesn&apos;t exist or has been removed.</p>
        <Link href="/vendors" className="text-sm text-navy hover:text-navy-light font-medium underline">
          Browse all vendors
        </Link>
      </div>
    );
  }

  const specialties = normalizeToStringArray(vendor.specialties);
  const seo: VendorSeoContent = vendor.seo_content || {};
  const schemaMarkup = vendor.schema_markup || null;

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      {schemaMarkup && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(schemaMarkup) }}
        />
      )}
      <Link href="/vendors" className="inline-flex items-center gap-1 text-sm text-navy hover:underline mb-6">
        <ArrowLeft size={14} /> Back to directory
      </Link>

      <div className="bg-white rounded-xl border border-warm-grey overflow-hidden">
        <div className="bg-gradient-to-r from-navy to-navy-light px-6 py-8">
          <div className="flex items-center gap-3 mb-2">
            <Store size={20} className="text-gold-light" />
            {vendor.category && (
              <span className="text-xs font-medium uppercase tracking-wider text-gold-light">{vendor.category}</span>
            )}
            {vendor.is_verified && (
              <span className="text-xs bg-status-success/20 text-green-200 px-2 py-0.5 rounded-full">Verified</span>
            )}
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white">{vendor.name}</h1>
          {vendor.tagline && (
            <p className="text-white/80 mt-2">{vendor.tagline}</p>
          )}
        </div>

        <div className="p-6 space-y-6">
          {typeof seo.summary === 'string' && seo.summary && (
            <div>
              <h2 className="text-sm font-semibold text-ink-muted uppercase tracking-wider mb-2">Summary</h2>
              <p className="text-navy leading-relaxed whitespace-pre-line">{seo.summary}</p>
            </div>
          )}

          {vendor.description && (
            <div>
              <h2 className="text-sm font-semibold text-ink-muted uppercase tracking-wider mb-2">About</h2>
              <p className="text-navy leading-relaxed whitespace-pre-line">{vendor.description}</p>
            </div>
          )}

          {Array.isArray(seo.services_list) && seo.services_list.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-ink-muted uppercase tracking-wider mb-2">Services</h2>
              <ul className="space-y-2">
                {seo.services_list.map((s: unknown, i: number) => (
                  <li key={i} className="text-navy">{String(s)}</li>
                ))}
              </ul>
            </div>
          )}

          {Array.isArray(seo.features_matrix) && seo.features_matrix.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-ink-muted uppercase tracking-wider mb-2">Features</h2>
              <div className="space-y-3">
                {seo.features_matrix.map((f, i: number) => (
                  <div key={i} className="rounded-lg border border-warm-grey p-3">
                    <div className="font-medium text-navy text-sm">
                      {String(f?.feature || '')}
                    </div>
                    {f?.details && (
                      <div className="text-ink-muted text-sm mt-1">{String(f.details)}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {specialties.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-ink-muted uppercase tracking-wider mb-2">Specialties</h2>
              <div className="flex flex-wrap gap-2">
                {specialties.map((s, i) => (
                  <span key={i} className="inline-flex items-center gap-1 px-3 py-1 bg-canvas-dark text-navy text-sm rounded-full">
                    <Tag size={12} /> {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="flex flex-col sm:flex-row gap-3 pt-4 border-t border-warm-grey">
            {vendor.website && (
              <a
                href={`/api/out?url=${encodeURIComponent(vendor.website)}&merchant=${encodeURIComponent(vendor.name)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-navy hover:bg-navy-light text-white font-medium rounded-lg transition-colors"
              >
                <ExternalLink size={16} /> Visit Website
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
