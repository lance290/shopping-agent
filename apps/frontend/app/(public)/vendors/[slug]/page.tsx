import { notFound } from 'next/navigation';
import { Store, ExternalLink, MapPin, Tag, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import type { Metadata } from 'next';

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
  service_areas?: unknown;
  website?: string | null;
  image_url?: string | null;
  is_verified: boolean;
  tier_affinity?: string | null;
  seo_content?: VendorSeoContent | null;
  schema_markup?: Record<string, unknown> | null;
}

async function fetchVendor(slug: string): Promise<VendorDetail | null> {
  const backendBase = (process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');
  const res = await fetch(`${backendBase}/api/public/vendors/slug/${encodeURIComponent(slug)}`, {
    cache: 'no-store',
  });
  if (res.status === 404) return null;
  if (!res.ok) return null;
  return (await res.json()) as VendorDetail;
}

export async function generateMetadata(
  { params }: { params: Promise<{ slug: string }> }
): Promise<Metadata> {
  const resolvedParams = await params;
  const vendor = await fetchVendor(resolvedParams.slug);
  if (!vendor) {
    return { title: 'Vendor Not Found' };
  }
  const summary = vendor?.seo_content?.summary || vendor?.description || vendor?.tagline || '';
  return {
    title: `${vendor.name} | Vendor Directory`,
    description: typeof summary === 'string' ? summary.slice(0, 155) : undefined,
  };
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

export default async function VendorDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const resolvedParams = await params;
  const vendor = await fetchVendor(resolvedParams.slug);
  if (!vendor) {
    notFound();
  }

  const specialties = normalizeToStringArray(vendor.specialties);
  const serviceAreas = normalizeToStringArray(vendor.service_areas);
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
      <Link href="/vendors" className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline mb-6">
        <ArrowLeft size={14} /> Back to directory
      </Link>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-8">
          <div className="flex items-center gap-3 mb-2">
            <Store size={20} className="text-blue-200" />
            {vendor.category && (
              <span className="text-xs font-medium uppercase tracking-wider text-blue-200">{vendor.category}</span>
            )}
            {vendor.is_verified && (
              <span className="text-xs bg-green-500/20 text-green-200 px-2 py-0.5 rounded-full">Verified</span>
            )}
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white">{vendor.name}</h1>
          {vendor.tagline && (
            <p className="text-blue-100 mt-2">{vendor.tagline}</p>
          )}
        </div>

        <div className="p-6 space-y-6">
          {typeof seo.summary === 'string' && seo.summary && (
            <div>
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">Summary</h2>
              <p className="text-gray-700 leading-relaxed whitespace-pre-line">{seo.summary}</p>
            </div>
          )}

          {vendor.description && (
            <div>
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">About</h2>
              <p className="text-gray-700 leading-relaxed whitespace-pre-line">{vendor.description}</p>
            </div>
          )}

          {Array.isArray(seo.services_list) && seo.services_list.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">Services</h2>
              <ul className="space-y-2">
                {seo.services_list.map((s: unknown, i: number) => (
                  <li key={i} className="text-gray-700">{String(s)}</li>
                ))}
              </ul>
            </div>
          )}

          {Array.isArray(seo.features_matrix) && seo.features_matrix.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">Features</h2>
              <div className="space-y-3">
                {seo.features_matrix.map((f, i: number) => (
                  <div key={i} className="rounded-lg border border-gray-100 p-3">
                    <div className="font-medium text-gray-900 text-sm">
                      {String(f?.feature || '')}
                    </div>
                    {f?.details && (
                      <div className="text-gray-700 text-sm mt-1">{String(f.details)}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {specialties.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">Specialties</h2>
              <div className="flex flex-wrap gap-2">
                {specialties.map((s, i) => (
                  <span key={i} className="inline-flex items-center gap-1 px-3 py-1 bg-blue-50 text-blue-700 text-sm rounded-full">
                    <Tag size={12} /> {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          {serviceAreas.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">Service Areas</h2>
              <div className="flex flex-wrap gap-2">
                {serviceAreas.map((area, i) => (
                  <span key={i} className="inline-flex items-center gap-1 px-3 py-1 bg-gray-100 text-gray-700 text-sm rounded-full">
                    <MapPin size={12} /> {area}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="flex flex-col sm:flex-row gap-3 pt-4 border-t border-gray-100">
            {vendor.website && (
              <a
                href={vendor.website}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-gray-900 hover:bg-gray-800 text-white font-medium rounded-lg transition-colors"
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
