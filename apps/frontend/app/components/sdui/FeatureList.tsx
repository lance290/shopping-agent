'use client';

import type { FeatureListBlock } from '../../sdui/types';

export function FeatureList({ features }: FeatureListBlock) {
  if (!features || features.length === 0) return null;

  return (
    <ul className="space-y-1">
      {features.map((feature, i) => (
        <li key={i} className="flex items-center gap-2 text-sm text-gray-700">
          <svg className="w-4 h-4 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          {feature}
        </li>
      ))}
    </ul>
  );
}
