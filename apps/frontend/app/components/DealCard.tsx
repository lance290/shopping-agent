'use client';

import { useState } from 'react';
import {
  Shield,
  CreditCard,
  CheckCircle2,
  MessageSquare,
  Clock,
  ArrowRight,
  Loader2,
  AlertTriangle,
  Truck,
} from 'lucide-react';

interface DealCardProps {
  deal: {
    id: number;
    row_id: number;
    status: string;
    proxy_email: string;
    vendor_quoted_price: number | null;
    platform_fee_pct: number;
    platform_fee_amount: number | null;
    buyer_total: number | null;
    currency: string;
    agreed_terms_summary: string | null;
    created_at: string;
    terms_agreed_at: string | null;
    funded_at: string | null;
    completed_at: string | null;
  };
  vendor?: {
    id: number;
    name: string;
    email: string | null;
    domain: string | null;
  } | null;
  messages?: Array<{
    id: number;
    sender_type: string;
    content_text: string;
    ai_classification: string | null;
    created_at: string;
  }>;
  onFundEscrow?: (dealId: number) => void;
  onConfirmDelivery?: (dealId: number) => void;
}

const STATUS_CONFIG: Record<string, {
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
  icon: typeof Shield;
}> = {
  negotiating: {
    label: 'Negotiating',
    color: 'text-blue-700',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    icon: MessageSquare,
  },
  terms_agreed: {
    label: 'Terms Agreed',
    color: 'text-amber-700',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    icon: CheckCircle2,
  },
  funded: {
    label: 'Funds Secured',
    color: 'text-emerald-700',
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
    icon: Shield,
  },
  in_transit: {
    label: 'In Transit',
    color: 'text-purple-700',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
    icon: Truck,
  },
  completed: {
    label: 'Completed',
    color: 'text-emerald-700',
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
    icon: CheckCircle2,
  },
  disputed: {
    label: 'Disputed',
    color: 'text-red-700',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    icon: AlertTriangle,
  },
  canceled: {
    label: 'Canceled',
    color: 'text-gray-500',
    bgColor: 'bg-gray-50',
    borderColor: 'border-gray-200',
    icon: AlertTriangle,
  },
};

