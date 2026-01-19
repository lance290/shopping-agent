'use client';

import { useEffect, useRef, useState } from 'react';
import Chat from './components/Chat';
import ProcurementBoard from './components/Board';
import ChoiceFactorPanel from './components/ChoiceFactorPanel';

export default function Home() {
  const CHAT_MIN_PX = 320;
  const CHAT_MAX_PX = 580;
  const CHAT_DEFAULT_PX = 420;

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
    <main className="flex h-screen w-full bg-white overflow-hidden">
      {/* Specifications Sidebar (Leftmost, collapsible) */}
      <ChoiceFactorPanel />

      {/* Chat Pane (Center Left) */}
      <div style={{ width: `${chatWidthPx}px` }} className="h-full shrink-0">
        <Chat />
      </div>

      <div
        className="w-3 bg-gray-200 hover:bg-blue-400 transition-colors cursor-col-resize"
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
      />
      
      {/* Board Pane (Right) */}
      <ProcurementBoard />
    </main>
  );
}
