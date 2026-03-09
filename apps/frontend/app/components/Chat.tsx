'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Bug, FolderPlus } from 'lucide-react';
import { useShoppingStore, mapBidToOffer } from '../store';
import { fetchRowsFromDb, fetchProjectsFromDb, fetchSingleRowFromDb, saveChatHistory, createProjectInDb } from '../utils/api';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { logout, getMe } from '../utils/auth';
import { getAnonymousSessionId } from '../utils/anonymous-session';
import ChatHeader from './ChatHeader';
import ChatMessages, { type Message } from './ChatMessages';
import type { Offer, ProviderStatusSnapshot, Row } from '../store';

type SsePayload = {
  text?: string;
  type?: string;
  row_id?: number;
  row?: Row;
  results?: Offer[];
  provider_statuses?: ProviderStatusSnapshot[];
  more_incoming?: boolean;
  user_message?: string;
  entity_id?: number;
  schema?: Record<string, unknown>;
  version?: number;
  vendors?: Array<Record<string, unknown>>;
  category?: string;
  partial_constraints?: Record<string, unknown>;
  service_type?: string;
  title?: string;
  message?: string;
};

const STARTER_PROMPTS = [
  'What should I treat myself to?',
  'Suggest my next read',
  'What are some good gift ideas for an 8-year-old boy?',
  'What are the best noise-cancelling headphones right now?',
];

