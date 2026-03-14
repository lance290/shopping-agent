'use client';

import { useState } from 'react';
import { submitOutcome, AUTH_REQUIRED, RESOLUTION_OPTIONS, QUALITY_OPTIONS } from '../../utils/api';
import type { ResolutionType, QualityType } from '../../utils/api';
import { ChevronDown } from 'lucide-react';

interface RowOutcomeSelectorProps {
  rowId: number;
  currentResolution?: string;
  currentQuality?: string;
}

export default function RowOutcomeSelector({
  rowId,
  currentResolution,
  currentQuality,
}: RowOutcomeSelectorProps) {
  const [resolution, setResolution] = useState<ResolutionType | undefined>(currentResolution as ResolutionType | undefined);
  const [quality, setQuality] = useState<QualityType | undefined>(currentQuality as QualityType | undefined);
  const [openMenu, setOpenMenu] = useState<'resolution' | 'quality' | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const handleResolution = async (val: ResolutionType) => {
    setIsSaving(true);
    const result = await submitOutcome(rowId, { outcome: val });
    setIsSaving(false);
    if (result === AUTH_REQUIRED) { alert('Sign in to rate this search'); return; }
    if (!result || typeof result !== 'object' || !('status' in result)) { alert('Failed to save'); return; }
    setResolution(val);
    setOpenMenu(null);
  };

  const handleQuality = async (val: QualityType) => {
    setIsSaving(true);
    const result = await submitOutcome(rowId, { quality: val });
    setIsSaving(false);
    if (result === AUTH_REQUIRED) { alert('Sign in to rate this search'); return; }
    if (!result || typeof result !== 'object' || !('status' in result)) { alert('Failed to save'); return; }
    setQuality(val);
    setOpenMenu(null);
  };

  const resLabel = RESOLUTION_OPTIONS.find((o) => o.type === resolution)?.label;
  const qualLabel = QUALITY_OPTIONS.find((o) => o.type === quality)?.label;

  const pillClass = (
    selected: string | undefined,
    positive: string[],
    negative: string[],
  ) =>
    selected
      ? positive.includes(selected)
        ? 'bg-green-50 border-green-200 text-green-700'
        : negative.includes(selected)
        ? 'bg-orange-50 border-orange-200 text-orange-700'
        : 'bg-blue-50 border-blue-200 text-blue-700'
      : 'bg-canvas-dark border-warm-grey text-ink-muted hover:border-gold/30';

  return (
    <div className="flex items-center gap-2 pt-2 border-t border-warm-grey/50 flex-wrap">
      <span className="text-[10px] text-onyx-muted font-medium uppercase tracking-wide">How did this go?</span>
      {/* Resolution selector */}
      <div className="relative">
        <button
          onClick={() => setOpenMenu(openMenu === 'resolution' ? null : 'resolution')}
          disabled={isSaving}
          className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg border transition-colors ${pillClass(resolution, ['solved'], ['not_solved'])}`}
        >
          {resLabel || 'Outcome'}
          <ChevronDown size={12} className={`transition-transform ${openMenu === 'resolution' ? 'rotate-180' : ''}`} />
        </button>
        {openMenu === 'resolution' && (
          <div className="absolute left-0 bottom-full mb-1 z-50 bg-white border border-warm-grey rounded-lg shadow-lg py-1 min-w-[160px]">
            {RESOLUTION_OPTIONS.map((opt) => (
              <button
                key={opt.type}
                onClick={() => handleResolution(opt.type)}
                className={`w-full text-left px-3 py-1.5 text-xs hover:bg-canvas-dark transition-colors ${
                  resolution === opt.type ? 'font-semibold text-gold-dark' : 'text-ink'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        )}
      </div>
      {/* Quality selector */}
      <div className="relative">
        <button
          onClick={() => setOpenMenu(openMenu === 'quality' ? null : 'quality')}
          disabled={isSaving}
          className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg border transition-colors ${pillClass(quality, ['results_were_strong'], ['results_were_noisy', 'routing_was_wrong'])}`}
        >
          {qualLabel || 'Result quality'}
          <ChevronDown size={12} className={`transition-transform ${openMenu === 'quality' ? 'rotate-180' : ''}`} />
        </button>
        {openMenu === 'quality' && (
          <div className="absolute left-0 bottom-full mb-1 z-50 bg-white border border-warm-grey rounded-lg shadow-lg py-1 min-w-[180px]">
            {QUALITY_OPTIONS.map((opt) => (
              <button
                key={opt.type}
                onClick={() => handleQuality(opt.type)}
                className={`w-full text-left px-3 py-1.5 text-xs hover:bg-canvas-dark transition-colors ${
                  quality === opt.type ? 'font-semibold text-gold-dark' : 'text-ink'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
