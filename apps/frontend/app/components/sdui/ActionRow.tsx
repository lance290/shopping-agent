'use client';

import { useState } from 'react';
import type { ActionRowBlock, ActionObject } from '../../sdui/types';
import { useShoppingStore } from '../../store';
import { fetchSingleRowFromDb, fundDealEscrowInDb, transitionDealInDb } from '../../utils/api';

function ActionButton({ action }: { action: ActionObject }) {
  const baseClasses = 'inline-flex items-center px-3 py-1.5 rounded-lg text-sm font-medium transition-colors';
  const rows = useShoppingStore((s) => s.rows);
  const updateRow = useShoppingStore((s) => s.updateRow);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const rowId = action.row_id ? Number(action.row_id) : null;
  const dealId = action.deal_id ? Number(action.deal_id) : null;
  const row = rowId ? rows.find((candidate) => candidate.id === rowId) : undefined;

  async function refreshRow() {
    if (!rowId) return;
    const updatedRow = await fetchSingleRowFromDb(rowId);
    if (updatedRow) {
      updateRow(rowId, updatedRow);
    }
  }

  async function handleDealAction(nextStatus: 'terms_agreed' | 'negotiating') {
    if (!dealId) return;

    const payload: {
      new_status: 'terms_agreed' | 'negotiating';
      vendor_quoted_price?: number;
      agreed_terms_summary?: string;
    } = { new_status: nextStatus };

    if (nextStatus === 'terms_agreed') {
      const existingPrice = row?.active_deal?.vendor_quoted_price;
      const priceInput = window.prompt('Agreed vendor price', existingPrice != null ? String(existingPrice) : '');
      if (priceInput === null) return;
      const trimmedPrice = priceInput.trim();
      if (trimmedPrice.length > 0) {
        const parsedPrice = Number(trimmedPrice);
        if (!Number.isFinite(parsedPrice) || parsedPrice <= 0) {
          window.alert('Enter a valid agreed price.');
          return;
        }
        payload.vendor_quoted_price = parsedPrice;
      }

      const existingSummary = row?.active_deal?.agreed_terms_summary ?? '';
      const summaryInput = window.prompt('Agreed terms summary', existingSummary);
      if (summaryInput === null) return;
      const trimmedSummary = summaryInput.trim();
      if (trimmedSummary.length > 0) {
        payload.agreed_terms_summary = trimmedSummary;
      }
    } else if (!window.confirm('Move this deal back to negotiation?')) {
      return;
    }

    setIsSubmitting(true);
    const ok = await transitionDealInDb(dealId, payload);
    setIsSubmitting(false);
    if (!ok) {
      window.alert('Unable to update the deal right now.');
      return;
    }
    await refreshRow();
  }

  async function handleFundEscrow() {
    if (!dealId) return;
    setIsSubmitting(true);
    const result = await fundDealEscrowInDb(dealId);
    setIsSubmitting(false);
    if (!result?.checkout_url) {
      window.alert('Unable to start checkout right now.');
      return;
    }
    window.location.assign(result.checkout_url);
  }

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
        <button
          type="button"
          disabled={isSubmitting || !dealId}
          onClick={() => {
            void handleFundEscrow();
          }}
          className={`${baseClasses} bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-60`}
        >
          {action.label}
          {action.amount != null && (
            <span className="ml-1 opacity-80">
              ({action.currency || 'USD'} {action.amount.toLocaleString()})
            </span>
          )}
        </button>
      );

    case 'mark_terms_agreed':
      return (
        <button
          type="button"
          disabled={isSubmitting || !dealId}
          onClick={() => {
            void handleDealAction('terms_agreed');
          }}
          className={`${baseClasses} bg-status-success text-white hover:bg-status-success/90 disabled:opacity-60`}
        >
          {action.label}
        </button>
      );

    case 'continue_negotiation':
      return (
        <button
          type="button"
          disabled={isSubmitting || !dealId}
          onClick={() => {
            void handleDealAction('negotiating');
          }}
          className={`${baseClasses} bg-slate-700 text-white hover:bg-slate-800 disabled:opacity-60`}
        >
          {action.label}
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
