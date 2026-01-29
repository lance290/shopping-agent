'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User } from 'lucide-react';
import Link from 'next/link';
import { SignedIn, SignedOut, SignOutButton, UserButton } from '@clerk/nextjs';
import { useShoppingStore } from '../store';
import { fetchRowsFromDb, fetchProjectsFromDb } from '../utils/api';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { cn } from '../../utils/cn';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

export default function Chat() {
  const disableClerk = process.env.NEXT_PUBLIC_DISABLE_CLERK === '1';
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const lastRowIdRef = useRef<number | null>(null);
  
  const store = useShoppingStore();
  const activeRow = store.rows.find(r => r.id === store.activeRowId);

  useEffect(() => {
    inputRef.current?.focus();
    setInput('');
    if (!activeRow || store.activeRowId === null) return;
    if (lastRowIdRef.current === store.activeRowId) return;
    lastRowIdRef.current = store.activeRowId;

    // Clear previous messages and start fresh for the new active row
    setMessages([
      {
        id: `${Date.now()}-${store.activeRowId}`,
        role: 'assistant',
        content: `Focused on: ${activeRow.title}`,
      },
    ]);
  }, [store.activeRowId]);
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Load rows on mount
  useEffect(() => {
    const loadData = async () => {
      const rows = await fetchRowsFromDb();
      if (rows) {
        store.setRows(rows);
      }
      const projects = await fetchProjectsFromDb();
      if (projects) {
        store.setProjects(projects);
      }
    };
    loadData();
  }, []);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
    };
    
    setMessages(prev => [...prev, userMessage]);
    const queryText = input.trim();
    setInput('');
    setIsLoading(true);
    const intendedProjectId = store.targetProjectId;
    const effectiveActiveRowId = store.activeRowId;

    let assistantMessageId: string | null = null;
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          messages: [...messages, userMessage],
          activeRowId: effectiveActiveRowId,
          projectId: intendedProjectId,
        }),
      });
      
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let assistantContent = '';
      let sseBuffer = '';
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '',
      };
      assistantMessageId = assistantMessage.id;
      setMessages(prev => [...prev, assistantMessage]);
      
      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          sseBuffer += chunk;

          while (true) {
            const sepIndex = sseBuffer.indexOf('\n\n');
            if (sepIndex === -1) break;
            const frame = sseBuffer.slice(0, sepIndex);
            sseBuffer = sseBuffer.slice(sepIndex + 2);

            const lines = frame.split('\n');
            let eventName = 'message';
            const dataLines: string[] = [];
            for (const line of lines) {
              if (line.startsWith('event:')) {
                eventName = line.slice('event:'.length).trim();
              } else if (line.startsWith('data:')) {
                dataLines.push(line.slice('data:'.length).trim());
              }
            }
            const dataRaw = dataLines.join('\n');
            let data: any = null;
            try {
              data = dataRaw ? JSON.parse(dataRaw) : null;
            } catch {
              data = dataRaw;
            }

            if (eventName === 'assistant_message') {
              assistantContent = typeof data?.text === 'string' ? data.text : '';
            } else if (eventName === 'action_started') {
              if (data?.type === 'search') {
                store.setIsSearching(true);
              }
            } else if (eventName === 'row_created') {
              const row = data?.row;
              if (row?.id) {
                const mergedRows = [...store.rows.filter((r) => r.id !== row.id), row].sort((a, b) => (a.id ?? 0) - (b.id ?? 0));
                store.setRows(mergedRows);
                store.setActiveRowId(row.id);
                store.setCurrentQuery(row.title);
              }
            } else if (eventName === 'row_updated') {
              const row = data?.row;
              if (row?.id) {
                const mergedRows = [...store.rows.filter((r) => r.id !== row.id), row].sort((a, b) => (a.id ?? 0) - (b.id ?? 0));
                store.setRows(mergedRows);
                store.setActiveRowId(row.id);
                store.setCurrentQuery(row.title);
              }
            } else if (eventName === 'search_results') {
              const rowId = data?.row_id;
              const results = Array.isArray(data?.results) ? data.results : [];
              if (rowId) {
                store.setRowResults(rowId, results);
              }
              store.setIsSearching(false);
            } else if (eventName === 'done') {
              store.setIsSearching(false);
            } else if (eventName === 'error') {
              const msg = typeof data?.message === 'string' ? data.message : 'Something went wrong.';
              assistantContent = msg;
              store.setIsSearching(false);
            }

            setMessages(prev =>
              prev.map(m =>
                m.id === assistantMessage.id
                  ? { ...m, content: assistantContent }
                  : m
              )
            );
          }

        }
      } else {
        assistantContent = await response.text().catch(() => '');
      }

      if (!assistantContent.trim()) {
        assistantContent = 'Sorry, the assistant returned an empty response. Please try again.';
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantMessage.id
              ? { ...m, content: assistantContent }
              : m
          )
        );
      }
    } catch (error) {
      console.error('Chat error:', error);
      const fallbackText = 'Sorry, something went wrong. Please try again.';
      if (assistantMessageId) {
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantMessageId
              ? { ...m, content: fallbackText }
              : m
          )
        );
      } else {
        setMessages(prev => [...prev, {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: fallbackText,
        }]);
      }
    } finally {
      setIsLoading(false);
    }
  };
  
  useEffect(() => {
    const cardClickQuery = store.cardClickQuery;
    if (cardClickQuery) {
      const cardMessage: Message = {
        id: Date.now().toString(),
        role: 'user',
        content: cardClickQuery,
      };
      setMessages(prev => [...prev, cardMessage]);
      store.setCardClickQuery(null);
    }
  }, [store.cardClickQuery]);

  const handleDevLogout = async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
    } finally {
      window.location.href = '/login';
    }
  };

  return (
    <div className="flex flex-col h-full bg-warm-light border-r border-warm-grey/70">
      <div className="h-20 px-6 border-b border-warm-grey/70 bg-warm-light flex items-center justify-between gap-4">
        <div className="flex flex-col justify-center min-w-0">
          <div className="text-[10px] uppercase tracking-[0.16em] text-onyx-muted/80 font-medium">Assistant</div>
          <div className="flex items-center gap-3 min-w-0 mt-1">
            <h2 className="text-lg font-medium flex items-center gap-2 text-onyx shrink-0">
              <Bot className="w-5 h-5 text-agent-blurple" />
              Shopping Agent
            </h2>
            {activeRow && (
              <div className="flex items-center gap-2 text-[11px] text-onyx-muted min-w-0">
                <span className="w-1.5 h-1.5 rounded-full bg-status-success"></span>
                <span className="uppercase tracking-wider">Active</span>
                <span className="truncate max-w-[180px] text-onyx">{activeRow.title}</span>
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {disableClerk ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleDevLogout}
              className="text-xs"
            >
              Clear session
            </Button>
          ) : (
            <>
              <SignedOut>
                <Link
                  href="/login"
                  className="text-xs font-medium text-onyx hover:text-agent-blurple transition-colors"
                >
                  Sign in
                </Link>
              </SignedOut>
              <SignedIn>
                <SignOutButton redirectUrl="/login">
                  <Button type="button" variant="ghost" size="sm" className="text-xs">
                    Sign out
                  </Button>
                </SignOutButton>
                <UserButton afterSignOutUrl="/login" />
              </SignedIn>
            </>
          )}
        </div>
      </div>

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
        <div ref={messagesEndRef} />
      </div>

      <div className="px-6 py-5 bg-white border-t border-warm-grey">
        <form onSubmit={handleSubmit} className="flex gap-3 items-end">
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={activeRow ? `Refine "${activeRow.title}"...` : "What are you looking for?"}
            className="flex-1"
          />
          <Button
            type="submit"
            disabled={isLoading || !input?.trim()}
            variant="primary"
            size="md"
            className="px-4"
          >
            <Send size={20} />
          </Button>
        </form>
      </div>
    </div>
  );
}
