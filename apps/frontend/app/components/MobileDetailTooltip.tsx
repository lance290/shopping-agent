'use client';

import React, { useEffect, useState } from 'react';

interface MobileDetailTooltipProps {
  show: boolean;
  onDismiss: () => void;
}

export function MobileDetailTooltip({ show, onDismiss }: MobileDetailTooltipProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (show) {
      setIsVisible(true);
      const timer = setTimeout(() => {
        setIsVisible(false);
        onDismiss();
      }, 3000);

      return () => clearTimeout(timer);
    }
  }, [show, onDismiss]);

  if (!isVisible) return null;

  return (
    <div
      className="fixed bottom-20 left-1/2 -translate-x-1/2 z-50 px-4 py-3 bg-gray-900 text-white text-sm rounded-lg shadow-lg animate-fade-in"
      role="status"
      aria-live="polite"
      onClick={() => {
        setIsVisible(false);
        onDismiss();
      }}
    >
      Open on desktop for details
    </div>
  );
}
