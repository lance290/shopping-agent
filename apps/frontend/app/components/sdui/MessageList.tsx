'use client';

import type { MessageListBlock } from '../../sdui/types';

export function MessageList({ messages }: MessageListBlock) {
  if (!messages || messages.length === 0) return null;

  return (
    <div className="space-y-2 bg-canvas-dark rounded-lg p-3">
      {messages.map((msg, i) => (
        <div key={i} className="flex gap-2 text-sm">
          <span className="font-medium text-ink-muted capitalize flex-shrink-0">
            {msg.sender === 'user' ? 'You' : msg.sender === 'assistant' ? 'Agent' : msg.sender}:
          </span>
          <span className="text-ink">{msg.text}</span>
        </div>
      ))}
    </div>
  );
}
