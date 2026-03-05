'use client';

import { Bot, LogIn, LogOut, Store } from 'lucide-react';
import type { Row } from '../store';

interface ChatHeaderProps {
  activeRow: Row | undefined;
  userEmail: string | null;
  userPhone: string | null;
  onLogout: () => void;
}

export default function ChatHeader({ activeRow, userEmail, userPhone, onLogout }: ChatHeaderProps) {
  const isLoggedIn = !!(userEmail || userPhone);

  return (
    <div className="h-14 px-4 sm:px-6 border-b border-warm-grey bg-navy text-white flex items-center justify-between gap-3">
      <div className="flex items-center gap-3 min-w-0">
        <h2 className="text-base font-semibold flex items-center gap-2 shrink-0">
          <Bot className="w-5 h-5 text-gold" />
          <span className="hidden sm:inline tracking-tight">BuyAnything</span>
        </h2>
        {activeRow && (
          <div className="flex items-center gap-1.5 text-xs text-white/60 min-w-0">
            <span className="w-1.5 h-1.5 rounded-full bg-status-success shrink-0"></span>
            <span className="truncate max-w-[160px]">{activeRow.title}</span>
          </div>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {isLoggedIn && (
          <span className="text-xs text-white/60 hidden sm:block truncate max-w-[120px]">
            {userEmail || userPhone}
          </span>
        )}
        <a
          href="/merchants/register"
          className="flex items-center gap-1.5 text-xs text-white/70 hover:text-white transition-colors px-2 py-1.5 rounded-md hover:bg-white/10"
        >
          <Store className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Sell</span>
        </a>
        {isLoggedIn ? (
          <button
            type="button"
            onClick={onLogout}
            className="flex items-center gap-1.5 text-xs text-white/70 hover:text-white transition-colors px-2 py-1.5 rounded-md hover:bg-white/10"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        ) : (
          <a
            href="/login"
            className="flex items-center gap-1.5 text-xs font-medium text-gold-light hover:text-white transition-colors px-3 py-1.5 rounded-md border border-gold/30 hover:border-gold"
          >
            <LogIn className="w-3.5 h-3.5" />
            <span>Sign In</span>
          </a>
        )}
      </div>
    </div>
  );
}
