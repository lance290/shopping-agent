import Link from 'next/link';
import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { ExternalLink, MapPin, Store } from 'lucide-react';

interface VendorCard {
  id: number;
  slug: string;
  name: string;
  tagline?: string | null;
  description?: string | null;
  category?: string | null;
  store_geo_location?: string | null;
  website?: string | null;
  image_url?: string | null;
  is_verified?: boolean;
  tier_affinity?: string | null;
}

interface VendorListResponse {
  vendors: VendorCard[];
  total: number;
  page: number;
  page_size: number;
}

function toSlug(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80);
}

function toTitleCase(s: string): string {
  return s
    .split(/[-_\s]+/g)
    .filter(Boolean)
    .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
    .join(' ');
}

async function fetchVendors(city: string, category: string, page: number): Promise<VendorListResponse | null> {
  const backendBase = (process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');
  const url = new URL(`${backendBase}/api/public/vendors/filter`);
  url.searchParams.set('city', city);
  url.searchParams.set('category', category);
  url.searchParams.set('page', String(page));
  url.searchParams.set('page_size', '24');

  const res = await fetch(url.toString(), { cache: 'no-store' });
  if (!res.ok) return null;
  return (await res.json()) as VendorListResponse;
}

export async function generateMetadata(
  { params, searchParams }: { params: Promise<{ city: string; category: string }>; searchParams?: Promise<{ page?: string }> }
): Promise<Metadata> {
  const resolvedParams = await params;
  const city = toTitleCase(decodeURIComponent(resolvedParams.city));
  const category = toTitleCase(decodeURIComponent(resolvedParams.category));
  const page = Number((await searchParams)?.page || '1') || 1;

  return {
    title: `${category} in ${city} | Vendor Directory${page > 1 ? ` (Page ${page})` : ''}`,
    description: `Browse ${category} vendors serving ${city}. Compare providers and click through to vendor websites.`,
  };
}

export default async function LocationCategoryVendorsPage(
  { params, searchParams }: { params: Promise<{ city: string; category: string }>; searchParams?: Promise<{ page?: string }> }
) {
  const resolvedParams = await params;
  const citySlug = toSlug(decodeURIComponent(resolvedParams.city));
  const categorySlug = toSlug(decodeURIComponent(resolvedParams.category));
  const city = toTitleCase(citySlug);
  const category = toTitleCase(categorySlug);
  const page = Number((await searchParams)?.page || '1') || 1;

  const data = await fetchVendors(city, category, page);
  if (!data) {
    notFound();
  }

  const totalPages = Math.max(1, Math.ceil((data.total || 0) / (data.page_size || 24)));

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-10">
        <div className="flex flex-wrap items-center gap-2 text-sm text-gray-500 mb-4">
          <Link href="/vendors" className="hover:underline">
            Vendor Directory
          </Link>
          <span>/</span>
          <span className="inline-flex items-center gap-1">
            <MapPin size={14} /> {city}
          </span>
          <span>/</span>
          <span className="inline-flex items-center gap-1">
            <Store size={14} /> {category}
          </span>
        </div>

        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900">
          {category} in {city}
        </h1>
        <p className="text-gray-600 mt-3 max-w-2xl">
          {data.total} vendors found. Click a vendor to view details, or click through to their website.
        </p>
      </div>

      {data.vendors.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          No vendors found for this city/category.
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {data.vendors.map((vendor) => (
            <div
              key={vendor.slug || vendor.id}
              className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm flex flex-col"
            >
              <Link href={`/vendors/${vendor.slug}`} className="block">
                <div className="flex items-center gap-2 mb-2">
                  <Store size={14} className="text-blue-600 shrink-0" />
                  {vendor.category && (
                    <span className="text-[10px] font-medium uppercase tracking-wider text-blue-600">
                      {vendor.category}
                    </span>
                  )}
                  {vendor.is_verified && (
                    <span className="text-[10px] bg-green-500/15 text-green-700 px-2 py-0.5 rounded-full">
                      Verified
                    </span>
                  )}
                </div>

                <h2 className="font-semibold text-gray-900 text-sm mb-1">{vendor.name}</h2>

                {vendor.tagline ? (
                  <p className="text-xs text-gray-500 mb-2 line-clamp-2">{vendor.tagline}</p>
                ) : vendor.description ? (
                  <p className="text-xs text-gray-500 mb-2 line-clamp-2">{vendor.description}</p>
                ) : null}

                {vendor.store_geo_location && (
                  <p className="text-[11px] text-gray-400 line-clamp-2">{vendor.store_geo_location}</p>
                )}
              </Link>

              <div className="mt-auto pt-4">
                {vendor.website ? (
                  <a
                    href={`/api/out?url=${encodeURIComponent(vendor.website)}&merchant=${encodeURIComponent(vendor.name)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
                  >
                    Visit website <ExternalLink size={12} />
                  </a>
                ) : (
                  <span className="text-xs text-gray-400">Website not listed</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-10">
          <Link
            href={`/locations/${citySlug}/${categorySlug}/vendors?page=${Math.max(1, page - 1)}`}
            aria-disabled={page <= 1}
            className={`px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 ${page <= 1 ? 'pointer-events-none opacity-50' : ''}`}
          >
            Previous
          </Link>
          <span className="px-4 py-2 text-sm text-gray-600">
            Page {page} of {totalPages}
          </span>
          <Link
            href={`/locations/${citySlug}/${categorySlug}/vendors?page=${Math.min(totalPages, page + 1)}`}
            aria-disabled={page >= totalPages}
            className={`px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 ${page >= totalPages ? 'pointer-events-none opacity-50' : ''}`}
          >
            Next
          </Link>
        </div>
      )}
    </div>
  );
}
