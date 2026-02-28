'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';

interface Transaction {
  id: number;
  type: string;
  amount_cents: number;
  description: string | null;
  created_at: string;
}

interface WalletData {
  balance_cents: number;
  transactions: Transaction[];
}

export default function PopWalletPage() {
  const [wallet, setWallet] = useState<WalletData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchWallet() {
      try {
        const res = await fetch('/api/pop/wallet');
        if (res.ok) {
          const data = await res.json();
          setWallet(data);
        }
      } catch {
        // Wallet not available
      } finally {
        setLoading(false);
      }
    }
    fetchWallet();
  }, []);

  const balance = wallet ? (wallet.balance_cents / 100).toFixed(2) : '0.00';

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <Image src="/pop-avatar.png" alt="Pop" width={32} height={32} className="rounded-full" />
            <span className="text-lg font-bold text-green-700">Pop</span>
          </Link>
          <Link
            href="/chat"
            className="text-sm text-gray-500 hover:text-green-700 transition-colors"
          >
            Chat
          </Link>
        </div>
      </nav>

      <div className="max-w-2xl mx-auto px-4 py-8">
        {/* Balance Card */}
        <div className="bg-gradient-to-br from-green-600 to-emerald-700 rounded-3xl p-8 text-white text-center mb-8 shadow-lg">
          <p className="text-sm opacity-80 mb-2">Your Pop Wallet</p>
          {loading ? (
            <div className="animate-pulse h-12 bg-white/20 rounded-xl w-32 mx-auto" />
          ) : (
            <h1 className="text-5xl font-bold">${balance}</h1>
          )}
          <p className="text-sm opacity-80 mt-3">Total savings earned</p>
          <div className="mt-6 flex gap-3 justify-center">
            <button
              disabled
              className="bg-white/20 text-white text-sm font-medium px-5 py-2.5 rounded-xl opacity-60 cursor-not-allowed"
              title="Coming soon"
            >
              Cash Out
            </button>
            <Link
              href="/chat"
              className="bg-white text-green-700 text-sm font-medium px-5 py-2.5 rounded-xl hover:bg-green-50 transition-colors"
            >
              Earn More
            </Link>
          </div>
        </div>

        {/* How to Earn */}
        <div className="bg-white rounded-2xl p-6 shadow-sm mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">How to earn</h2>
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <span className="text-2xl">💬</span>
              <div>
                <p className="text-sm font-medium text-gray-900">Tell Pop what you need</p>
                <p className="text-xs text-gray-500">Text or chat your grocery list</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-2xl">🔄</span>
              <div>
                <p className="text-sm font-medium text-gray-900">Claim a swap</p>
                <p className="text-xs text-gray-500">Pop finds brand deals — tap to claim before shopping</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-2xl">🧾</span>
              <div>
                <p className="text-sm font-medium text-gray-900">Snap your receipt</p>
                <p className="text-xs text-gray-500">Photo your receipt after shopping — Pop verifies automatically</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-2xl">💰</span>
              <div>
                <p className="text-sm font-medium text-gray-900">Get paid</p>
                <p className="text-xs text-gray-500">Savings go straight to your Pop Wallet</p>
              </div>
            </div>
          </div>
        </div>

        {/* Transactions */}
        <div className="bg-white rounded-2xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Activity</h2>
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="animate-pulse flex gap-3">
                  <div className="w-10 h-10 bg-gray-100 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <div className="h-3 bg-gray-100 rounded w-3/4" />
                    <div className="h-2 bg-gray-100 rounded w-1/2" />
                  </div>
                </div>
              ))}
            </div>
          ) : !wallet?.transactions?.length ? (
            <div className="text-center py-8">
              <span className="text-3xl block mb-3">🌱</span>
              <p className="text-sm text-gray-500">
                No activity yet. Start chatting with Pop to earn savings!
              </p>
            </div>
          ) : (
            <ul className="space-y-3">
              {wallet.transactions.map((tx) => (
                <li key={tx.id} className="flex items-center gap-3">
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center ${
                      tx.amount_cents > 0
                        ? 'bg-green-100 text-green-600'
                        : 'bg-gray-100 text-gray-500'
                    }`}
                  >
                    {tx.amount_cents > 0 ? '+' : '-'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-900 truncate">
                      {tx.description || tx.type}
                    </p>
                    <p className="text-xs text-gray-400">
                      {new Date(tx.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <span
                    className={`text-sm font-semibold ${
                      tx.amount_cents > 0 ? 'text-green-600' : 'text-gray-500'
                    }`}
                  >
                    {tx.amount_cents > 0 ? '+' : ''}${(tx.amount_cents / 100).toFixed(2)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
