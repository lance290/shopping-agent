import type { MetadataRoute } from 'next';

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://buy-anything.com';
const BACKEND_URL = (process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');

function toSlug(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80);
}

interface FacetResponse {
  cities: string[];
  categories: string[];
  combos: Array<{ city: string; category: string }>;
}

async function fetchFacets(): Promise<FacetResponse | null> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/public/vendors/facets`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return (await res.json()) as FacetResponse;
  } catch {
    return null;
  }
}

interface VendorSlugRow {
  slug: string;
}

async function fetchVendorSlugs(): Promise<string[]> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/public/vendors?page=1&page_size=100`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    const data = await res.json();
    return (data.vendors || [])
      .map((v: VendorSlugRow) => v.slug)
      .filter(Boolean);
  } catch {
    return [];
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date().toISOString();

  const staticPages: MetadataRoute.Sitemap = [
    { url: SITE_URL, lastModified: now, changeFrequency: 'daily', priority: 1.0 },
    { url: `${SITE_URL}/vendors`, lastModified: now, changeFrequency: 'daily', priority: 0.9 },
    { url: `${SITE_URL}/guides`, lastModified: now, changeFrequency: 'weekly', priority: 0.8 },
    { url: `${SITE_URL}/about`, lastModified: now, changeFrequency: 'monthly', priority: 0.5 },
    { url: `${SITE_URL}/how-it-works`, lastModified: now, changeFrequency: 'monthly', priority: 0.5 },
    { url: `${SITE_URL}/contact`, lastModified: now, changeFrequency: 'monthly', priority: 0.4 },
    { url: `${SITE_URL}/privacy`, lastModified: now, changeFrequency: 'monthly', priority: 0.3 },
    { url: `${SITE_URL}/terms`, lastModified: now, changeFrequency: 'monthly', priority: 0.3 },
  ];

  const [facets, vendorSlugs] = await Promise.all([fetchFacets(), fetchVendorSlugs()]);

  const vendorPages: MetadataRoute.Sitemap = vendorSlugs.map((slug) => ({
    url: `${SITE_URL}/vendors/${slug}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: 0.7,
  }));

  const geoPages: MetadataRoute.Sitemap = (facets?.combos || []).map((combo) => ({
    url: `${SITE_URL}/locations/${toSlug(combo.city)}/${toSlug(combo.category)}/vendors`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: 0.6,
  }));

  return [...staticPages, ...vendorPages, ...geoPages];
}
