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
  promptSuggestions?: string[];
  onPromptSelect?: (prompt: string) => void;
}

const ChatMessages = forwardRef<HTMLDivElement, ChatMessagesProps>(
  function ChatMessages({ messages, isLoading, promptSuggestions = [], onPromptSelect }, ref) {
    return (
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center text-center mt-20 mb-12 opacity-0 animate-fade-in px-4">
            <div className="w-16 h-16 bg-gradient-to-tr from-gold to-gold-light rounded-2xl flex items-center justify-center mb-6 shadow-sm ring-1 ring-black/5">
              <span className="text-2xl" role="img" aria-label="sparkles">✨</span>
            </div>
            <div className="text-[10px] uppercase tracking-[0.16em] text-onyx-muted/80 font-medium">Welcome</div>
            <h3 className="text-xl font-semibold text-onyx mt-2 mb-2">BuyAnything Intelligence</h3>
            <p className="text-sm max-w-sm leading-relaxed text-onyx-muted">
              Your AI Chief of Staff for sourcing and procurement. Describe your project requirements, and I&apos;ll secure vetted vendor bids for you.
            </p>
            {promptSuggestions.length > 0 && (
              <div className="mt-8 w-full max-w-md space-y-3">
                <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-onyx-muted/70 text-left">
                  Things to try
                </div>
                <div className="grid gap-2">
                  {promptSuggestions.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => onPromptSelect?.(prompt)}
                      className="rounded-2xl border border-warm-grey bg-white px-4 py-3 text-left text-sm text-ink shadow-sm transition hover:border-gold hover:bg-gold/5"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}
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
                m.role === 'user' ? "bg-[#E7F0FF] text-onyx border-[#C7D9F6]" : "text-gold-dark"
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
