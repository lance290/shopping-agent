'use client';

import type { PriceBlockData } from '../../sdui/types';

export function PriceBlock({ amount, currency, label }: PriceBlockData) {
  const formatted = amount !== null && amount !== undefined
    ? new Intl.NumberFormat('en-US', { style: 'currency', currency: currency || 'USD' }).format(amount)
    : null;

  return (
    <div className="flex items-baseline gap-2">
      {formatted ? (
        <span className="text-xl font-bold text-gray-900">{formatted}</span>
      ) : (
        <span className="text-lg font-semibold text-blue-600">Request Quote</span>
      )}
      {label && label !== 'Total' && (
        <span className="text-sm text-gray-500">{label}</span>
      )}
    </div>
  );
}
