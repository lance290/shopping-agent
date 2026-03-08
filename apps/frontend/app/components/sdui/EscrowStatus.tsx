'use client';

export function QuoteAccepted({ deal_id }: { deal_id: string }) {
  return (
    <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 flex items-center gap-3">
      <div className="bg-purple-100 p-2 rounded-full">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-purple-600">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
          <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
        </svg>
      </div>
      <div>
        <p className="text-sm font-semibold text-purple-800">Quote Accepted</p>
        <p className="text-xs text-purple-600">Pending final invoice payment with vendor</p>
      </div>
      {deal_id && (
        <p className="text-xs text-purple-400 mt-2">Deal #{deal_id}</p>
      )}
    </div>
  );
}
