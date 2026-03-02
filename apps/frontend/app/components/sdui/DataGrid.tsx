'use client';

import type { DataGridBlock } from '../../sdui/types';

export function DataGrid({ items }: DataGridBlock) {
  if (!items || items.length === 0) return null;

  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
      {items.map((item, i) => (
        <div key={i} className="contents">
          <dt className="text-gray-500 font-medium">{item.key}</dt>
          <dd className="text-gray-900">{item.value}</dd>
        </div>
      ))}
    </div>
  );
}
