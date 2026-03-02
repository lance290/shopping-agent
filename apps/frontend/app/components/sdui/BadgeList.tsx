'use client';

import type { BadgeListBlock } from '../../sdui/types';

export function BadgeList({ tags, source_refs }: BadgeListBlock) {
  if (!tags || tags.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5">
      {tags.map((tag, i) => (
        <span
          key={i}
          className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700"
          title={source_refs?.[i] ? `Source: ${source_refs[i]}` : undefined}
        >
          {tag}
          {source_refs?.[i] && (
            <button
              className="ml-1 text-gray-400 hover:text-blue-500"
              title="Why we're saying this"
              aria-label={`Provenance for ${tag}`}
            >
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </button>
          )}
        </span>
      ))}
    </div>
  );
}
