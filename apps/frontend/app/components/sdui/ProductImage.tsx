'use client';

import type { ProductImageBlock } from '../../sdui/types';

export function ProductImage({ url, alt }: ProductImageBlock) {
  return (
    <div className="relative w-full aspect-square max-w-[200px] rounded-lg overflow-hidden bg-gray-100">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={url}
        alt={alt || ''}
        className="w-full h-full object-cover"
        loading="lazy"
        onError={(e) => {
          (e.target as HTMLImageElement).src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect fill="%23f3f4f6" width="100" height="100"/><text x="50" y="55" text-anchor="middle" fill="%239ca3af" font-size="12">No Image</text></svg>';
        }}
      />
    </div>
  );
}
