'use client';

import type { EscrowStatusBlock } from '../../sdui/types';

export function EscrowStatus({ deal_id }: EscrowStatusBlock) {
  return (
    <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center flex-shrink-0">
          <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
        </div>
        <div>
          <p className="text-sm font-semibold text-purple-800">Funds in Escrow</p>
          <p className="text-xs text-purple-600">Protected until delivery is confirmed</p>
        </div>
      </div>
      {deal_id && (
        <p className="text-xs text-purple-400 mt-2">Deal #{deal_id}</p>
      )}
    </div>
  );
}
