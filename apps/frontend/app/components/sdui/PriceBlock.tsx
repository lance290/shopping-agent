'use client';

import type { PriceBlockData } from '../../sdui/types';

export function PriceBlock({ amount, currency, label }: PriceBlockData) {
  const formatted = amount !== null && amount !== undefined
    ? new Intl.NumberFormat('en-US', { style: 'currency', currency: currency || 'USD' }).format(amount)
    : null;

  return (
    <div className="flex items-baseline gap-2">
      {formatted ? (
        <span className="text-xl font-bold text-ink">{formatted}</span>
      ) : (
        <span className="text-lg font-semibold text-gold-dark">Request Quote</span>
      )}
      {label && label !== 'Total' && (
        <span className="text-sm text-ink-muted">{label}</span>
      )}
    </div>
  );
}
