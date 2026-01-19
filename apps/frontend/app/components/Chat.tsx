'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User } from 'lucide-react';
import { useShoppingStore } from '../store';
import { persistRowToDb, runSearchApi, createRowInDb, fetchRowsFromDb } from '../utils/api';

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
  const activeRow = store.rows.find(r => r.id === store.activeRowId);
  
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

  /**
   * MAIN FLOW:
   * 1a. User types in search
   * 1b. A search query is created and saved to Zustand
   * 1c. A card is either selected if possible or created
   * 1d. Zustand is updated as source of truth
   * 1e. We update the database with the query
   * 1f. We run the search
   */
  const handleSearchFlow = async (query: string) => {
    console.log('[Chat] === SEARCH FLOW START ===');
    console.log('[Chat] 1a. Query:', query);

    store.setCurrentQuery(query);

    // 1c. Select or create card
    const currentRows = store.rows;
    let targetRow = store.selectOrCreateRow(query, currentRows);
    
    if (targetRow) {
      // Select existing row
      console.log('[Chat] Step 2. Identifying existing row:', targetRow.id, targetRow.title);
      store.setActiveRowId(targetRow.id);
      
      // Update title if needed
      if (targetRow.title !== query) {
        store.updateRow(targetRow.id, { title: query });
        await persistRowToDb(targetRow.id, query);
      }
    } else {
      // Refresh from DB (LLM might have created it)
      console.log('[Chat] 1c. No matching row in store, refreshing from DB...');
      const freshRows = await fetchRowsFromDb();
      store.setRows(freshRows);
      
      targetRow = freshRows.find(r => r.title === query) || null;
      if (!targetRow && freshRows.length > 0) {
        // Fallback to newest
        targetRow = freshRows[freshRows.length - 1];
      }
      
      if (targetRow) {
        store.setActiveRowId(targetRow.id);
      }
    }

    // 1f. Run the search
    if (targetRow) {
      store.setIsSearching(true);
      const results = await runSearchApi(query, targetRow.id);
      store.setRowResults(targetRow.id, results);
    }

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
          
          // --- Stream Parsing (Phase 1 Refactor: Cleaned up but logic preserved) ---
          
          // 1. Row Creation
          const rowMatch = assistantContent.match(/✅ Adding "([^"]+)" to your procurement board/);
          if (rowMatch && !rowCreationHandled) {
            rowCreationHandled = true;
            const createdItemName = rowMatch[1];
            // Wait for DB commit
            await new Promise(resolve => setTimeout(resolve, 800));
            const freshRows = await fetchRowsFromDb();
            store.setRows(freshRows);
            
            if (freshRows.length > 0) {
              const newestRow = freshRows[freshRows.length - 1];
              store.setActiveRowId(newestRow.id);
              // Trigger search
              const results = await runSearchApi(newestRow.title, newestRow.id);
              store.setRowResults(newestRow.id, results);
            }
          }
          
          // 2. Row Update
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
          
          // 3. Explicit Search
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
  
  // Handle when a card is clicked (called from Board via store)
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
    <div className="flex flex-col h-full border-r border-gray-200 bg-gray-50 w-1/3 min-w-[350px] shrink-0">
      <div className="p-4 border-b border-gray-200 bg-white shadow-sm">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Bot className="w-5 h-5 text-blue-600" />
          Shopping Agent
        </h2>
        {activeRow && (
          <div className="text-xs text-gray-500 mt-1 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-500"></span>
            Active: <span className="font-medium text-gray-700 truncate max-w-[200px]">{activeRow.title}</span>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-10">
            <p>Hello! I can help you find items and manage your procurement list.</p>
            <p className="text-sm mt-2 text-gray-400">Try "I need a blue hoodie under $50"</p>
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
                m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-green-100 text-green-600'
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
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-white border-t border-gray-200">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            className="flex-1 p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-black text-sm"
            value={input}
            placeholder={activeRow ? `Refine "${activeRow.title}"...` : "What are you looking for?"}
            onChange={(e) => setInput(e.target.value)}
          />
          <button
            type="submit"
            disabled={isLoading || !input?.trim()}
            className="bg-blue-600 text-white p-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}
