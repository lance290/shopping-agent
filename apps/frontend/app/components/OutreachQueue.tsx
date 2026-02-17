'use client';

import { useState } from 'react';
import { Mail, Phone, MessageCircle, Check, Send, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';
import { Offer } from '../store';

interface VendorMatchPanelProps {
  rowId: number;
  desireTier: string;
  offers: Offer[];
}

const CHANNEL_ICON: Record<string, typeof Mail> = {
  email: Mail,
  phone: Phone,
  whatsapp: MessageCircle,
};

function matchReasonFromOffer(offer: Offer): string[] {
  const reasons: string[] = [];
  if (offer.vendor_name || offer.vendor_company) {
    reasons.push(`Specialist: ${offer.vendor_company || offer.vendor_name}`);
  }
  if (offer.match_score && offer.match_score > 0.7) {
    reasons.push('Strong match to your request');
  } else if (offer.match_score && offer.match_score > 0.4) {
    reasons.push('Potential match');
  }
  if (offer.is_service_provider) {
    reasons.push('Service provider in your area');
  }
  if (reasons.length === 0) {
    reasons.push('Found via vendor directory');
  }
  return reasons;
}

export default function OutreachQueue({ rowId, desireTier, offers }: VendorMatchPanelProps) {
  const [selectedVendors, setSelectedVendors] = useState<Set<number>>(new Set());
  const [expandedVendor, setExpandedVendor] = useState<number | null>(null);
  const [requestingQuotes, setRequestingQuotes] = useState(false);
  const [quotesRequested, setQuotesRequested] = useState<Set<number>>(new Set());

  // Only show vendor_directory results (the ones vetted by intention matching)
  const vendorOffers = offers.filter(o => o.source === 'vendor_directory');

  if (vendorOffers.length === 0) return null;

  const toggleSelect = (bidId: number) => {
    setSelectedVendors(prev => {
      const next = new Set(prev);
      if (next.has(bidId)) {
        next.delete(bidId);
      } else {
        next.add(bidId);
      }
      return next;
    });
  };

  const requestQuote = async (bidId: number) => {
    setQuotesRequested(prev => new Set(prev).add(bidId));
  };

  const requestSelectedQuotes = async () => {
    if (selectedVendors.size === 0) return;
    setRequestingQuotes(true);
    try {
      const res = await fetch('/api/outreach/campaigns', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ row_id: rowId }),
      });
      if (res.ok) {
        setQuotesRequested(new Set([...quotesRequested, ...selectedVendors]));
        setSelectedVendors(new Set());
      }
    } finally {
      setRequestingQuotes(false);
    }
  };

  const tierLabel = desireTier === 'service' ? 'Service Providers'
    : desireTier === 'bespoke' ? 'Specialists'
    : desireTier === 'high_value' ? 'Brokers & Specialists'
    : 'Matched Vendors';

  return (
    <div className="mt-3">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5" />
          {tierLabel} ({vendorOffers.length})
        </h4>
        {selectedVendors.size > 0 && (
          <button
            onClick={requestSelectedQuotes}
            disabled={requestingQuotes}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            <Send className="w-3 h-3" />
            Request {selectedVendors.size} Quote{selectedVendors.size !== 1 ? 's' : ''}
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {vendorOffers.map(offer => {
          const bidId = offer.bid_id || 0;
          const isSelected = selectedVendors.has(bidId);
          const isRequested = quotesRequested.has(bidId);
          const isExpanded = expandedVendor === bidId;
          const reasons = matchReasonFromOffer(offer);
          const ChannelIcon = CHANNEL_ICON[offer.vendor_email ? 'email' : 'phone'] || Mail;

          return (
            <div
              key={bidId}
              className={`relative border rounded-xl p-4 transition-all cursor-pointer ${
                isRequested
                  ? 'border-green-300 bg-green-50/50'
                  : isSelected
                  ? 'border-blue-400 bg-blue-50/50 ring-1 ring-blue-400'
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
              }`}
              onClick={() => !isRequested && toggleSelect(bidId)}
            >
              {/* Selection indicator */}
              <div className="absolute top-3 right-3">
                {isRequested ? (
                  <span className="flex items-center gap-1 text-xs text-green-600 font-medium">
                    <Check className="w-3.5 h-3.5" />
                    Requested
                  </span>
                ) : isSelected ? (
                  <div className="w-5 h-5 rounded-full bg-blue-600 flex items-center justify-center">
                    <Check className="w-3 h-3 text-white" />
                  </div>
                ) : (
                  <div className="w-5 h-5 rounded-full border-2 border-gray-300" />
                )}
              </div>

              {/* Vendor info */}
              <div className="pr-8">
                <h5 className="text-sm font-semibold text-gray-900 leading-tight">
                  {offer.vendor_company || offer.vendor_name || offer.merchant}
                </h5>
                {offer.title && offer.title !== offer.merchant && (
                  <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">{offer.title}</p>
                )}
              </div>

              {/* Match reasons */}
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                {reasons.map((reason, i) => (
                  <span key={i} className="inline-flex items-center text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                    {reason}
                  </span>
                ))}
              </div>

              {/* Request Quote button - centered in middle of card */}
              {!isRequested && (
                <div className="mt-4 flex items-center justify-center">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      requestQuote(bidId);
                    }}
                    className="flex items-center gap-1.5 px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm"
                  >
                    <Send className="w-3.5 h-3.5" />
                    Request Quote
                  </button>
                </div>
              )}

              {/* Contact info + expand */}
              <div className="mt-auto pt-3 flex items-center justify-between border-t border-gray-100">
                <div className="flex items-center gap-1.5 text-xs text-gray-400">
                  <ChannelIcon className="w-3.5 h-3.5" />
                  {offer.vendor_email || 'Contact available'}
                </div>
                {!isRequested && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setExpandedVendor(isExpanded ? null : bidId);
                    }}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                )}
              </div>

              {/* Expanded: additional details if needed */}
              {isExpanded && !isRequested && (
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <p className="text-xs text-gray-500">
                    Click Request Quote to send your requirements to {offer.vendor_company || offer.vendor_name || offer.merchant}.
                  </p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
