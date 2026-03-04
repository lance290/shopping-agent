'use client';

import { Bot, LogOut, Store } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import type { Row } from '../store';

interface ChatHeaderProps {
  activeRow: Row | undefined;
  userEmail: string | null;
  userPhone: string | null;
  onLogout: () => void;
}

export default function ChatHeader({ activeRow, userEmail, userPhone, onLogout }: ChatHeaderProps) {
  return (
    <div className="h-20 px-6 border-b border-warm-grey/70 bg-warm-light flex items-center justify-between gap-4">
      <div className="flex flex-col justify-center min-w-0">
        <div className="text-[10px] uppercase tracking-[0.16em] text-onyx-muted/80 font-medium">Assistant</div>
        <div className="flex items-center gap-3 min-w-0 mt-1">
          <h2 className="text-lg font-medium flex items-center gap-2 text-onyx shrink-0">
            <Bot className="w-5 h-5 text-agent-blurple" />
            Shopping Agent
          </h2>
          {activeRow && (
            <div className="flex items-center gap-2 text-[11px] text-onyx-muted min-w-0">
              <span className="w-1.5 h-1.5 rounded-full bg-status-success"></span>
              <span className="uppercase tracking-wider">Active</span>
              <span className="truncate max-w-[180px] text-onyx">{activeRow.title}</span>
            </div>
          )}
        </div>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        <div className="text-xs text-onyx-muted hidden sm:block">
          {userEmail || userPhone || 'User'}
        </div>
        <a
          href="/merchants/register"
          className="flex items-center gap-1.5 text-xs text-onyx-muted hover:text-agent-blurple transition-colors"
          title="Become a seller"
        >
          <Store className="w-4 h-4" />
          <span className="hidden sm:inline">Sell</span>
        </a>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onLogout}
          className="text-xs text-onyx-muted hover:text-agent-blurple"
          title="Sign out"
        >
          <LogOut className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}
