'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User } from 'lucide-react';
import { useShoppingStore, Row } from '../store';

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
  
  const store = useShoppingStore();
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Helper: Persist row to database
  const persistRowToDb = async (rowId: number, title: string) => {
    console.log('[Chat] Persisting to DB:', rowId, title);
    try {
      const res = await fetch(`/api/rows?id=${rowId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      });
      if (res.ok) {
        console.log('[Chat] DB persist success');
        return true;
      } else {
        console.error('[Chat] DB persist failed:', res.status);
        return false;
      }
    } catch (err) {
      console.error('[Chat] DB persist error:', err);
      return false;
    }
  };

  // Helper: Run search and update store
  const runSearch = async (query: string) => {
    console.log('[Chat] Running search:', query);
    store.setIsSearching(true);
    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      const data = await res.json();
      console.log('[Chat] Search returned:', data.results?.length || 0, 'products');
      store.setSearchResults(data.results || []);
    } catch (err) {
      console.error('[Chat] Search error:', err);
      store.setSearchResults([]);
    }
  };

  // Helper: Create a new row in database
  const createRowInDb = async (title: string): Promise<Row | null> => {
    console.log('[Chat] Creating row in DB:', title);
    try {
      const res = await fetch('/api/rows', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          title, 
          status: 'sourcing',
          request_spec: {
            item_name: title,
            constraints: '{}'
          }
        }),
      });
      if (res.ok) {
        const newRow = await res.json();
        console.log('[Chat] Row created:', newRow);
        return newRow;
      } else {
        console.error('[Chat] Create row failed:', res.status, await res.text());
      }
    } catch (err) {
      console.error('[Chat] Create row error:', err);
    }
    return null;
  };

  // Helper: Fetch all rows from DB
  const fetchRowsFromDb = async (): Promise<Row[]> => {
    try {
      const res = await fetch('/api/rows');
      if (res.ok) {
        const rows = await res.json();
        return Array.isArray(rows) ? rows : [];
      }
    } catch (err) {
      console.error('[Chat] Fetch rows error:', err);
    }
    return [];
  };

  /**
   * MAIN FLOW:
   * 1a. User types in search
   * 1b. A search query is created and saved to Zustand
   * 1c. A card is either selected if possible or created
   * 1d. Zustand is updated as source of truth
   * 1e. We update the database with the query
   * 1f. We run the search
   * 1g. We save the source of truth to the database
   */
  const handleSearchFlow = async (query: string) => {
    console.log('[Chat] === SEARCH FLOW START ===');
    console.log('[Chat] 1a. Query:', query);

    // 1b. Save query to Zustand
    store.setCurrentQuery(query);
    console.log('[Chat] 1b. Query saved to Zustand');

    // 1c. Select or create card
    const currentRows = store.rows;
    let targetRow = store.selectOrCreateRow(query, currentRows);
    
    if (targetRow) {
      // Select existing row - This is Step 2: extending the search
      console.log('[Chat] Step 2. Identifying existing row for extension:', targetRow.id, targetRow.title);
      store.setActiveRowId(targetRow.id);
      
      // Update the row title in Zustand and DB to reflect the extended query
      if (targetRow.title !== query) {
        console.log('[Chat] 1e. Updating existing row title:', query);
        store.updateRow(targetRow.id, { title: query });
        await persistRowToDb(targetRow.id, query);
      }
    } else {
      // No matching row in store - refresh from DB first (LLM may have created it)
      console.log('[Chat] 1c. No matching row in store, refreshing from DB...');
      const freshRows = await fetchRowsFromDb();
      console.log('[Chat] Fetched rows from DB:', freshRows.length);
      store.setRows(freshRows);
      
      // Check again after refresh
      targetRow = freshRows.find(r => r.title === query) || null;
      if (targetRow) {
        console.log('[Chat] Found row after refresh:', targetRow.id, targetRow.title);
        store.setActiveRowId(targetRow.id);
      } else if (freshRows.length > 0) {
        // Select the newest row (likely the one just created by LLM)
        const newestRow = freshRows[freshRows.length - 1];
        console.log('[Chat] Selecting newest row:', newestRow.id, newestRow.title);
        store.setActiveRowId(newestRow.id);
        targetRow = newestRow;
      }
    }

    // 1d. Zustand is already the source of truth
    console.log('[Chat] 1d. Zustand updated - activeRowId:', store.activeRowId);

    // 1f. Run the search
    await runSearch(query);
    console.log('[Chat] 1f. Search complete');

    console.log('[Chat] === SEARCH FLOW END ===');
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
          
          // Parse search events from the stream - this is a NEW search
          const searchMatch = assistantContent.match(/🔍 Searching for "([^"]+)"/);
          if (searchMatch && searchMatch[1] !== lastProcessedQuery) {
            lastProcessedQuery = searchMatch[1];
            // Execute the full search flow
            await handleSearchFlow(lastProcessedQuery);
          }
          
          // Parse row creation from stream (only handle once)
          const rowMatch = assistantContent.match(/✅ Adding "([^"]+)" to your procurement board/);
          if (rowMatch && !rowCreationHandled) {
            rowCreationHandled = true;
            console.log('[Chat] Row creation detected in stream:', rowMatch[1]);
            // Wait a moment for the backend to commit the row
            await new Promise(resolve => setTimeout(resolve, 500));
            // Refresh rows from DB to ensure we have the latest
            const freshRows = await fetchRowsFromDb();
            console.log('[Chat] Fetched fresh rows:', freshRows.length, freshRows);
            store.setRows(freshRows);
            // Select the newest row
            if (freshRows.length > 0) {
              const newestRow = freshRows[freshRows.length - 1];
              store.setActiveRowId(newestRow.id);
              console.log('[Chat] Set active row:', newestRow.id, newestRow.title);
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
      setIsLoading(false);
    }
  };
  
  // Handle when a card is clicked (called from Board via store)
  // This appends the card's query to the chat
  useEffect(() => {
    const cardClickQuery = store.cardClickQuery;
    
    if (cardClickQuery) {
      console.log('[Chat] Card clicked - Appending to chat:', cardClickQuery);
      const cardMessage: Message = {
        id: Date.now().toString(),
        role: 'user',
        content: cardClickQuery,
      };
      setMessages(prev => [...prev, cardMessage]);
      // Clear the trigger so it doesn't fire again
      store.setCardClickQuery(null);
    }
  }, [store.cardClickQuery]);

  return (
    <div className="flex flex-col h-full border-r border-gray-200 bg-gray-50 w-1/3 min-w-[300px]">
      <div className="p-4 border-b border-gray-200 bg-white shadow-sm">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Bot className="w-5 h-5 text-blue-600" />
          Shopping Agent
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-10">
            <p>Hello! I can help you find items and manage your procurement list.</p>
            <p className="text-sm mt-2">Try "I need a blue hoodie under $50"</p>
          </div>
        )}
        
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex gap-3 ${
              m.role === 'user' ? 'flex-row-reverse' : ''
            }`}
          >
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                m.role === 'user' ? 'bg-blue-100 text-blue-600' : 'bg-green-100 text-green-600'
              }`}
            >
              {m.role === 'user' ? <User size={16} /> : <Bot size={16} />}
            </div>
            
            <div
              className={`rounded-lg p-3 max-w-[85%] text-sm whitespace-pre-wrap ${
                m.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white border border-gray-200 text-gray-800 shadow-sm'
              }`}
            >
              {m.content || (m.role === 'assistant' && isLoading ? '...' : '')}
            </div>
          </div>
        ))}
        {isLoading && messages[messages.length - 1]?.role === 'user' && (
            <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-green-100 text-green-600 flex items-center justify-center shrink-0">
                    <Bot size={16} />
                </div>
                <div className="bg-white border border-gray-200 rounded-lg p-3 shadow-sm">
                    <span className="animate-pulse">Thinking...</span>
                </div>
            </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-white border-t border-gray-200">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            className="flex-1 p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-black"
            value={input}
            placeholder="What are you looking for?"
            onChange={(e) => setInput(e.target.value)}
          />
          <button
            type="submit"
            disabled={isLoading || !input?.trim()}
            className="bg-blue-600 text-white p-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send size={20} />
          </button>
        </form>
      </div>
    </div>
  );
}
