'use client';

import type { ActionRowBlock, ActionObject } from '../../sdui/types';

function ActionButton({ action }: { action: ActionObject }) {
  const baseClasses = 'inline-flex items-center px-3 py-1.5 rounded-lg text-sm font-medium transition-colors';

  switch (action.intent) {
    case 'outbound_affiliate':
      return (
        <a
          href={`/api/out?bid_id=${action.bid_id || ''}&url=${encodeURIComponent(action.url || '')}`}
          target="_blank"
          rel="noopener noreferrer"
          className={`${baseClasses} bg-gold text-navy hover:bg-gold-dark`}
        >
          {action.label}
        </a>
      );

    case 'contact_vendor':
      return (
        <button className={`${baseClasses} bg-status-success text-white hover:bg-status-success/90`}>
          {action.label}
        </button>
      );

    case 'claim_swap':
      return (
        <button className={`${baseClasses} bg-emerald-500 text-white hover:bg-emerald-600`}>
          {action.label}
        </button>
      );

    case 'fund_escrow':
      return (
        <button className={`${baseClasses} bg-purple-600 text-white hover:bg-purple-700`}>
          {action.label}
          {action.amount != null && (
            <span className="ml-1 opacity-80">
              (${action.amount.toLocaleString()})
            </span>
          )}
        </button>
      );

    case 'send_tip':
      return (
        <button className={`${baseClasses} bg-amber-500 text-white hover:bg-amber-600`}>
          {action.label}
          {action.amount != null && (
            <span className="ml-1 opacity-80">${action.amount}</span>
          )}
        </button>
      );

    case 'view_all_bids':
      return (
        <button className={`${baseClasses} bg-canvas-dark text-ink hover:bg-warm-grey`}>
          {action.label}
        </button>
      );

    case 'view_raw':
    case 'edit_request':
    default:
      return (
        <button className={`${baseClasses} bg-canvas-dark text-ink hover:bg-warm-grey`}>
          {action.label}
        </button>
      );
  }
}

export function ActionRow({ actions }: ActionRowBlock) {
  if (!actions || actions.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 pt-1">
      {actions.slice(0, 3).map((action, i) => (
        <ActionButton key={i} action={action} />
      ))}
    </div>
  );
}
