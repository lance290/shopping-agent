'use client';

import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Store, ExternalLink, MapPin, Tag, Loader2, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

interface VendorDetail {
  id: number;
  slug: string;
  name: string;
  tagline?: string | null;
  description?: string | null;
  category?: string | null;
  specialties?: string | null;
  service_areas?: string | null;
  website?: string | null;
  image_url?: string | null;
  is_verified: boolean;
  tier_affinity?: string | null;
}

export default function VendorDetailPage() {
  const params = useParams();
  const vendorId = params?.slug as string;
  const [vendor, setVendor] = useState<VendorDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadVendor = async () => {
      try {
        const res = await fetch(`/api/proxy/public-vendors/${vendorId}`);
        if (!res.ok) {
          throw new Error(res.status === 404 ? 'Vendor not found' : 'Failed to load vendor');
        }
        const data = await res.json();
        setVendor(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load vendor');
      } finally {
        setLoading(false);
      }
    };
    if (vendorId) loadVendor();
  }, [vendorId]);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
      </div>
    );
  }

  if (error || !vendor) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-20 text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Vendor Not Found</h1>
        <p className="text-gray-500 mb-6">{error || 'This vendor does not exist.'}</p>
        <Link href="/vendors" className="text-blue-600 hover:underline">Browse all vendors</Link>
      </div>
    );
  }

  const parseJson = (val: string | null | undefined): string[] => {
    if (!val) return [];
    try {
      const parsed = JSON.parse(val);
      return Array.isArray(parsed) ? parsed : [String(parsed)];
    } catch {
      return val.split(',').map((s) => s.trim()).filter(Boolean);
    }
  };

  const specialties = parseJson(vendor.specialties);
  const serviceAreas = parseJson(vendor.service_areas);

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
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
          {vendor.description && (
            <div>
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">About</h2>
              <p className="text-gray-700 leading-relaxed whitespace-pre-line">{vendor.description}</p>
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
            <button
              onClick={() => {
                // Fire quote intent
                fetch('/api/proxy/quote-intent', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    query: vendor.name,
                    vendor_slug: vendor.slug,
                    vendor_name: vendor.name,
                  }),
                }).catch(() => {});

                // Open mailto
                const subject = `Quote request — ${vendor.name}`;
                const body = `Hi ${vendor.name},\n\nI found you on BuyAnything and would like to request a quote.\n\nCould you provide more information about your services?\n\nThank you`;
                const params = new URLSearchParams({ subject, body });
                if (vendor.website) {
                  window.open(vendor.website, '_blank', 'noopener');
                }
              }}
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
            >
              Request Quote
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
