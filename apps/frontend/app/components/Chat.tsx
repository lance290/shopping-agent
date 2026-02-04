'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, LogOut } from 'lucide-react';
import { useShoppingStore } from '../store';
import { fetchRowsFromDb, fetchProjectsFromDb, saveChatHistory } from '../utils/api';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { cn } from '../../utils/cn';
import { logout, getMe } from '../utils/auth';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

export default function Chat() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [userPhone, setUserPhone] = useState<string | null>(null);
  // Track pending clarification context for multi-turn flows (e.g., aviation)
  const [pendingClarification, setPendingClarification] = useState<{
    type: string;
    service_type?: string;
    title?: string;
    partial_constraints: Record<string, unknown>;
  } | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const lastRowIdRef = useRef<number | null>(null);
  
  const store = useShoppingStore();
  const activeRow = store.rows.find(r => r.id === store.activeRowId);

  useEffect(() => {
    // Check auth state
    getMe().then(user => {
      if (user && user.authenticated) {
        setUserEmail(user.email || null);
        setUserPhone(user.phone_number || null);
      }
    });
  }, []);

  useEffect(() => {
    if (!activeRow || store.activeRowId === null) return;
    if (lastRowIdRef.current === store.activeRowId) return;
    lastRowIdRef.current = store.activeRowId;
    
    // Only focus/clear on actual row switch
    setInput('');

    // Load chat history from the row, or start fresh
    let loadedMessages: Message[] = [];
    if (activeRow.chat_history) {
      try {
        loadedMessages = JSON.parse(activeRow.chat_history);
      } catch {
        loadedMessages = [];
      }
    }
    
    if (loadedMessages.length > 0) {
      setMessages(loadedMessages);
    } else {
      // No history - show focus message
      setMessages([
        {
          id: `${Date.now()}-${store.activeRowId}`,
          role: 'assistant',
          content: `Focused on: ${activeRow.title}`,
        },
      ]);
    }
    
    // Clear clarification context when switching rows
    setPendingClarification(null);
  }, [store.activeRowId, activeRow]);
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  // Helper to save chat history - called only on stream end, not on every message change
  const saveCurrentChat = (msgs: Message[]) => {
    if (store.activeRowId && msgs.length > 0) {
      saveChatHistory(store.activeRowId, msgs);
    }
  };

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
          // Include pending clarification context if we're in a multi-turn flow
          pendingClarification: pendingClarification,
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
                // Clear previous results when starting a new search
                const searchRowId = data?.row_id;
                if (searchRowId) {
                  store.setRowResults(searchRowId, [], undefined, true);
                }
              }
            } else if (eventName === 'row_created') {
              const row = data?.row;
              if (row?.id) {
                // Only preserve chat history if this was a clarification flow completion
                // (pendingClarification was active). Otherwise it's a new unrelated request.
                if (pendingClarification) {
                  const currentMessages = [...messages, { id: assistantMessage.id, role: 'assistant' as const, content: assistantContent }];
                  saveChatHistory(row.id, currentMessages);
                  const rowWithHistory = { ...row, chat_history: JSON.stringify(currentMessages) };
                  const mergedRows = [...store.rows.filter((r) => r.id !== row.id), rowWithHistory];
                  store.setRows(mergedRows);
                } else {
                  // New request - preserve full conversation including user message
                  const currentMessages = [...messages, { id: assistantMessage.id, role: 'assistant' as const, content: assistantContent }];
                  saveChatHistory(row.id, currentMessages);
                  const rowWithHistory = { ...row, chat_history: JSON.stringify(currentMessages) };
                  const mergedRows = [...store.rows.filter((r) => r.id !== row.id), rowWithHistory];
                  store.setRows(mergedRows);
                }
                
                store.setActiveRowId(row.id);
                store.setCurrentQuery(row.title);
                setPendingClarification(null);
                // Update ref so load effect doesn't overwrite
                lastRowIdRef.current = row.id;
              }
            } else if (eventName === 'context_switch') {
              // User switched to completely different topic - new row, fresh chat for new topic
              const row = data?.row;
              if (row?.id) {
                // Start fresh conversation with just the switch message and response
                const lastUserMsg = messages.filter(m => m.role === 'user').pop();
                const freshMessages = lastUserMsg 
                  ? [lastUserMsg, { id: assistantMessage.id, role: 'assistant' as const, content: assistantContent }]
                  : [{ id: assistantMessage.id, role: 'assistant' as const, content: assistantContent }];
                saveChatHistory(row.id, freshMessages);
                const rowWithHistory = { ...row, chat_history: JSON.stringify(freshMessages) };
                const mergedRows = [...store.rows.filter((r) => r.id !== row.id), rowWithHistory];
                store.setRows(mergedRows);
                store.setActiveRowId(row.id);
                store.setCurrentQuery(row.title);
                setMessages(freshMessages);
                setPendingClarification(null);
                lastRowIdRef.current = row.id;
              }
            } else if (eventName === 'row_updated') {
              const row = data?.row;
              if (row?.id) {
                const mergedRows = [...store.rows.filter((r) => r.id !== row.id), row];
                store.setRows(mergedRows);
                store.setActiveRowId(row.id);
                store.setCurrentQuery(row.title);
              }
            } else if (eventName === 'search_results') {
              const rowId = data?.row_id;
              const results = Array.isArray(data?.results) ? data.results : [];
              const providerStatuses = Array.isArray(data?.provider_statuses) ? data.provider_statuses : undefined;
              const moreIncoming = data?.more_incoming ?? false;
              const provider = data?.provider;
              
              if (rowId) {
                if (provider) {
                  // Streaming: append results from this provider
                  store.appendRowResults(rowId, results, providerStatuses, moreIncoming);
                } else {
                  // Non-streaming fallback: replace all
                  store.setRowResults(rowId, results, providerStatuses, moreIncoming);
                }
              }
              if (!moreIncoming) {
                store.setIsSearching(false);
              }
            } else if (eventName === 'vendors_loaded') {
              // Service request - convert vendors to offer-like tiles
              const rowId = data?.row_id;
              const vendors = Array.isArray(data?.vendors) ? data.vendors : [];
              const category = data?.category;
              
              if (rowId && vendors.length > 0) {
                // Convert vendors to offer format for display
                const vendorOffers = vendors.map((v: any, idx: number) => ({
                  id: `vendor-${idx}`,
                  title: v.title || v.vendor_company || v.name || 'Charter Provider',
                  price: null,
                  image_url: v.image_url,
                  item_url: v.url,
                  url: v.url,
                  source: v.source || 'vendor',
                  seller_name: v.vendor_company || v.title,
                  seller_domain: null,
                  is_vendor: true,
                  is_service_provider: true,
                  vendor_id: idx,
                  vendor_category: category,
                  vendor_name: v.vendor_name,
                  vendor_company: v.vendor_company || v.title,
                  vendor_email: v.vendor_email,
                  contact_name: v.vendor_name,
                  contact_email: v.vendor_email,
                  contact_phone: v.contact_phone,
                }));
                store.setRowResults(rowId, vendorOffers, undefined, false);
              }
              // Don't set isSearching=false here - let 'done' event handle it
              // Otherwise RowStrip's auto-refresh triggers before vendor offers propagate
            } else if (eventName === 'needs_clarification') {
              // Store partial constraints for the next turn
              if (data?.type && data?.partial_constraints) {
                setPendingClarification({
                  type: data.type,
                  service_type: data.service_type,
                  title: data.title,
                  partial_constraints: data.partial_constraints,
                });
              }
            } else if (eventName === 'done') {
              store.setIsSearching(false);
              // Clear clarification context if row was created successfully
              // (done event after row_created means we completed the flow)
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
      // Save chat history after stream completes
      setMessages(currentMsgs => {
        saveCurrentChat(currentMsgs);
        return currentMsgs;
      });
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

  const handleLogout = async () => {
    try {
      await logout();
      window.location.href = '/login';
    } catch (err) {
      console.error('Logout failed', err);
      // Force redirect anyway
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
          <div className="text-xs text-onyx-muted hidden sm:block">
            {userEmail || userPhone || 'User'}
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            className="text-xs text-onyx-muted hover:text-agent-blurple"
            title="Sign out"
          >
            <LogOut className="w-4 h-4" />
          </Button>
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
