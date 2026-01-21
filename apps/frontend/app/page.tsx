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
    <main className="flex h-screen w-full bg-canvas text-onyx overflow-hidden font-sans selection:bg-agent-blurple/20 selection:text-agent-blurple">
      {/* Specifications Sidebar (Leftmost, collapsible, absolute on mobile, relative on desktop if we wanted) 
          Actually, current design puts it leftmost in the flex container.
          Let's keep it there but make sure it has z-index to slide properly.
      */}
      <div className="z-20 shadow-xl shadow-onyx/5">
        <ChoiceFactorPanel />
      </div>

      {/* Chat Pane (Center Left) */}
      <div 
        style={{ width: `${chatWidthPx}px` }} 
        className="h-full shrink-0 z-10 relative shadow-[5px_0_30px_-10px_rgba(0,0,0,0.05)]"
      >
        <Chat />
      </div>

      {/* Draggable Handle */}
      <div
        className={cn(
          "w-1 h-full cursor-col-resize z-30 transition-colors duration-200 relative group -ml-0.5 hover:w-2",
          isDraggingRef.current ? "bg-agent-blurple w-1.5" : "hover:bg-agent-blurple/50"
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
        <div className="absolute inset-y-0 -left-2 -right-2 z-30" /> {/* Hit area */}
      </div>
      
      {/* Board Pane (Right) */}
      <div className="flex-1 min-w-0 bg-warm-light/30 h-full relative z-0">
        <ProcurementBoard />
      </div>
    </main>
  );
}
