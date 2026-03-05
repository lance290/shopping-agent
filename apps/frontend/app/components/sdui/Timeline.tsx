'use client';

import type { TimelineBlock } from '../../sdui/types';

export function Timeline({ steps }: TimelineBlock) {
  if (!steps || steps.length === 0) return null;

  return (
    <div className="flex items-center gap-1 overflow-x-auto py-2">
      {steps.map((step, i) => (
        <div key={i} className="flex items-center gap-1 flex-shrink-0">
          <div className="flex flex-col items-center">
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                step.status === 'done'
                  ? 'bg-green-500 text-white'
                  : step.status === 'active'
                  ? 'bg-gold text-navy ring-2 ring-gold/30'
                  : 'bg-canvas-dark text-ink-muted'
              }`}
            >
              {step.status === 'done' ? '✓' : i + 1}
            </div>
            <span className={`text-xs mt-1 whitespace-nowrap ${
              step.status === 'active' ? 'font-semibold text-gold-dark' : 'text-ink-muted'
            }`}>
              {step.label}
            </span>
          </div>
          {i < steps.length - 1 && (
            <div className={`w-8 h-0.5 mt-[-14px] ${
              step.status === 'done' ? 'bg-green-400' : 'bg-canvas-dark'
            }`} />
          )}
        </div>
      ))}
    </div>
  );
}
