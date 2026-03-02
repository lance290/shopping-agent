'use client';

import type { ReceiptUploaderBlock } from '../../sdui/types';

export function ReceiptUploader({ campaign_id }: ReceiptUploaderBlock) {
  return (
    <div className="border-2 border-dashed border-emerald-300 rounded-lg p-4 bg-emerald-50 text-center">
      <div className="text-emerald-600 mb-2">
        <svg className="w-8 h-8 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
        </svg>
      </div>
      <p className="text-sm font-medium text-emerald-700">Upload your receipt</p>
      <p className="text-xs text-emerald-600 mt-1">Take a photo of your receipt to claim your savings</p>
      <button className="mt-3 inline-flex items-center px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-700 transition-colors">
        Choose Photo
      </button>
      {campaign_id && (
        <input type="hidden" name="campaign_id" value={campaign_id} />
      )}
    </div>
  );
}
