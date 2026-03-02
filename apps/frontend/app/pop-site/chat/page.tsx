'use client';

import { useState, useRef, useEffect, useCallback, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { DynamicRenderer } from '../../components/sdui/DynamicRenderer';

const LS_ITEMS_KEY = 'pop_guest_list_items';
const LS_GUEST_PROJECT_KEY = 'pop_guest_project_id';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

interface Deal {
  id: number;
  title: string;
  price: number;
  source: string;
  url: string;
  image_url: string | null;
  is_selected: boolean;
}

interface ListItem {
  id: number;
  title: string;
  status: string;
  deals?: Deal[];
  lowest_price?: number | null;
  deal_count?: number;
  ui_schema?: Record<string, unknown> | null;
}

function PopChatInner() {
  const searchParams = useSearchParams();
  const sharedListId = searchParams.get('list');
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        "Hey! I'm Pop, your grocery savings assistant. Tell me what you need from the store and I'll find the best deals for you. Try something like \"I need milk, eggs, and bread\".",
    },
  ]);
  const [listItems, setListItems] = useState<ListItem[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [projectTitle, setProjectTitle] = useState<string>('My Shopping List');
  const [allProjects, setAllProjects] = useState<{id: number, title: string}[]>([]);
  const [showProjectMenu, setShowProjectMenu] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState('');
  const [expandedItemId, setExpandedItemId] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const editInputRef = useRef<HTMLInputElement>(null);
  const isCommittingRef = useRef(false);

  const handleDuplicateProject = async () => {
    if (!projectId || !isLoggedIn) return;
    try {
      const res = await fetch(`/api/pop/list/${projectId}/duplicate`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setProjectId(data.project_id);
        setProjectTitle(data.title);
        // refresh items
        const listRes = await fetch(`/api/pop/my-list?project_id=${data.project_id}`);
        if (listRes.ok) {
          const listData = await listRes.json();
          setListItems(listData.items || []);
        }
        // refresh all projects
        const listsRes = await fetch('/api/pop/lists');
        if (listsRes.ok) {
          setAllProjects(await listsRes.json());
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSwitchProject = async (id: number) => {
    setShowProjectMenu(false);
    try {
      const listRes = await fetch(`/api/pop/my-list?project_id=${id}`);
      if (listRes.ok) {
        const listData = await listRes.json();
        setProjectId(listData.project_id);
        setProjectTitle(listData.title || 'My Shopping List');
        setListItems(listData.items || []);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateProject = async () => {
    setShowProjectMenu(false);
    const title = window.prompt("Enter new list name:");
    if (!title || !title.trim()) return;
    try {
      const res = await fetch('/api/pop/lists', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title.trim() })
      });
      if (res.ok) {
        const data = await res.json();
        setProjectId(data.project_id);
        setProjectTitle(data.title);
        setListItems([]);
        const listsRes = await fetch('/api/pop/lists');
        if (listsRes.ok) {
          setAllProjects(await listsRes.json());
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (editingId !== null) editInputRef.current?.focus();
  }, [editingId]);

  // On mount: try to load list from DB (logged-in) or localStorage (guest)
  useEffect(() => {
    async function loadInitialList() {
      try {
        // If a shared list ID is provided, load that list directly
        if (sharedListId) {
          const sharedRes = await fetch(`/api/pop/list/${sharedListId}`);
          if (sharedRes.ok) {
            const data = await sharedRes.json();
            setIsLoggedIn(true);
            setProjectId(data.project_id);
            if (data.items?.length > 0) setListItems(data.items);
            return;
          }
        }
        const res = await fetch('/api/pop/my-list');
        if (res.ok) {
          const data = await res.json();
          setIsLoggedIn(true);
          if (data.project_id) {
            setProjectId(data.project_id);
            if (data.items?.length > 0) setListItems(data.items);
          }
          return;
        }
        // Only fall through to localStorage when explicitly not authenticated.
        // Any other error (500, 503) should not silently drop to guest mode.
        if (res.status !== 401) return;
      } catch {
        // Network error — stay in guest mode
      }
      // Guest: restore from localStorage
      try {
        const raw = localStorage.getItem(LS_ITEMS_KEY);
        if (raw) {
          const saved: ListItem[] = JSON.parse(raw);
          if (saved.length > 0) setListItems(saved);
        }
        const savedProjectId = localStorage.getItem(LS_GUEST_PROJECT_KEY);
        if (savedProjectId) setProjectId(Number(savedProjectId));
      } catch {
        // ignore
      }
    }
    loadInitialList();
  }, [sharedListId]);

  // Persist guest items + project_id to localStorage whenever they change
  useEffect(() => {
    if (!isLoggedIn) {
      if (listItems.length > 0) localStorage.setItem(LS_ITEMS_KEY, JSON.stringify(listItems));
      if (projectId) localStorage.setItem(LS_GUEST_PROJECT_KEY, String(projectId));
    }
  }, [listItems, isLoggedIn, projectId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || isLoading) return;

    const userMsg: Message = { id: `user-${Date.now()}`, role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    const guestProjectId = !isLoggedIn
      ? projectId ?? (localStorage.getItem(LS_GUEST_PROJECT_KEY) ? Number(localStorage.getItem(LS_GUEST_PROJECT_KEY)) : null)
      : null;

    try {
      const res = await fetch('/api/pop/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, ...(guestProjectId ? { guest_project_id: guestProjectId } : {}) }),
      });
      const data = await res.json();

      setMessages((prev) => [
        ...prev,
        { id: `asst-${Date.now()}`, role: 'assistant', content: data.reply || 'Got it!' },
      ]);

      if (data.list_items?.length > 0) setListItems(data.list_items);
      if (data.project_id) setProjectId(data.project_id);
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: `err-${Date.now()}`, role: 'assistant', content: 'Oops, something went wrong. Try again!' },
      ]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleDeleteItem = useCallback(async (item: ListItem) => {
    if (isLoggedIn) {
      await fetch(`/api/pop/item/${item.id}`, { method: 'DELETE' });
    }
    setListItems((prev) => {
      const next = prev.filter((i) => i.id !== item.id);
      if (!isLoggedIn) localStorage.setItem(LS_ITEMS_KEY, JSON.stringify(next));
      return next;
    });
  }, [isLoggedIn]);

  const startEdit = (item: ListItem) => {
    setEditingId(item.id);
    setEditValue(item.title);
  };

  const commitEdit = useCallback(async (item: ListItem) => {
    if (isCommittingRef.current) return;
    const newTitle = editValue.trim();
    if (!newTitle || newTitle === item.title) {
      setEditingId(null);
      return;
    }
    isCommittingRef.current = true;
    setEditingId(null);
    try {
      if (isLoggedIn) {
        await fetch(`/api/pop/item/${item.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: newTitle }),
        });
      }
      setListItems((prev) => {
        const next = prev.map((i) => (i.id === item.id ? { ...i, title: newTitle } : i));
        if (!isLoggedIn) localStorage.setItem(LS_ITEMS_KEY, JSON.stringify(next));
        return next;
      });
    } finally {
      isCommittingRef.current = false;
    }
  }, [editValue, isLoggedIn]);

  const handleClaimDeal = useCallback(async (itemId: number, dealId: number) => {
    try {
      await fetch(`/api/pop/offer/${dealId}/claim`, { method: 'POST' });
      setListItems((prev) =>
        prev.map((item) => {
          if (item.id !== itemId || !item.deals) return item;
          return {
            ...item,
            deals: item.deals.map((d) => ({
              ...d,
              is_selected: d.id === dealId,
            })),
          };
        })
      );
    } catch {
      // ignore
    }
  }, []);

  const sourceLabel = (source: string): string => {
    const map: Record<string, string> = {
      kroger: 'Kroger',
      rainforest_amazon: 'Amazon',
      ebay_browse: 'eBay',
      searchapi_google_shopping: 'Google',
    };
    return map[source] || source;
  };

  const sourceColor = (source: string): string => {
    const map: Record<string, string> = {
      kroger: 'bg-blue-100 text-blue-700',
      rainforest_amazon: 'bg-orange-100 text-orange-700',
      ebay_browse: 'bg-red-100 text-red-700',
      searchapi_google_shopping: 'bg-emerald-100 text-emerald-700',
    };
    return map[source] || 'bg-gray-100 text-gray-700';
  };

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <Image src="/pop-avatar.png" alt="Pop" width={32} height={32} className="rounded-full" />
            <span className="text-lg font-bold text-green-700">Pop</span>
          </Link>
          <div className="flex items-center gap-3">
            <a
              href="https://buy.stripe.com/test_dRm5kEcSC6lWc0NeUh1ck00"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs flex items-center gap-1.5 px-2 py-1 rounded-full bg-green-50 text-green-700 hover:bg-green-100 transition-colors mr-2"
            >
              <span>☕️</span> Tip Jar
            </a>
            {listItems.length > 0 && (
              <Link
                href={projectId ? `/list/${projectId}` : '#'}
                className="text-xs bg-green-100 text-green-800 px-2.5 py-1 rounded-full font-medium hover:bg-green-200 transition-colors"
              >
                {listItems.length} item{listItems.length !== 1 ? 's' : ''} on list →
              </Link>
            )}
            <Link
              href="/login"
              className="text-sm text-gray-500 hover:text-green-700 transition-colors"
            >
              {isLoggedIn ? 'My Account' : 'Sign In'}
            </Link>
          </div>
        </div>
      </nav>

      <div className="flex-1 flex flex-col lg:flex-row max-w-6xl mx-auto w-full">
        {/* Chat Panel */}
        <div className="flex-1 flex flex-col min-h-0">
          <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex items-end gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'assistant' && (
                  <Image src="/pop-avatar.png" alt="Pop" width={28} height={28} className="rounded-full flex-shrink-0 mb-1" />
                )}
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                    msg.role === 'user' ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex items-end gap-2 justify-start">
                <Image src="/pop-avatar.png" alt="Pop" width={28} height={28} className="rounded-full flex-shrink-0 mb-1" />
                <div className="bg-gray-100 rounded-2xl px-4 py-3">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-green-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 bg-green-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-green-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="border-t border-gray-100 bg-white p-4">
            <form onSubmit={handleSubmit} className="flex gap-3 max-w-2xl mx-auto">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="What do you need from the store?"
                disabled={isLoading}
                className="flex-1 px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm text-gray-900 placeholder-gray-400 disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={isLoading || !input.trim()}
                className="bg-green-600 text-white px-5 py-3 rounded-xl hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm"
              >
                Send
              </button>
            </form>
            <p className="text-center text-xs text-gray-400 mt-2">
              Pop finds deals on groceries. Try: &quot;eggs, butter, and whole wheat bread&quot;
            </p>
          </div>
        </div>

        {/* List Sidebar */}
        {(listItems.length > 0 || isLoggedIn) && (
          <div className="lg:w-96 border-t lg:border-t-0 lg:border-l border-gray-100 bg-gray-50/50 p-4 flex flex-col h-[calc(100vh-56px)]">
            <div className="flex items-center justify-between mb-3 relative flex-shrink-0">
              <button 
                onClick={() => isLoggedIn && setShowProjectMenu(!showProjectMenu)}
                className={`flex items-center gap-2 text-sm font-semibold text-gray-900 ${isLoggedIn ? 'hover:bg-gray-200 px-2 py-1 rounded -ml-2' : ''}`}
              >
                <span>🛒</span> {projectTitle}
                {isLoggedIn && (
                  <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                )}
              </button>
              
              {showProjectMenu && isLoggedIn && (
                <div className="absolute top-full left-0 mt-1 w-48 bg-white rounded-xl shadow-lg border border-gray-100 py-1 z-50">
                  <div className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wide border-b border-gray-100">
                    Your Lists
                  </div>
                  {allProjects.map(p => (
                    <button
                      key={p.id}
                      onClick={() => handleSwitchProject(p.id)}
                      className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-50 flex items-center justify-between ${p.id === projectId ? 'text-green-700 font-medium bg-green-50/50' : 'text-gray-700'}`}
                    >
                      <span className="truncate">{p.title}</span>
                      {p.id === projectId && <span className="text-green-500">✓</span>}
                    </button>
                  ))}
                  <div className="border-t border-gray-100 mt-1">
                    <button
                      onClick={handleCreateProject}
                      className="w-full text-left px-4 py-2 text-sm text-green-700 hover:bg-green-50 flex items-center gap-2 font-medium"
                    >
                      <span className="text-lg leading-none">+</span> New List
                    </button>
                  </div>
                </div>
              )}

              <div className="flex items-center gap-2">
                {isLoggedIn && projectId && (
                  <button
                    onClick={handleDuplicateProject}
                    className="p-1.5 text-gray-400 hover:text-green-600 rounded hover:bg-green-50 transition-colors"
                    title="Duplicate List"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                  </button>
                )}
                {projectId && (
                  <Link
                    href={`/pop-site/list/${projectId}`}
                    className="text-xs text-green-600 hover:text-green-700 font-medium flex items-center gap-1"
                  >
                    View Full <span className="hidden sm:inline">List</span> →
                  </Link>
                )}
              </div>
            </div>
            
            <div className="flex-1 overflow-y-auto -mx-4 px-4 pb-4">
              {listItems.length === 0 ? (
                <div className="text-center py-12 text-gray-400">
                  <span className="text-4xl block mb-3">🛒</span>
                  <p className="text-sm">List is empty.</p>
                  <p className="text-xs mt-1">Tell Pop what you need!</p>
                </div>
              ) : (
                <>
                  <ul className="space-y-3">
                    {listItems.map((item) => {
                      const isExpanded = expandedItemId === item.id;
                      const selectedDeal = item.deals?.find((d) => d.is_selected);
                      const hasDealChoices = (item.deal_count ?? 0) > 0;

                      return (
                        <li key={item.id} className="bg-white rounded-xl shadow-sm overflow-hidden">
                          {/* Item header */}
                          <div className="group flex items-center gap-2 px-3 py-2.5">
                            <button
                              className={`w-5 h-5 rounded-full border-2 flex-shrink-0 flex items-center justify-center transition-colors ${
                                selectedDeal ? 'bg-green-500 border-green-500' : 'border-gray-300'
                              }`}
                              title={selectedDeal ? 'Deal picked' : 'No deal picked yet'}
                              onClick={() => hasDealChoices && setExpandedItemId(isExpanded ? null : item.id)}
                            >
                              {selectedDeal && (
                                <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                </svg>
                              )}
                            </button>

                            {editingId === item.id ? (
                              <input
                                ref={editInputRef}
                                value={editValue}
                                onChange={(e) => setEditValue(e.target.value)}
                                onBlur={() => commitEdit(item)}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') commitEdit(item);
                                  if (e.key === 'Escape') setEditingId(null);
                                }}
                                className="flex-1 text-sm text-gray-900 border-b border-green-400 outline-none bg-transparent"
                              />
                            ) : (
                              <button
                                className="flex-1 text-left min-w-0"
                                onClick={() => hasDealChoices ? setExpandedItemId(isExpanded ? null : item.id) : startEdit(item)}
                              >
                                <span className="text-sm font-medium text-gray-900 truncate block">{item.title}</span>
                                {hasDealChoices && (
                                  <span className="text-xs text-gray-500">
                                    {item.deal_count} deal{item.deal_count !== 1 ? 's' : ''}
                                    {item.lowest_price != null && ` from $${item.lowest_price.toFixed(2)}`}
                                  </span>
                                )}
                                {!hasDealChoices && (
                                  <span className="text-xs text-gray-400 italic">Searching for deals...</span>
                                )}
                              </button>
                            )}

                            <div className="flex items-center gap-1 flex-shrink-0">
                              {hasDealChoices && (
                                <button
                                  onClick={() => setExpandedItemId(isExpanded ? null : item.id)}
                                  className="p-1 text-gray-400 hover:text-green-600 transition-colors"
                                  title="Show deals"
                                >
                                  <svg className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                                  </svg>
                                </button>
                              )}
                              <button
                                onClick={() => handleDeleteItem(item)}
                                className="opacity-0 group-hover:opacity-100 transition-opacity p-1 text-gray-300 hover:text-red-400"
                                title="Remove item"
                              >
                                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                                </svg>
                              </button>
                            </div>
                          </div>

                          {/* Expanded Content: SDUI + Legacy deal choices */}
                          {isExpanded && (
                            <div className="border-t border-gray-100 px-3 py-2 space-y-3 max-h-[400px] overflow-y-auto">
                              {item.ui_schema && (
                                <div className="mb-2">
                                  <DynamicRenderer
                                    schema={item.ui_schema}
                                    fallbackTitle={item.title}
                                    fallbackStatus={item.status}
                                  />
                                </div>
                              )}

                              {item.deals && item.deals.length > 0 && (
                                <div className="space-y-2">
                                  {item.deals.map((deal) => (
                                    <button
                                      key={deal.id}
                                      onClick={() => handleClaimDeal(item.id, deal.id)}
                                      className={`w-full flex items-center gap-2.5 p-2 rounded-lg text-left transition-colors ${
                                        deal.is_selected
                                          ? 'bg-green-50 ring-1 ring-green-300'
                                          : 'hover:bg-gray-50'
                                      }`}
                                    >
                                      {deal.image_url ? (
                                        // eslint-disable-next-line @next/next/no-img-element
                                        <img
                                          src={deal.image_url}
                                          alt={deal.title}
                                          className="w-10 h-10 rounded-md object-cover flex-shrink-0 bg-gray-100"
                                        />
                                      ) : (
                                        <div className="w-10 h-10 rounded-md bg-gray-100 flex-shrink-0 flex items-center justify-center">
                                          <svg className="w-5 h-5 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                          </svg>
                                        </div>
                                      )}
                                      <div className="flex-1 min-w-0">
                                        <p className="text-xs text-gray-800 truncate">{deal.title}</p>
                                        <div className="flex items-center gap-1.5 mt-0.5">
                                          <span className="text-sm font-semibold text-gray-900">${deal.price.toFixed(2)}</span>
                                          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${sourceColor(deal.source)}`}>
                                            {sourceLabel(deal.source)}
                                          </span>
                                        </div>
                                      </div>
                                      {deal.is_selected && (
                                        <svg className="w-5 h-5 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                        </svg>
                                      )}
                                    </button>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}

                          {/* Selected deal summary (collapsed) */}
                          {!isExpanded && selectedDeal && (
                            <div className="border-t border-gray-100 px-3 py-1.5 flex items-center gap-2">
                              <span className="text-xs text-green-700 font-medium">${selectedDeal.price.toFixed(2)}</span>
                              <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${sourceColor(selectedDeal.source)}`}>
                                {sourceLabel(selectedDeal.source)}
                              </span>
                            </div>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                  {!isLoggedIn && (
                    <p className="mt-3 text-xs text-gray-400 text-center">
                      <Link href="/login" className="text-green-600 hover:underline">Sign in</Link> to save your list permanently
                    </p>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function PopChatPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-white flex items-center justify-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600" /></div>}>
      <PopChatInner />
    </Suspense>
  );
}
