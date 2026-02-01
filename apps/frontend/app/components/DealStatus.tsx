'use client';

import { Mail, CheckCircle2, Handshake } from 'lucide-react';

interface DealStatusProps {
  status: 'introduced' | 'closed' | null;
  sellerCompany?: string;
  dealValue?: number;
}

export function DealStatus({ status, sellerCompany, dealValue }: DealStatusProps) {
  if (!status) return null;

  if (status === 'introduced') {
    return (
      <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-4">
        <div className="flex items-center gap-3">
          <div className="bg-purple-100 p-2 rounded-full">
            <Mail className="text-purple-600" size={20} />
          </div>
          <div>
            <div className="font-semibold text-purple-900">Deal in Progress</div>
            <div className="text-sm text-purple-700">
              You've been introduced to {sellerCompany || 'the vendor'} via email.
              {dealValue && (
                <span className="font-medium"> (${dealValue.toLocaleString()})</span>
              )}
            </div>
          </div>
        </div>
        <div className="mt-3 text-xs text-purple-600">
          Check your email for contact details. Communicate directly to finalize the deal.
        </div>
      </div>
    );
  }

  if (status === 'closed') {
    return (
      <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 mb-4">
        <div className="flex items-center gap-3">
          <div className="bg-emerald-100 p-2 rounded-full">
            <Handshake className="text-emerald-600" size={20} />
          </div>
          <div>
            <div className="font-semibold text-emerald-900">Deal Closed!</div>
            <div className="text-sm text-emerald-700">
              Successfully completed with {sellerCompany || 'vendor'}.
              {dealValue && (
                <span className="font-medium"> (${dealValue.toLocaleString()})</span>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
