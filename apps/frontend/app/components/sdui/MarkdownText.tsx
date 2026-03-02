'use client';

import type { MarkdownTextBlock } from '../../sdui/types';

export function MarkdownText({ content }: MarkdownTextBlock) {
  if (!content) return null;

  const html = content
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br/>');

  return (
    <div
      className="text-sm text-gray-700 leading-relaxed prose prose-sm max-w-none"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
