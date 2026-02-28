'use client';

import { useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { CheckCircle2, Link2, Pencil, ShoppingBag } from 'lucide-react';
import { Button } from '../../../components/ui/Button';

interface RowData {
  id: number;
  title: string;
  status: string;
  budget_max: number | null;
  currency: string;
}

export default function ListPage() {
  const params = useParams();
  const id = params.id as string;

  const [row, setRow] = useState<RowData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [savingTitle, setSavingTitle] = useState(false);
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
    fetchRow();
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
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      // Clipboard API unavailable — use execCommand fallback
      const textarea = document.createElement('textarea');
      textarea.value = url;
      textarea.style.cssText = 'position:fixed;opacity:0;pointer-events:none';
      document.body.appendChild(textarea);
      textarea.select();
      try {
        document.execCommand('copy');
      } finally {
        document.body.removeChild(textarea);
      }
    }
    setCopied(true);
    if (copyTimeoutRef.current) clearTimeout(copyTimeoutRef.current);
    copyTimeoutRef.current = setTimeout(() => setCopied(false), 2400);
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
              ) : (
                <>
                  <Link2 size={16} />
                  Share with Family
                </>
              )}
            </Button>
          </div>

          {row.budget_max != null && (
            <div className="text-sm text-gray-600 mb-4">
              Budget: up to ${Number(row.budget_max).toLocaleString()} {row.currency || 'USD'}
            </div>
          )}

          <div className="border-t border-gray-100 pt-4">
            <p className="text-sm text-gray-500">
              Share this list with family and friends so they can view and shop together.
            </p>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6 text-center">
          <h3 className="font-semibold text-gray-900 mb-2">Find the best deals</h3>
          <p className="text-sm text-gray-600 mb-4">
            BuyAnything helps you find the best prices across the internet.
          </p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
          >
            <ShoppingBag size={16} />
            Open My Board
          </Link>
        </div>
      </div>
    </div>
  );
}
