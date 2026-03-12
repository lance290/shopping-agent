'use client';

import { useEffect, useState } from 'react';
import type { SearchProgress } from '../../store-state';

const SEARCH_TIPS = [
  'Comparing prices across providers...',
  'Finding the best options for you...',
  'Checking availability and ratings...',
  'Scanning trusted marketplaces...',
  'Looking for the perfect match...',
];

export function SearchProgressBar({ progress, isSearching }: { progress?: SearchProgress; isSearching: boolean }) {
  const [elapsed, setElapsed] = useState(0);
  const [tipIndex, setTipIndex] = useState(0);

  useEffect(() => {
    if (!isSearching || !progress) {
      setElapsed(0);
      return;
    }
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - progress.startedAt) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [isSearching, progress]);

  useEffect(() => {
    if (!isSearching) return;
    const interval = setInterval(() => {
      setTipIndex(i => (i + 1) % SEARCH_TIPS.length);
    }, 4000);
    return () => clearInterval(interval);
  }, [isSearching]);

  if (!isSearching && !progress) return null;
  if (progress?.isComplete && !isSearching) return null;

  const providers = progress?.providers ?? [];
  const totalResults = progress?.totalResultsSoFar ?? 0;
  const agentMessage = progress?.agentMessage;

  return (
    <div className="space-y-3" style={{ animation: 'fade-in 0.3s ease-out' }}>
      {/* Progress bar */}
      <div className="relative h-1 bg-warm-grey/50 rounded-full overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-gold via-gold-light to-gold rounded-full animate-progress-indeterminate" />
      </div>

      {/* Status row */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {/* Animated search icon */}
          <div className="flex-shrink-0 w-5 h-5 relative">
            <svg className="w-5 h-5 text-gold animate-spin-slow" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
            </svg>
          </div>

          {/* Agent message or rotating tip */}
          <p className="text-xs text-ink-muted truncate transition-opacity duration-500">
            {agentMessage || SEARCH_TIPS[tipIndex]}
          </p>
        </div>

        {/* Live counter */}
        {totalResults > 0 && (
          <span
            className="flex-shrink-0 text-xs font-medium text-gold-dark tabular-nums"
            style={{ animation: 'counter-in 0.3s ease-out' }}
          >
            {totalResults} found
          </span>
        )}

        {/* Elapsed timer */}
        {elapsed > 0 && (
          <span className="flex-shrink-0 text-[10px] text-onyx-muted tabular-nums">
            {elapsed}s
          </span>
        )}
      </div>

      {/* Provider chips */}
      {providers.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {providers.map((p, i) => (
            <span
              key={p.name}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium"
              style={{ animation: `chip-in 0.3s ease-out ${i * 100}ms backwards` }}
            >
              {p.status === 'done' ? (
                <>
                  <svg className="w-3 h-3 text-status-success" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                  <span className="text-status-success">{p.displayName}</span>
                  {p.resultCount > 0 && (
                    <span className="text-onyx-muted">({p.resultCount})</span>
                  )}
                </>
              ) : p.status === 'error' ? (
                <>
                  <svg className="w-3 h-3 text-status-error" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  <span className="text-status-error">{p.displayName}</span>
                </>
              ) : (
                <>
                  <div className="w-3 h-3 border-2 border-gold border-t-transparent rounded-full animate-spin" />
                  <span className="text-ink-muted">{p.displayName}</span>
                </>
              )}
            </span>
          ))}

          {/* "More searching..." indicator when results are still incoming */}
          {!progress?.isComplete && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium text-ink-muted animate-pulse">
              <div className="w-3 h-3 border-2 border-warm-grey border-t-gold rounded-full animate-spin" />
              searching...
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export function SkeletonCard({ index = 0 }: { index?: number }) {
  return (
    <div
      className="rounded-lg"
      style={{ animation: `skeleton-in 0.5s ease-out ${index * 150}ms backwards` }}
    >
      <div className="flex items-center gap-3 p-2">
        {/* Image skeleton */}
        <div className="w-12 h-12 rounded-md bg-canvas-dark skeleton-shimmer flex-shrink-0" />

        {/* Text skeletons */}
        <div className="flex-1 min-w-0 space-y-2">
          <div className="h-3.5 bg-canvas-dark rounded skeleton-shimmer w-3/4" />
          <div className="h-3 bg-canvas-dark rounded skeleton-shimmer w-1/2" />
        </div>

        {/* Price skeleton */}
        <div className="flex-shrink-0 space-y-1.5">
          <div className="h-4 bg-canvas-dark rounded skeleton-shimmer w-16 ml-auto" />
          <div className="h-3 bg-canvas-dark rounded skeleton-shimmer w-12 ml-auto" />
        </div>
      </div>
    </div>
  );
}

export function SkeletonCardGroup({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }, (_, i) => (
        <SkeletonCard key={i} index={i} />
      ))}
    </div>
  );
}
