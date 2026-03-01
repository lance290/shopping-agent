'use client';

import { useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { AlertCircle, CheckCircle2, Link2, LogIn, Pencil, ShoppingBag } from 'lucide-react';
import { Button } from '../../../components/ui/Button';
import { getMe } from '../../utils/auth';

interface BidItem {
  id: number;
  item_title: string;
  price: number | null;
  currency: string;
  image_url: string | null;
  item_url: string | null;
}

interface RowData {
  id: number;
  title: string;
  status: string;
  budget_max: number | null;
  currency: string;
  bids?: BidItem[];
}

export default function ListPage() {
  const params = useParams();
  const id = params.id as string;

  const [row, setRow] = useState<RowData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [copyFailed, setCopyFailed] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [savingTitle, setSavingTitle] = useState(false);
  const [checkedItems, setCheckedItems] = useState<Set<number>>(new Set());
  const [isDoneShopping, setIsDoneShopping] = useState(false);
  const titleInputRef = useRef<HTMLInputElement | null>(null);
  const copyTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (copyTimeoutRef.current) clearTimeout(copyTimeoutRef.current);
    };
  }, []);

  useEffect(() => {
    async function fetchRow() {
      try {
        const res = await fetch(`/api/rows?id=${id}`);
        if (!res.ok) {
          throw new Error('List not found');
        }
        const data: RowData = await res.json();
        setRow(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load list');
      } finally {
        setLoading(false);
      }
    }
    async function checkAuth() {
      const me = await getMe();
      setIsAuthenticated(!!me?.authenticated);
    }
    fetchRow();
    checkAuth();
  }, [id]);

  const handleStartEditTitle = () => {
    if (!row) return;
    setEditTitle(row.title);
    setIsEditingTitle(true);
    setTimeout(() => titleInputRef.current?.select(), 0);
  };

  const handleSaveTitle = async () => {
    if (!row) return;
    const trimmed = editTitle.trim();
    if (!trimmed || trimmed === row.title) {
      setIsEditingTitle(false);
      return;
    }
    setSavingTitle(true);
    try {
      const res = await fetch(`/api/rows?id=${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: trimmed }),
      });
      if (res.ok) {
        setRow({ ...row, title: trimmed });
      }
    } finally {
      setSavingTitle(false);
      setIsEditingTitle(false);
    }
  };

  const handleTitleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSaveTitle();
    if (e.key === 'Escape') setIsEditingTitle(false);
  };

  const handleShareWithFamily = async () => {
    const url = window.location.href;
    let success = false;

    try {
      await navigator.clipboard.writeText(url);
      success = true;
    } catch (err) {
      // AbortError: user dismissed the clipboard permission prompt — do not fall through
      if (err instanceof DOMException && err.name === 'AbortError') return;

      // Clipboard API unavailable — try execCommand fallback
      if (typeof document.execCommand === 'function') {
        const textarea = document.createElement('textarea');
        textarea.value = url;
        textarea.style.cssText = 'position:fixed;opacity:0;pointer-events:none';
        document.body.appendChild(textarea);
        textarea.select();
        try {
          success = document.execCommand('copy');
        } finally {
          document.body.removeChild(textarea);
        }
      }
    }

    if (success) {
      setCopied(true);
      setCopyFailed(false);
      if (copyTimeoutRef.current) clearTimeout(copyTimeoutRef.current);
      copyTimeoutRef.current = setTimeout(() => setCopied(false), 2400);
    } else {
      setCopyFailed(true);
      if (copyTimeoutRef.current) clearTimeout(copyTimeoutRef.current);
      copyTimeoutRef.current = setTimeout(() => setCopyFailed(false), 2400);
    }
  };

  const handleToggleItem = (bidId: number) => {
    setCheckedItems((prev) => {
      const next = new Set(prev);
      if (next.has(bidId)) {
        next.delete(bidId);
      } else {
        next.add(bidId);
      }
      return next;
    });
  };

  const handleDoneShopping = () => {
    // Mark session as done — items remain visible so the shopper can review what they got.
    setIsDoneShopping(true);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (error || !row) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
          <ShoppingBag className="mx-auto text-gray-400 mb-4" size={48} />
          <h1 className="text-xl font-bold text-gray-900 mb-2">List Not Found</h1>
          <p className="text-gray-600 mb-6">{error || 'This list is no longer available.'}</p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700 transition-colors"
          >
            <ShoppingBag size={16} />
            Start Shopping
          </Link>
        </div>
      </div>
    );
  }

  const bids = row.bids ?? [];

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <div className="flex items-start justify-between gap-4 mb-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">
                Shopping List
              </p>
              {isEditingTitle ? (
                <input
                  ref={titleInputRef}
                  data-testid="title-edit-input"
                  type="text"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  onBlur={handleSaveTitle}
                  onKeyDown={handleTitleKeyDown}
                  disabled={savingTitle}
                  className="text-2xl font-bold text-gray-900 border-b-2 border-blue-500 outline-none bg-transparent w-full"
                  autoFocus
                />
              ) : (
                <button
                  data-testid="title-edit-btn"
                  onClick={handleStartEditTitle}
                  className="group flex items-center gap-2 text-left"
                >
                  <h1 className="text-2xl font-bold text-gray-900">{row.title}</h1>
                  <Pencil size={16} className="text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                </button>
              )}
              {row.status && row.status !== 'new' && (
                <p className="text-sm text-gray-500 mt-1 capitalize">{row.status}</p>
              )}
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleShareWithFamily}
              className="shrink-0 flex items-center gap-2"
              data-testid="share-with-family-btn"
            >
              {copied ? (
                <>
                  <CheckCircle2 size={16} className="text-green-600" />
                  <span className="text-green-600">Copied!</span>
                </>
              ) : copyFailed ? (
                <>
                  <AlertCircle size={16} className="text-red-500" />
                  <span className="text-red-500">Copy failed</span>
                </>
              ) : (
                <>
                  <Link2 size={16} />
                  Copy Link
                </>
              )}
            </Button>
          </div>

          {row.budget_max != null && (
            <div className="text-sm text-gray-600 mb-4">
              Budget: up to ${Number(row.budget_max).toLocaleString()} {row.currency || 'USD'}
            </div>
          )}

          {/* Shopping items checklist */}
          {bids.length > 0 && (
            <div className="border-t border-gray-100 pt-4">
              {isDoneShopping && (
                <div
                  data-testid="done-shopping-banner"
                  className="flex items-center gap-2 mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm font-medium"
                >
                  <CheckCircle2 size={16} className="shrink-0" />
                  Happy shopping! Here&apos;s everything on the list.
                </div>
              )}
              <ul data-testid="items-list" className="space-y-2 mb-4">
                {bids.map((bid) => {
                  const isChecked = checkedItems.has(bid.id);
                  return (
                    <li key={bid.id}>
                      <label
                        data-testid={`item-${bid.id}`}
                        className="flex items-center gap-3 p-3 rounded-lg border border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors"
                      >
                        <input
                          type="checkbox"
                          data-testid={`item-checkbox-${bid.id}`}
                          checked={isChecked}
                          onChange={() => handleToggleItem(bid.id)}
                          className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                        />
                        <span className={`flex-1 text-sm font-medium ${isChecked ? 'line-through text-gray-400' : 'text-gray-800'}`}>
                          {bid.item_title}
                        </span>
                        {bid.price != null && (
                          <span className="text-sm text-gray-500 shrink-0">
                            ${Number(bid.price).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </span>
                        )}
                      </label>
                    </li>
                  );
                })}
              </ul>
              {!isDoneShopping && (
                <Button
                  data-testid="done-shopping-btn"
                  variant="primary"
                  size="md"
                  onClick={handleDoneShopping}
                  className="w-full"
                >
                  Done Shopping
                </Button>
              )}
            </div>
          )}

          {bids.length === 0 && (
            <div className="border-t border-gray-100 pt-4">
              <p className="text-sm text-gray-500">
                Share this list with family and friends so they can view and shop together.
              </p>
            </div>
          )}
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6 text-center">
          <h3 className="font-semibold text-gray-900 mb-2">Find the best deals</h3>
          <p className="text-sm text-gray-600 mb-4">
            BuyAnything helps you find the best prices across the internet.
          </p>
          {isAuthenticated ? (
            <Link
              href="/"
              className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
            >
              <ShoppingBag size={16} />
              Open My Board
            </Link>
          ) : (
            <Link
              href="/login"
              data-testid="login-btn"
              className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
            >
              <LogIn size={16} />
              Sign In
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
