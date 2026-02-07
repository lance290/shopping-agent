'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Share2, ExternalLink, ShoppingBag, Package, DollarSign } from 'lucide-react';

interface ShareContent {
  resource_type: string;
  resource_id: number;
  resource_data: Record<string, unknown>;
  created_by: number;
  access_count: number;
}

export default function SharePage() {
  const params = useParams();
  const token = params.token as string;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [content, setContent] = useState<ShareContent | null>(null);

  useEffect(() => {
    // Viral Flywheel (PRD 06): store share token for referral attribution on signup
    if (token && typeof window !== 'undefined') {
      localStorage.setItem('referral_token', token);
    }

    async function resolveShare() {
      try {
        const res = await fetch(`/api/shares/${token}`);
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || 'Share link not found or expired');
        }
        const data: ShareContent = await res.json();
        setContent(data);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Failed to load shared content';
        setError(message);
      } finally {
        setLoading(false);
      }
    }
    resolveShare();
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (error || !content) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
          <Share2 className="mx-auto text-gray-400 mb-4" size={48} />
          <h1 className="text-xl font-bold text-gray-900 mb-2">Link Not Found</h1>
          <p className="text-gray-600 mb-6">{error || 'This share link is no longer available.'}</p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700 transition-colors"
          >
            <ShoppingBag size={16} />
            Start Shopping
          </Link>
        </div>
      </div>
    );
  }

  const { resource_type, resource_data, access_count } = content;

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="bg-blue-100 p-2 rounded-lg">
                <Share2 className="text-blue-600" size={20} />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Shared Content</h1>
                <p className="text-sm text-gray-500">
                  {resource_type === 'tile' || resource_type === 'bid'
                    ? 'Shared Offer'
                    : resource_type === 'row'
                    ? 'Shared Request'
                    : 'Shared Project'}
                </p>
              </div>
            </div>
            <div className="text-xs text-gray-400">
              {access_count} view{access_count !== 1 ? 's' : ''}
            </div>
          </div>

          {/* Tile/Bid Content */}
          {(resource_type === 'tile' || resource_type === 'bid') && (
            <div className="border border-gray-200 rounded-lg p-4">
              <h2 className="font-semibold text-gray-900 mb-2">
                {(resource_data.item_title as string) || 'Untitled Offer'}
              </h2>
              {resource_data.price != null && (
                <div className="flex items-center gap-1 text-lg font-bold text-emerald-700 mb-2">
                  <DollarSign size={18} />
                  {Number(resource_data.price).toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                  <span className="text-sm font-normal text-gray-500 ml-1">
                    {(resource_data.currency as string) || 'USD'}
                  </span>
                </div>
              )}
              {!!resource_data.condition && (
                <div className="text-sm text-gray-600 mb-2">
                  Condition: {String(resource_data.condition)}
                </div>
              )}
              {!!resource_data.item_url && (
                <a
                  href={resource_data.item_url as string}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-blue-600 text-sm hover:underline"
                >
                  <ExternalLink size={14} />
                  View Original
                </a>
              )}
            </div>
          )}

          {/* Row Content */}
          {resource_type === 'row' && (
            <div className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Package className="text-gray-400" size={16} />
                <h2 className="font-semibold text-gray-900">
                  {(resource_data.title as string) || 'Untitled Request'}
                </h2>
              </div>
              {!!resource_data.status && (
                <div className="text-sm text-gray-600 mb-1">
                  Status: <span className="font-medium">{String(resource_data.status)}</span>
                </div>
              )}
              {resource_data.budget_max != null && (
                <div className="text-sm text-gray-600">
                  Budget: up to ${Number(resource_data.budget_max).toLocaleString()}
                </div>
              )}
            </div>
          )}

          {/* Project Content */}
          {resource_type === 'project' && (
            <div className="border border-gray-200 rounded-lg p-4">
              <h2 className="font-semibold text-gray-900 mb-2">
                {(resource_data.title as string) || 'Untitled Project'}
              </h2>
              {!!resource_data.created_at && (
                <div className="text-sm text-gray-500">
                  Created: {new Date(String(resource_data.created_at)).toLocaleDateString()}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Affiliate Disclosure (PRD 08) */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-6 text-xs text-amber-800">
          <strong>Disclosure:</strong> Some links on this page may be affiliate links. BuyAnything.ai may earn a commission from qualifying purchases at no extra cost to you.{' '}
          <Link href="/disclosure" className="underline hover:text-amber-900">Learn more</Link>
        </div>

        {/* CTA */}
        <div className="bg-white rounded-lg shadow-lg p-6 text-center">
          <h3 className="font-semibold text-gray-900 mb-2">Want to find deals like this?</h3>
          <p className="text-sm text-gray-600 mb-4">
            BuyAnything helps you find the best deals across the internet.
          </p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
          >
            <ShoppingBag size={16} />
            Start Shopping
          </Link>
        </div>
      </div>
    </div>
  );
}
