'use client';

import type { MessageListBlock } from '../../sdui/types';

export function MessageList({ messages }: MessageListBlock) {
  if (!messages || messages.length === 0) return null;

  return (
    <div className="space-y-2 bg-gray-50 rounded-lg p-3">
      {messages.map((msg, i) => (
        <div key={i} className="flex gap-2 text-sm">
          <span className="font-medium text-gray-500 capitalize flex-shrink-0">
            {msg.sender === 'user' ? 'You' : msg.sender === 'assistant' ? 'Agent' : msg.sender}:
          </span>
          <span className="text-gray-700">{msg.text}</span>
        </div>
      ))}
    </div>
  );
}
