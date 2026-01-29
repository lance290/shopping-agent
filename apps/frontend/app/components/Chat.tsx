'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User } from 'lucide-react';
import Link from 'next/link';
import { SignedIn, SignedOut, SignOutButton, UserButton } from '@clerk/nextjs';
import { useShoppingStore, shouldForceNewRow } from '../store';
import { persistRowToDb, runSearchApi, fetchRowsFromDb, fetchProjectsFromDb, createRowInDb } from '../utils/api';
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

  const handleSearchFlow = async (query: string) => {
    store.setCurrentQuery(query);

    // 1c. Select or create card
    const currentRows = store.rows;
    let targetRow = store.selectOrCreateRow(query, currentRows);
    
    if (targetRow) {
      store.setActiveRowId(targetRow.id);
      if (targetRow.title !== query) {
        store.updateRow(targetRow.id, { title: query });
        await persistRowToDb(targetRow.id, query);
      }
    } else {
      // No match found - create a new row explicitly so we can attach it to the selected project.
      const intendedProjectId = store.targetProjectId;
      const created = await createRowInDb(query, store.targetProjectId);
      if (created) {
        store.addRow(created);
        store.setActiveRowId(created.id);

        store.setIsSearching(true);
        const results = await runSearchApi(query, created.id);
        store.setRowResults(created.id, results);
        return;
      }

      // Fallback: if create failed, refresh and attempt to locate an existing row.
      const freshRows = await fetchRowsFromDb();
      if (freshRows) {
        store.setRows(freshRows);
        targetRow = intendedProjectId
          ? freshRows.find((r) => r.title === query && r.project_id === intendedProjectId) || null
          : freshRows.find((r) => r.title === query) || null;
      }

      if (targetRow) {
        store.setActiveRowId(targetRow.id);
      }
    }

    if (targetRow) {
      store.setIsSearching(true);
      const results = await runSearchApi(query, targetRow.id);
      store.setRowResults(targetRow.id, results);
    }
  };
  
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
    const shouldNewRow = shouldForceNewRow({
      message: queryText,
      activeRowTitle: activeRow?.title || null,
      aggressiveness: store.newRowAggressiveness,
    });

    const effectiveActiveRowId = shouldNewRow ? null : store.activeRowId;
    if (shouldNewRow) {
      store.setActiveRowId(null);
    }

    const pickRowFromFresh = (freshRows: any[], query: string) => {
      const q = query.toLowerCase().trim();
      const scoped = intendedProjectId
        ? freshRows.filter((r) => r.project_id === intendedProjectId)
        : freshRows;
      const byTitle = scoped.find((r) => r.title?.toLowerCase?.().trim?.() === q);
      const newestById = [...scoped].sort((a, b) => (b.id ?? 0) - (a.id ?? 0))[0];
      return byTitle || newestById || null;
    };

    let searchTriggered = false;
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
      
      if (!response.ok) throw new Error('Failed to send message');
      
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let assistantContent = '';
      let lastProcessedQuery = '';
      let rowCreationHandled = false;
      let rowUpdateHandled = false;
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '',
      };
      setMessages(prev => [...prev, assistantMessage]);
      
      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value, { stream: true });
          assistantContent += chunk;
          
          const rowMatch = assistantContent.match(/✅ Adding "([^"]+)" to your procurement board/);
          if (rowMatch && !rowCreationHandled) {
            rowCreationHandled = true;
            await new Promise(resolve => setTimeout(resolve, 800));
            const freshRows = await fetchRowsFromDb();
            if (freshRows) {
              store.setRows(freshRows);

              const selected = pickRowFromFresh(freshRows, rowMatch[1]);
              if (selected) {
                store.setActiveRowId(selected.id);
                store.setCurrentQuery(selected.title);
              }
            }
          }
          
          const updateMatch = assistantContent.match(/🔄 Updating row #(\d+) to "([^"]+)".*Done!/s);
          if (updateMatch && !rowUpdateHandled) {
            rowUpdateHandled = true;
            const updatedRowId = parseInt(updateMatch[1], 10);
            
            const freshRows = await fetchRowsFromDb();
            if (freshRows) {
              store.setRows(freshRows);
              store.setActiveRowId(updatedRowId);
            }
          }
          
          const searchMatch = assistantContent.match(/🔍 Searching for "([^"]+)"/);
          if (searchMatch && searchMatch[1] !== lastProcessedQuery) {
            lastProcessedQuery = searchMatch[1];
            searchTriggered = true;

            // Ensure we have a stable active row for this search
            let rowId = store.activeRowId;
            if (!rowId) {
              const freshRows = await fetchRowsFromDb();
              if (freshRows) {
                store.setRows(freshRows);
                const selected = pickRowFromFresh(freshRows, lastProcessedQuery);
                if (selected) {
                  rowId = selected.id;
                  store.setActiveRowId(rowId);
                }
              }
            }

            if (rowId) {
              store.setIsSearching(true);
              const results = await runSearchApi(lastProcessedQuery, rowId);
              store.setRowResults(rowId, results);
            }
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
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, something went wrong. Please try again.',
      }]);
    } finally {
      if (!searchTriggered) {
        const rowId = store.activeRowId;
        if (rowId && queryText) {
          store.setIsSearching(true);
          const results = await runSearchApi(queryText, rowId);
          store.setRowResults(rowId, results);
        }
      }
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
        <div className="mb-3">
          <div className="flex items-center justify-between">
            <div className="text-[10px] uppercase tracking-[0.16em] text-onyx-muted/80 font-medium">Topic switching</div>
            <div className="text-[11px] text-onyx-muted">{store.newRowAggressiveness}</div>
          </div>
          <input
            type="range"
            min={0}
            max={100}
            step={1}
            value={store.newRowAggressiveness}
            onChange={(e) => store.setNewRowAggressiveness(Number(e.target.value))}
            className="w-full"
            aria-label="Topic switching aggressiveness"
          />
        </div>
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
