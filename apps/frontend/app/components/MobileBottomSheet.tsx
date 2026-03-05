'use client';

import { useRef, useState, useCallback, useEffect } from 'react';
import { ChevronUp } from 'lucide-react';

// Snap points as percentages of viewport height (from bottom)
const SNAP_PEEK = 72;   // px from bottom — just the handle + active list label
const SNAP_HALF = 50;   // 50% of viewport
const SNAP_FULL = 90;   // 90% of viewport

type SnapPoint = 'peek' | 'half' | 'full';

interface MobileBottomSheetProps {
  children: React.ReactNode;
  /** Label shown in the peek bar (e.g. active list name + count) */
  peekLabel?: string;
  /** Secondary info in peek bar */
  peekSublabel?: string;
  /** External control: set to 'half' when new results arrive */
  snapTo?: SnapPoint;
  onSnapChange?: (snap: SnapPoint) => void;
}

function snapToPixels(snap: SnapPoint): number {
  const vh = window.innerHeight;
  switch (snap) {
    case 'peek': return SNAP_PEEK;
    case 'half': return vh * (SNAP_HALF / 100);
    case 'full': return vh * (SNAP_FULL / 100);
  }
}

function nearestSnap(heightPx: number): SnapPoint {
  const vh = window.innerHeight;
  const peekPx = SNAP_PEEK;
  const halfPx = vh * (SNAP_HALF / 100);
  const fullPx = vh * (SNAP_FULL / 100);

  const distPeek = Math.abs(heightPx - peekPx);
  const distHalf = Math.abs(heightPx - halfPx);
  const distFull = Math.abs(heightPx - fullPx);

  if (distPeek <= distHalf && distPeek <= distFull) return 'peek';
  if (distHalf <= distFull) return 'half';
  return 'full';
}

export default function MobileBottomSheet({
  children,
  peekLabel,
  peekSublabel,
  snapTo,
  onSnapChange,
}: MobileBottomSheetProps) {
  const sheetRef = useRef<HTMLDivElement>(null);
  const [currentSnap, setCurrentSnap] = useState<SnapPoint>('peek');
  const [sheetHeight, setSheetHeight] = useState(SNAP_PEEK);
  const [isDragging, setIsDragging] = useState(false);

  // Touch tracking
  const dragStartY = useRef(0);
  const dragStartHeight = useRef(0);

  // Apply snap point
  const applySnap = useCallback((snap: SnapPoint) => {
    const px = snapToPixels(snap);
    setSheetHeight(px);
    setCurrentSnap(snap);
    onSnapChange?.(snap);
  }, [onSnapChange]);

  // External snapTo control
  useEffect(() => {
    if (snapTo && snapTo !== currentSnap) {
      applySnap(snapTo);
    }
  }, [snapTo, currentSnap, applySnap]);

  // Initialize on mount
  useEffect(() => {
    setSheetHeight(SNAP_PEEK);
  }, []);

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    setIsDragging(true);
    dragStartY.current = e.touches[0].clientY;
    dragStartHeight.current = sheetHeight;
  }, [sheetHeight]);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!isDragging) return;
    const deltaY = dragStartY.current - e.touches[0].clientY;
    const newHeight = Math.max(SNAP_PEEK, Math.min(window.innerHeight * 0.95, dragStartHeight.current + deltaY));
    setSheetHeight(newHeight);
  }, [isDragging]);

  const handleTouchEnd = useCallback(() => {
    if (!isDragging) return;
    setIsDragging(false);
    const snap = nearestSnap(sheetHeight);
    applySnap(snap);
  }, [isDragging, sheetHeight, applySnap]);

  // Mouse drag support (for desktop testing)
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    setIsDragging(true);
    dragStartY.current = e.clientY;
    dragStartHeight.current = sheetHeight;
    e.preventDefault();
  }, [sheetHeight]);

  useEffect(() => {
    if (!isDragging) return;
    const handleMouseMove = (e: MouseEvent) => {
      const deltaY = dragStartY.current - e.clientY;
      const newHeight = Math.max(SNAP_PEEK, Math.min(window.innerHeight * 0.95, dragStartHeight.current + deltaY));
      setSheetHeight(newHeight);
    };
    const handleMouseUp = () => {
      setIsDragging(false);
      const snap = nearestSnap(sheetHeight);
      applySnap(snap);
    };
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, sheetHeight, applySnap]);

  const handlePeekTap = () => {
    if (currentSnap === 'peek') {
      applySnap('half');
    } else {
      applySnap('peek');
    }
  };

  return (
    <div
      ref={sheetRef}
      className="fixed bottom-0 left-0 right-0 z-50 bg-white rounded-t-2xl shadow-[0_-4px_24px_rgba(0,0,0,0.12)] flex flex-col"
      style={{
        height: sheetHeight,
        transition: isDragging ? 'none' : 'height 0.3s cubic-bezier(0.32, 0.72, 0, 1)',
        touchAction: 'none',
      }}
    >
      {/* Drag Handle + Peek Bar */}
      <div
        className="flex-shrink-0 cursor-grab active:cursor-grabbing select-none"
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        onMouseDown={handleMouseDown}
      >
        {/* Handle pill */}
        <div className="flex justify-center pt-2 pb-1">
          <div className="w-10 h-1 rounded-full bg-gray-300" />
        </div>

        {/* Peek label row */}
        <button
          type="button"
          onClick={handlePeekTap}
          className="w-full flex items-center justify-between px-4 pb-2"
        >
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-sm font-semibold text-ink truncate">
              {peekLabel || 'Your Lists'}
            </span>
            {peekSublabel && (
              <span className="text-xs text-ink-muted">{peekSublabel}</span>
            )}
          </div>
          <ChevronUp
            size={18}
            className={`text-ink-muted transition-transform duration-300 ${
              currentSnap !== 'peek' ? 'rotate-180' : ''
            }`}
          />
        </button>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto overscroll-contain min-h-0">
        {children}
      </div>
    </div>
  );
}

export type { SnapPoint };