export default function Chat() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isTipJarLoading, setIsTipJarLoading] = useState(false);
  const [isProd, setIsProd] = useState(true);
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
  const formRef = useRef<HTMLFormElement>(null);
  const lastRowIdRef = useRef<number | null>(null);
  
  const store = useShoppingStore();
  const activeRowId = store.activeRowId;
  const rows = store.rows;
  const cardClickQuery = store.cardClickQuery;
  const setRows = store.setRows;
  const setProjects = store.setProjects;
  const updateRow = store.updateRow;
  const setCardClickQuery = store.setCardClickQuery;
  const addProject = store.addProject;
  const setTargetProjectId = store.setTargetProjectId;
  const setReportBugModalOpen = store.setReportBugModalOpen;
  const activeRow = rows.find(r => r.id === activeRowId);

  useEffect(() => {
    const hostname = window.location.hostname;
    if (
      hostname === 'localhost' ||
      hostname === '127.0.0.1' ||
      hostname.includes('dev') ||
      hostname.includes('staging')
    ) {
      setIsProd(false);
    } else {
      setIsProd(true);
    }
  }, []);

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
    // Auto-focus the input on mount so the keyboard appears on mobile
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    // Handle "New Request" - clear the chat when activeRowId becomes null
    if (activeRowId === null) {
      setMessages([]);
      setInput('');
      setPendingClarification(null);
      lastRowIdRef.current = null;
      return;
    }

    if (!activeRow) return;
    if (lastRowIdRef.current === activeRowId) return;

    // Save outgoing row's chat before switching
    const outgoingRowId = lastRowIdRef.current;
    if (outgoingRowId) {
      setMessages(currentMsgs => {
        if (currentMsgs.length > 0) {
          saveChatHistory(outgoingRowId, currentMsgs);
          // Defer updateRow to avoid setState-during-render warning
          queueMicrotask(() => {
            updateRow(outgoingRowId, { chat_history: JSON.stringify(currentMsgs) });
          });
        }
        return currentMsgs;
      });
    }

    lastRowIdRef.current = activeRowId;

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
          id: `${Date.now()}-${activeRowId}`,
          role: 'assistant',
          content: `Focused on: ${activeRow.title}`,
        },
      ]);
    }

    // Clear clarification context when switching rows
    setPendingClarification(null);
  }, [activeRowId, activeRow, updateRow]);
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  // Helper to save chat history - called only on stream end, not on every message change
  const saveCurrentChat = (msgs: Message[]) => {
    if (activeRowId && msgs.length > 0) {
      saveChatHistory(activeRowId, msgs);
    }
  };

  // Load rows on mount
  useEffect(() => {
    const loadData = async () => {
      console.log('[Chat] Loading rows on mount...');
      const rows = await fetchRowsFromDb();
      console.log('[Chat] fetchRowsFromDb returned:', rows?.length ?? 'null', 'rows');
      if (rows) {
        setRows(rows);
      }
      const projects = await fetchProjectsFromDb();
      if (projects) {
        setProjects(projects);
      }
    };
    loadData();
  }, [setProjects, setRows]);
  
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
    const intendedProjectId = store.targetProjectId;
    const effectiveActiveRowId = activeRowId;

    let assistantMessageId: string | null = null;
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Anonymous-Session-Id': getAnonymousSessionId(),
        },
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
            let data: unknown = null;
            try {
              data = dataRaw ? JSON.parse(dataRaw) : null;
            } catch {
              data = dataRaw;
            }
            const payload: SsePayload =
              data !== null && typeof data === 'object' && !Array.isArray(data)
                ? (data as SsePayload)
                : {};

            if (eventName === 'assistant_message') {
              assistantContent = typeof payload.text === 'string' ? payload.text : '';
            } else if (eventName === 'action_started') {
              if (payload.type === 'search') {
                store.setIsSearching(true);
                // Mark more results incoming but DON'T clear existing results
                // This prevents the flash where results disappear then reappear
                const searchRowId = typeof payload.row_id === 'number' ? payload.row_id : null;
                if (searchRowId) {
                  store.setMoreResultsIncoming(searchRowId, true);
                }
              } else if (payload.type === 'fetch_vendors') {
                // Service rows: show loading state while fetching vendors
                store.setIsSearching(true);
                const vendorRowId = typeof payload.row_id === 'number' ? payload.row_id : null;
                if (vendorRowId) {
                  store.setMoreResultsIncoming(vendorRowId, true);
                }
              }
            } else if (eventName === 'row_created') {
              const row = payload.row;
              if (row?.id) {
                // Only preserve chat history if this was a clarification flow completion
                // (pendingClarification was active). Otherwise it's a new unrelated request.
                if (pendingClarification) {
                  const currentMessages = [...messages, userMessage, { id: assistantMessage.id, role: 'assistant' as const, content: assistantContent }];
                  saveChatHistory(row.id, currentMessages);
                  const rowWithHistory = { ...row, chat_history: JSON.stringify(currentMessages) };
                  const mergedRows = [...rows.filter((r) => r.id !== row.id), rowWithHistory];
                  setRows(mergedRows);
                } else {
                  // New request — save outgoing row's chat, then start fresh for the new row
                  const outgoingRowId = store.activeRowId;
                  if (outgoingRowId && outgoingRowId !== row.id) {
                    saveChatHistory(outgoingRowId, messages);
                    store.updateRow(outgoingRowId, { chat_history: JSON.stringify(messages) });
                  }
                  const freshMessages = [userMessage, { id: assistantMessage.id, role: 'assistant' as const, content: assistantContent }];
                  saveChatHistory(row.id, freshMessages);
                  const rowWithHistory = { ...row, chat_history: JSON.stringify(freshMessages) };
                  const mergedRows = [...rows.filter((r) => r.id !== row.id), rowWithHistory];
                  setRows(mergedRows);
                  setMessages(freshMessages);
                }
                
                store.setActiveRowId(row.id);
                store.setCurrentQuery(row.title);
                setPendingClarification(null);
                // Update ref so load effect doesn't overwrite
                lastRowIdRef.current = row.id;
              }
            } else if (eventName === 'context_switch') {
              // User switched to completely different topic - new row, fresh chat for new topic
              const row = payload.row;
              if (row?.id) {
                // Save outgoing row's chat before switching
                const outgoingRowId = store.activeRowId;
                if (outgoingRowId && outgoingRowId !== row.id) {
                  saveChatHistory(outgoingRowId, messages);
                  store.updateRow(outgoingRowId, { chat_history: JSON.stringify(messages) });
                }
                // Start fresh conversation with the CURRENT user message (not stale closure)
                // userMessage is the message that triggered this context switch
                const freshMessages = [
                  userMessage,
                  { id: assistantMessage.id, role: 'assistant' as const, content: assistantContent }
                ];
                saveChatHistory(row.id, freshMessages);
                const rowWithHistory = { ...row, chat_history: JSON.stringify(freshMessages) };
                const mergedRows = [...rows.filter((r) => r.id !== row.id), rowWithHistory];
                setRows(mergedRows);
                store.setActiveRowId(row.id);
                store.setCurrentQuery(row.title);
                setMessages(freshMessages);
                setPendingClarification(null);
                lastRowIdRef.current = row.id;
              }
            } else if (eventName === 'row_updated') {
              const row = payload.row;
              const rowId = (typeof row?.id === 'number' ? row.id : null) ?? (typeof payload.row_id === 'number' ? payload.row_id : null);
              if (rowId) {
                // Signal that new results are incoming — but DON'T clear existing results.
                // Old results stay visible until the first search_results batch replaces them.
                store.setMoreResultsIncoming(rowId, true);
                store.setIsSearching(true);
                const updatedRow = row ?? await fetchSingleRowFromDb(rowId);
                if (updatedRow) {
                  const mergedRows = [...rows.filter((r) => r.id !== updatedRow.id), updatedRow];
                  setRows(mergedRows);
                  store.setActiveRowId(updatedRow.id);
                  store.setCurrentQuery(updatedRow.title);
                }
              }
            } else if (eventName === 'factors_updated') {
              const row = payload.row;
              const rowId = (typeof row?.id === 'number' ? row.id : null) ?? (typeof payload.row_id === 'number' ? payload.row_id : null);
              console.log('[Chat] factors_updated event:', { rowId, hasRow: !!row, factorsType: typeof row?.choice_factors, factorsLen: row?.choice_factors?.length });
              if (row) {
                // Merge factors + answers into existing row — preserve local bids/chat_history
                store.updateRow(row.id, {
                  choice_factors: row.choice_factors,
                  choice_answers: row.choice_answers,
                });
                console.log('[Chat] Updated row with factors, choice_factors type:', typeof row.choice_factors);
              } else if (rowId) {
                const freshRow = await fetchSingleRowFromDb(rowId);
                if (freshRow) {
                  store.updateRow(freshRow.id, {
                    choice_factors: freshRow.choice_factors,
                    choice_answers: freshRow.choice_answers,
                  });
                }
              }
            } else if (eventName === 'search_results') {
              const rowId = typeof payload.row_id === 'number' ? payload.row_id : null;
              const results = Array.isArray(payload.results) ? payload.results : [];
              const providerStatuses = Array.isArray(payload.provider_statuses) ? payload.provider_statuses : undefined;
              const moreIncoming = typeof payload.more_incoming === 'boolean' ? payload.more_incoming : false;
              const userMessage = typeof payload.user_message === 'string' ? payload.user_message : undefined;
              if (userMessage && !assistantContent.trim()) {
                assistantContent = userMessage;
              }
              
              if (rowId) {
                // Always append during SSE streaming — never replace.
                // The authoritative DB re-fetch happens on 'done'.
                store.appendRowResults(rowId, results, providerStatuses, moreIncoming, userMessage);
              }
              if (!moreIncoming) {
                store.setIsSearching(false);
              }
            } else if (eventName === 'ui_schema_updated') {
              const entityId = typeof payload.entity_id === 'number' ? payload.entity_id : null;
              const schema = payload.schema;
              if (entityId && schema) {
                store.updateRow(entityId, {
                  ui_schema: schema,
                  ui_schema_version: typeof payload.version === 'number' ? payload.version : 1,
                });
              }
            } else if (eventName === 'vendors_loaded') {
              // Service request - convert vendors to offer-like tiles
              const rowId = typeof payload.row_id === 'number' ? payload.row_id : null;
              const vendors = Array.isArray(payload.vendors) ? payload.vendors : [];
              const category = typeof payload.category === 'string' ? payload.category : undefined;

              if (rowId) {
                // Clear "more results incoming" flag for this row
                store.setMoreResultsIncoming(rowId, false);

                if (vendors.length > 0) {
                  // Convert vendors to offer format for display
                  const vendorOffers: Offer[] = vendors.map((v, idx: number) => ({
                    id: `vendor-${idx}`,
                    title: (typeof v.title === 'string' && v.title) || (typeof v.vendor_company === 'string' && v.vendor_company) || (typeof v.name === 'string' && v.name) || 'Charter Provider',
                    price: null,
                    currency: 'USD',
                    merchant: (typeof v.vendor_company === 'string' && v.vendor_company) || (typeof v.title === 'string' && v.title) || 'Vendor',
                    url: typeof v.url === 'string' ? v.url : '#',
                    image_url: typeof v.image_url === 'string' ? v.image_url : null,
                    rating: null,
                    reviews_count: null,
                    shipping_info: null,
                    source: (typeof v.source === 'string' && v.source) || 'vendor',
                    is_service_provider: true,
                    vendor_category: category,
                    vendor_name: typeof v.vendor_name === 'string' ? v.vendor_name : undefined,
                    vendor_company: (typeof v.vendor_company === 'string' && v.vendor_company) || (typeof v.title === 'string' ? v.title : undefined),
                    vendor_email: typeof v.vendor_email === 'string' ? v.vendor_email : undefined,
                  }));
                  store.setRowResults(rowId, vendorOffers, undefined, false);
                }
              }
              // Don't set isSearching=false here - let 'done' event handle it
              // Otherwise RowStrip's auto-refresh triggers before vendor offers propagate
            } else if (eventName === 'needs_clarification') {
              // Store partial constraints for the next turn
              if (typeof payload.type === 'string' && payload.partial_constraints && typeof payload.partial_constraints === 'object') {
                setPendingClarification({
                  type: payload.type,
                  service_type: typeof payload.service_type === 'string' ? payload.service_type : undefined,
                  title: typeof payload.title === 'string' ? payload.title : undefined,
                  partial_constraints: payload.partial_constraints as Record<string, unknown>,
                });
              }
            } else if (eventName === 'done') {
              store.setIsSearching(false);
              const doneRowId = store.activeRowId;
              if (doneRowId) {
                store.setMoreResultsIncoming(doneRowId, false);
                // Authoritative re-fetch: DB has all persisted, filtered bids.
                // This replaces any stale/mixed results from the SSE stream.
                const freshRow = await fetchSingleRowFromDb(doneRowId);
                if (freshRow && freshRow.bids && freshRow.bids.length > 0) {
                  const offers = freshRow.bids.map(mapBidToOffer);
                  store.setRowResults(doneRowId, offers);
                  store.updateRow(doneRowId, freshRow);
                }
              }
            } else if (eventName === 'error') {
              const msg = typeof payload.message === 'string' ? payload.message : 'Something went wrong.';
              assistantContent = msg;
              store.setIsSearching(false);
              const errorRowId = (typeof payload.row_id === 'number' ? payload.row_id : null) ?? store.activeRowId;
              if (errorRowId) {
                store.setMoreResultsIncoming(errorRowId, false);
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
      // Belt-and-suspenders: force-refetch active row after stream ends
      // to ensure factors/answers are loaded even if SSE events were missed
      const finalRowId = store.activeRowId;
      if (finalRowId) {
        console.log('[Chat] Stream ended, force-refetching row', finalRowId);
        fetchSingleRowFromDb(finalRowId).then(freshRow => {
          if (freshRow) {
            console.log('[Chat] Post-stream refetch got row, factors:', typeof freshRow.choice_factors, freshRow.choice_factors?.length);
            // Don't overwrite chat_history — it was just saved and the backend
            // response may be stale (race between PATCH save and GET fetch)
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            const { chat_history: _, ...rowWithoutChat } = freshRow;
            store.updateRow(freshRow.id, rowWithoutChat);
          }
        }).catch(() => {});
      }
    }
  };
  
  useEffect(() => {
    if (cardClickQuery && !isLoading) {
      setCardClickQuery(null);
      setInput(cardClickQuery);
      // Defer submit so React flushes the input state first
      setTimeout(() => {
        formRef.current?.requestSubmit();
      }, 0);
    }
  }, [cardClickQuery, isLoading, setCardClickQuery]);

  const handleLogout = async () => {
    try {
      await logout();
      window.location.href = '/login?logged_out=1';
    } catch (err) {
      console.error('Logout failed', err);
      window.location.href = '/login?logged_out=1';
    }
  };

  const handleCreateProject = async () => {
    const title = window.prompt('Enter project name:');
    if (!title || !title.trim()) return;

    const newProject = await createProjectInDb(title.trim());
    if (newProject) {
      addProject(newProject);
      setTargetProjectId(newProject.id);
    } else {
      alert('Failed to create project');
    }
  };

  const handleTipJar = async () => {
    if (isTipJarLoading) return;
    setIsTipJarLoading(true);
    try {
      const res = await fetch('/api/tip-jar', { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || 'Failed to create tip jar session');
      if (data?.checkout_url) window.location.href = data.checkout_url;
    } catch (error) {
      console.error('[tip-jar] failed to create session', error);
    } finally {
      setIsTipJarLoading(false);
    }
  };

  const handlePromptSelect = (prompt: string) => {
    if (isLoading) return;
    setInput(prompt);
    inputRef.current?.focus();
    window.setTimeout(() => {
      formRef.current?.requestSubmit();
    }, 0);
  };

  return (
    <div className="flex flex-col h-full bg-warm-light border-r border-warm-grey/70">
      <ChatHeader
        activeRow={activeRow}
        userEmail={userEmail}
        userPhone={userPhone}
        onLogout={handleLogout}
      />

      <div className="lg:hidden px-4 py-2 bg-white border-b border-warm-grey flex items-center gap-2 overflow-x-auto">
        <button
          onClick={handleTipJar}
          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-amber-900 bg-amber-100 rounded-lg hover:bg-amber-200 transition-colors disabled:opacity-60 whitespace-nowrap"
          title="Support our team"
          disabled={isTipJarLoading}
        >
          <span>☕️</span>
          {isTipJarLoading ? 'Opening…' : 'Tip Jar'}
        </button>
        <button
          onClick={handleCreateProject}
          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-accent-blue bg-accent-blue/10 rounded-lg hover:bg-accent-blue/20 transition-colors whitespace-nowrap"
        >
          <FolderPlus size={14} />
          New Project
        </button>
        {!isProd && (
          <button
            onClick={() => setReportBugModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors whitespace-nowrap"
            title="Report Bug"
          >
            <Bug size={14} />
            Report Bug
          </button>
        )}
      </div>

      <ChatMessages
        ref={messagesEndRef}
        messages={messages}
        isLoading={isLoading}
        promptSuggestions={STARTER_PROMPTS}
        onPromptSelect={handlePromptSelect}
      />

      <div className="px-6 py-5 bg-white border-t border-warm-grey">
        <form ref={formRef} onSubmit={handleSubmit} className="flex gap-3 items-end">
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={activeRow ? `Refine "${activeRow.title}"...` : "Ask Annie a question..."}
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