function formatCurrency(amount: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount);
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export function DealCard({
  deal,
  vendor,
  messages,
  onFundEscrow,
  onConfirmDelivery,
}: DealCardProps) {
  const [loading, setLoading] = useState(false);

  const config = STATUS_CONFIG[deal.status] || STATUS_CONFIG.negotiating;
  const StatusIcon = config.icon;

  const handleFundEscrow = async () => {
    if (!onFundEscrow) return;
    setLoading(true);
    try {
      await onFundEscrow(deal.id);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmDelivery = async () => {
    if (!onConfirmDelivery) return;
    setLoading(true);
    try {
      await onConfirmDelivery(deal.id);
    } finally {
      setLoading(false);
    }
  };

  const recentMessages = messages?.slice(-3) || [];

  return (
    <div className={`rounded-xl border-2 ${config.borderColor} ${config.bgColor} overflow-hidden`}>
      {/* Header */}
      <div className="px-5 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${config.bgColor}`}>
            <StatusIcon className={config.color} size={22} />
          </div>
          <div>
            <div className={`font-semibold ${config.color}`}>{config.label}</div>
            {vendor && (
              <div className="text-sm text-gray-600">
                with <span className="font-medium">{vendor.name}</span>
              </div>
            )}
          </div>
        </div>
        <div className="text-xs text-gray-400">
          Deal #{deal.id}
        </div>
      </div>

      {/* Price breakdown — shown when terms are agreed or later */}
      {deal.vendor_quoted_price != null && deal.status !== 'negotiating' && (
        <div className="mx-5 mb-4 bg-white rounded-lg border border-gray-100 p-4">
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Vendor quote</span>
              <span className="font-medium">
                {formatCurrency(deal.vendor_quoted_price, deal.currency)}
              </span>
            </div>
            {deal.platform_fee_amount != null && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">
                  Service fee ({(deal.platform_fee_pct * 100).toFixed(0)}%)
                </span>
                <span className="text-gray-500">
                  {formatCurrency(deal.platform_fee_amount, deal.currency)}
                </span>
              </div>
            )}
            {deal.buyer_total != null && (
              <>
                <hr className="border-gray-100" />
                <div className="flex justify-between text-base font-semibold">
                  <span>Your total</span>
                  <span className="text-emerald-700">
                    {formatCurrency(deal.buyer_total, deal.currency)}
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Terms summary */}
      {deal.agreed_terms_summary && (
        <div className="mx-5 mb-4 text-sm text-gray-700 bg-white rounded-lg border border-gray-100 p-3">
          <div className="font-medium text-gray-900 mb-1">Agreed Terms</div>
          {deal.agreed_terms_summary}
        </div>
      )}

      {/* Recent messages preview */}
      {recentMessages.length > 0 && (
        <div className="mx-5 mb-4 space-y-2">
          <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Recent Messages
          </div>
          {recentMessages.map((msg) => (
            <div
              key={msg.id}
              className={`text-sm p-2 rounded-lg ${
                msg.sender_type === 'buyer'
                  ? 'bg-blue-50 text-blue-900 ml-4'
                  : msg.sender_type === 'vendor'
                  ? 'bg-white text-gray-900 mr-4 border border-gray-100'
                  : 'bg-gray-50 text-gray-500 text-xs italic'
              }`}
            >
              <div className="flex justify-between items-center mb-0.5">
                <span className="text-xs font-medium capitalize opacity-60">
                  {msg.sender_type}
                </span>
                <span className="text-xs opacity-40">
                  {formatDate(msg.created_at)}
                </span>
              </div>
              <div className="line-clamp-2">{msg.content_text}</div>
              {msg.ai_classification === 'terms_agreed' && (
                <div className="mt-1 text-xs text-amber-600 font-medium flex items-center gap-1">
                  <CheckCircle2 size={12} />
                  AI detected agreement
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="px-5 pb-4">
        {/* Fund escrow CTA — only when terms are agreed */}
        {deal.status === 'terms_agreed' && onFundEscrow && (
          <button
            onClick={handleFundEscrow}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="animate-spin" size={18} />
            ) : (
              <>
                <CreditCard size={18} />
                Secure Funds via Escrow
                <ArrowRight size={16} />
              </>
            )}
          </button>
        )}

        {/* Confirm delivery — only when funded */}
        {deal.status === 'funded' && onConfirmDelivery && (
          <button
            onClick={handleConfirmDelivery}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="animate-spin" size={18} />
            ) : (
              <>
                <CheckCircle2 size={18} />
                Confirm Delivery
              </>
            )}
          </button>
        )}

        {/* Negotiating hint */}
        {deal.status === 'negotiating' && (
          <div className="flex items-center gap-2 text-sm text-blue-600 bg-blue-50 rounded-lg p-3">
            <Clock size={16} />
            <span>
              Reply to <span className="font-mono text-xs bg-blue-100 px-1.5 py-0.5 rounded">{deal.proxy_email}</span> to continue negotiating.
            </span>
          </div>
        )}

        {/* Completed */}
        {deal.status === 'completed' && (
          <div className="flex items-center gap-2 text-sm text-emerald-600 bg-emerald-50 rounded-lg p-3">
            <CheckCircle2 size={16} />
            <span>
              Deal completed{deal.completed_at ? ` on ${formatDate(deal.completed_at)}` : ''}.
              Vendor payout has been initiated.
            </span>
          </div>
        )}

        {/* Escrow trust badge */}
        {['terms_agreed', 'funded', 'in_transit'].includes(deal.status) && (
          <div className="mt-3 flex items-center gap-2 text-xs text-gray-400">
            <Shield size={14} />
            <span>Funds protected by BuyAnything escrow. Vendor is paid only after you confirm delivery.</span>
          </div>
        )}
      </div>
    </div>
  );
}
