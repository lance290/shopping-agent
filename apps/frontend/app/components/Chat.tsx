'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles } from 'lucide-react';
import { useShoppingStore } from '../store';
import { persistRowToDb, runSearchApi, fetchRowsFromDb } from '../utils/api';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { cn } from '../../utils/cn';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

export default function Chat() {
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

    setMessages(prev => [
      ...prev,
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
    const loadRows = async () => {
      const rows = await fetchRowsFromDb();
      store.setRows(rows);
    };
    loadRows();
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
      const freshRows = await fetchRowsFromDb();
      store.setRows(freshRows);
      targetRow = freshRows.find(r => r.title === query) || null;
      if (!targetRow && freshRows.length > 0) {
        targetRow = freshRows[freshRows.length - 1];
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
    setInput('');
    setIsLoading(true);
    
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          messages: [...messages, userMessage],
          activeRowId: store.activeRowId,
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
            store.setRows(freshRows);
            
            if (freshRows.length > 0) {
              const newestRow = freshRows[freshRows.length - 1];
              store.setActiveRowId(newestRow.id);
              const results = await runSearchApi(newestRow.title, newestRow.id);
              store.setRowResults(newestRow.id, results);
            }
          }
          
          const updateMatch = assistantContent.match(/🔄 Updating row #(\d+) to "([^"]+)".*Done!/s);
          if (updateMatch && !rowUpdateHandled) {
            rowUpdateHandled = true;
            const updatedRowId = parseInt(updateMatch[1], 10);
            const updatedTitle = updateMatch[2];
            
            const freshRows = await fetchRowsFromDb();
            store.setRows(freshRows);
            store.setActiveRowId(updatedRowId);
            
            const results = await runSearchApi(updatedTitle, updatedRowId);
            store.setRowResults(updatedRowId, results);
          }
          
          const searchMatch = assistantContent.match(/🔍 Searching for "([^"]+)"/);
          if (searchMatch && searchMatch[1] !== lastProcessedQuery) {
            lastProcessedQuery = searchMatch[1];
            await handleSearchFlow(lastProcessedQuery);
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

  return (
    <div className="flex flex-col h-full bg-canvas-dark/5 backdrop-blur-3xl border-r border-warm-grey/50">
      <div className="p-6 border-b border-warm-grey/50 bg-white/50 backdrop-blur-md">
        <h2 className="font-serif text-2xl font-semibold flex items-center gap-3 text-onyx">
          <Sparkles className="w-6 h-6 text-agent-blurple animate-pulse" />
          Shopping Agent
        </h2>
        {activeRow && (
          <div className="flex items-center gap-2 mt-2">
            <span className="w-1.5 h-1.5 rounded-full bg-status-success shadow-[0_0_8px_rgba(16,185,129,0.5)]"></span>
            <span className="text-xs font-medium text-onyx-muted uppercase tracking-wider">Active Context:</span>
            <span className="text-sm font-medium text-onyx truncate max-w-[200px]">{activeRow.title}</span>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center p-8 opacity-60">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-agent-blurple to-agent-camel mb-6 flex items-center justify-center shadow-lg shadow-agent-blurple/20">
              <Bot className="w-8 h-8 text-white" />
            </div>
            <h3 className="font-serif text-xl text-onyx mb-2">How can I help you today?</h3>
            <p className="text-sm text-onyx-muted max-w-xs">
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
                "w-10 h-10 rounded-full flex items-center justify-center shrink-0 shadow-sm",
                m.role === 'user' 
                  ? "bg-onyx text-white" 
                  : "bg-white text-agent-blurple border border-warm-grey"
              )}
            >
              {m.role === 'user' ? <User size={18} /> : <Bot size={18} />}
            </div>
            
            <div
              className={cn(
                "rounded-2xl p-4 text-sm leading-relaxed shadow-sm",
                m.role === 'user'
                  ? "bg-onyx text-white rounded-tr-sm"
                  : "bg-white border border-warm-grey text-onyx rounded-tl-sm"
              )}
            >
              <div className="whitespace-pre-wrap font-sans">
                {m.content || (m.role === 'assistant' && isLoading ? (
                  <div className="flex gap-1 items-center h-5">
                    <span className="w-1.5 h-1.5 bg-agent-blurple rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                    <span className="w-1.5 h-1.5 bg-agent-blurple rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                    <span className="w-1.5 h-1.5 bg-agent-blurple rounded-full animate-bounce"></span>
                  </div>
                ) : '')}
              </div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-6 bg-white/80 backdrop-blur-md border-t border-warm-grey/50">
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
            variant="ai"
            size="md"
            className="rounded-xl px-4"
          >
            <Send size={20} />
          </Button>
        </form>
      </div>
    </div>
  );
}
