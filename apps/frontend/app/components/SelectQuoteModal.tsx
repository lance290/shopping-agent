'use client';

import { useState } from 'react';
import { X, Mail, Phone, Building2, DollarSign } from 'lucide-react';

interface QuoteInfo {
  quote_id: number;
  seller_company: string;
  seller_name?: string;
  price: number;
  description?: string;
}

interface SelectQuoteModalProps {
  isOpen: boolean;
  onClose: () => void;
  quote: QuoteInfo | null;
  onConfirm: (buyerInfo: { name?: string; phone?: string }) => Promise<void>;
}

export function SelectQuoteModal({
  isOpen,
  onClose,
  quote,
  onConfirm,
}: SelectQuoteModalProps) {
  const [buyerName, setBuyerName] = useState('');
  const [buyerPhone, setBuyerPhone] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !quote) return null;

  async function handleConfirm() {
    setSubmitting(true);
    setError(null);
    try {
      await onConfirm({ name: buyerName || undefined, phone: buyerPhone || undefined });
      onClose();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to select quote';
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-xl shadow-2xl max-w-md w-full p-6 z-10">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-onyx-muted hover:text-ink"
        >
          <X size={20} />
        </button>

        {/* Header */}
        <div className="mb-6">
          <h2 className="text-xl font-bold text-ink">Select This Quote?</h2>
          <p className="text-sm text-ink-muted mt-1">
            This will introduce you to the vendor via email.
          </p>
        </div>

        {/* Quote Summary */}
        <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 mb-6">
          <div className="flex items-start gap-3">
            <div className="bg-emerald-100 p-2 rounded-lg">
              <Building2 className="text-emerald-600" size={20} />
            </div>
            <div className="flex-1">
              <div className="font-semibold text-ink">{quote.seller_company}</div>
              {quote.seller_name && (
                <div className="text-sm text-ink-muted">{quote.seller_name}</div>
              )}
              <div className="flex items-center gap-1 mt-2 text-lg font-bold text-emerald-700">
                <DollarSign size={18} />
                {quote.price.toLocaleString()}
              </div>
              {quote.description && (
                <p className="text-sm text-ink-muted mt-2 line-clamp-2">
                  {quote.description}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Your Contact Info */}
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-ink mb-3">
            Your Contact Info (Optional)
          </h3>
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-ink-muted mb-1">Your Name</label>
              <input
                type="text"
                value={buyerName}
                onChange={(e) => setBuyerName(e.target.value)}
                className="w-full px-3 py-2 border border-warm-grey rounded-lg text-sm focus:ring-2 focus:ring-gold focus:border-gold"
                placeholder="Enter your name"
              />
            </div>
            <div>
              <label className="block text-xs text-ink-muted mb-1">Your Phone</label>
              <input
                type="tel"
                value={buyerPhone}
                onChange={(e) => setBuyerPhone(e.target.value)}
                className="w-full px-3 py-2 border border-warm-grey rounded-lg text-sm focus:ring-2 focus:ring-gold focus:border-gold"
                placeholder="(555) 123-4567"
              />
            </div>
          </div>
        </div>

        {/* What happens next */}
        <div className="bg-canvas-dark rounded-lg p-4 mb-6">
          <h4 className="text-sm font-semibold text-ink mb-2">What happens next?</h4>
          <ul className="text-sm text-ink-muted space-y-1">
            <li className="flex items-center gap-2">
              <Mail size={14} className="text-onyx-muted" />
              You&apos;ll receive the vendor&apos;s contact info
            </li>
            <li className="flex items-center gap-2">
              <Mail size={14} className="text-onyx-muted" />
              The vendor will receive your contact info
            </li>
            <li className="flex items-center gap-2">
              <Phone size={14} className="text-onyx-muted" />
              You can communicate directly to finalize
            </li>
          </ul>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-lg mb-4 text-sm">
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={onClose}
            disabled={submitting}
            className="flex-1 px-4 py-2 border border-warm-grey rounded-lg text-ink font-medium hover:bg-canvas-dark disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={submitting}
            className="flex-1 px-4 py-2 bg-emerald-600 text-white rounded-lg font-medium hover:bg-emerald-700 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {submitting ? (
              <>
                <span className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></span>
                Sending...
              </>
            ) : (
              <>
                <Mail size={16} />
                Select & Introduce
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
