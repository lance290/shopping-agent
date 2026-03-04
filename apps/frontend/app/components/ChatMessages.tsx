'use client';

import { forwardRef } from 'react';
import { Bot, User } from 'lucide-react';
import { cn } from '../../utils/cn';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

interface ChatMessagesProps {
  messages: Message[];
  isLoading: boolean;
}

const ChatMessages = forwardRef<HTMLDivElement, ChatMessagesProps>(
  function ChatMessages({ messages, isLoading }, ref) {
    return (
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center px-6 text-onyx-muted">
            <div className="w-14 h-14 rounded-full bg-white border border-warm-grey flex items-center justify-center mb-5">
              <Bot className="w-6 h-6 text-agent-blurple" />
            </div>
            <div className="text-[10px] uppercase tracking-[0.16em] text-onyx-muted/80 font-medium">Welcome</div>
            <h3 className="text-lg font-medium text-onyx mt-2 mb-2">How can I help you today?</h3>
            <p className="text-sm max-w-xs">
              I can help you find products, compare prices, and manage your procurement list.
            </p>
          </div>
        )}
        
        {messages.map((m) => (
          <div
            key={m.id}
            className={cn(
              "flex gap-4 max-w-[90%]",
              m.role === 'user' ? "ml-auto flex-row-reverse" : ""
            )}
          >
            <div
              className={cn(
                "w-9 h-9 rounded-full flex items-center justify-center shrink-0 border border-warm-grey/70 bg-white/90",
                m.role === 'user' ? "bg-[#E7F0FF] text-onyx border-[#C7D9F6]" : "text-agent-blurple"
              )}
            >
              {m.role === 'user' ? <User size={18} /> : <Bot size={18} />}
            </div>
            
            <div
              className={cn(
                "rounded-2xl px-4 py-3 text-sm leading-relaxed",
                m.role === 'user'
                  ? "bg-gradient-to-br from-[#E7F0FF] to-[#D3E2FB] text-ink rounded-tr-sm border border-[#C7D9F6] shadow-[0_6px_14px_rgba(13,82,168,0.12)]"
                  : "bg-white/95 border border-warm-grey/70 text-ink rounded-tl-sm"
              )}
            >
              <div className="whitespace-pre-wrap font-sans">
                {m.content || (m.role === 'assistant' && isLoading ? (
                  <div className="flex gap-1 items-center h-5">
                    <span className="w-1.5 h-1.5 bg-onyx-muted rounded-full animate-pulse"></span>
                    <span className="w-1.5 h-1.5 bg-onyx-muted rounded-full animate-pulse [animation-delay:0.2s]"></span>
                    <span className="w-1.5 h-1.5 bg-onyx-muted rounded-full animate-pulse [animation-delay:0.4s]"></span>
                  </div>
                ) : '')}
              </div>
            </div>
          </div>
        ))}
        <div ref={ref} />
      </div>
    );
  }
);

export default ChatMessages;
export type { Message };
