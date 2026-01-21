'use client';

import { useEffect, useRef, useState } from 'react';
import Chat from './components/Chat';
import ProcurementBoard from './components/Board';
import ChoiceFactorPanel from './components/ChoiceFactorPanel';
import { cn } from '../utils/cn';

export default function Home() {
  const CHAT_MIN_PX = 360;
  const CHAT_MAX_PX = 700;
  const CHAT_DEFAULT_PX = 450;

  const [chatWidthPx, setChatWidthPx] = useState<number>(CHAT_DEFAULT_PX);
  const isDraggingRef = useRef(false);
  const dragStartXRef = useRef<number>(0);
  const dragStartWidthRef = useRef<number>(CHAT_DEFAULT_PX);
  const latestWidthRef = useRef<number>(CHAT_DEFAULT_PX);

  useEffect(() => {
    try {
      const raw = localStorage.getItem('chatWidthPx');
      if (!raw) return;
      const parsed = Number(raw);
      if (!Number.isFinite(parsed)) return;
      setChatWidthPx(Math.min(CHAT_MAX_PX, Math.max(CHAT_MIN_PX, parsed)));
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!isDraggingRef.current) return;
      const delta = e.clientX - dragStartXRef.current;
      const next = Math.min(CHAT_MAX_PX, Math.max(CHAT_MIN_PX, dragStartWidthRef.current + delta));
      latestWidthRef.current = next;
      setChatWidthPx(next);
    };

    const onUp = () => {
      if (!isDraggingRef.current) return;
      isDraggingRef.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      try {
        localStorage.setItem('chatWidthPx', String(latestWidthRef.current));
      } catch {
        // ignore
      }
    };

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, []);

  return (
    <main className="flex h-screen w-full bg-transparent text-onyx overflow-hidden font-sans selection:bg-agent-blurple/15 selection:text-agent-blurple">
      {/* Specifications Sidebar (Leftmost, collapsible, absolute on mobile, relative on desktop if we wanted) 
          Actually, current design puts it leftmost in the flex container.
          Let's keep it there but make sure it has z-index to slide properly.
      */}
      <div className="z-20 border-r border-warm-grey/70">
        <ChoiceFactorPanel />
      </div>

      {/* Chat Pane (Center Left) */}
      <div 
        style={{ width: `${chatWidthPx}px` }} 
        className="h-full shrink-0 z-10 relative"
      >
        <Chat />
      </div>

      {/* Draggable Handle */}
      <div
        className={cn(
          "w-px h-full cursor-col-resize z-30 transition-colors duration-200 relative group bg-warm-grey/70 hover:bg-onyx/40",
          isDraggingRef.current ? "bg-agent-blurple" : ""
        )}
        onMouseDown={(e) => {
          e.preventDefault();
          isDraggingRef.current = true;
          dragStartXRef.current = e.clientX;
          dragStartWidthRef.current = chatWidthPx;
          latestWidthRef.current = chatWidthPx;
          document.body.style.cursor = 'col-resize';
          document.body.style.userSelect = 'none';
        }}
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize chat"
      >
        <div className="absolute inset-y-0 -left-2 -right-2 z-30" />
      </div>
      
      {/* Board Pane (Right) */}
      <div className="flex-1 min-w-0 bg-transparent h-full relative z-0">
        <ProcurementBoard />
      </div>
    </main>
  );
}
