'use client';

import { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';
import { useShoppingStore, mapBidToOffer } from '../store';
import { fetchRowsFromDb, fetchProjectsFromDb, fetchSingleRowFromDb, saveChatHistory } from '../utils/api';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { logout, getMe } from '../utils/auth';
import ChatHeader from './ChatHeader';
import ChatMessages, { type Message } from './ChatMessages';

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
    // Auto-focus the input on mount so the keyboard appears on mobile
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    // Handle "New Request" - clear the chat when activeRowId becomes null
    if (store.activeRowId === null) {
      setMessages([]);
      setInput('');
      setPendingClarification(null);
      lastRowIdRef.current = null;
      return;
    }

    if (!activeRow) return;
    if (lastRowIdRef.current === store.activeRowId) return;

    // Save outgoing row's chat before switching
    const outgoingRowId = lastRowIdRef.current;
    if (outgoingRowId) {
      setMessages(currentMsgs => {
        if (currentMsgs.length > 0) {
          saveChatHistory(outgoingRowId, currentMsgs);
          // Defer updateRow to avoid setState-during-render warning
          queueMicrotask(() => {
            store.updateRow(outgoingRowId, { chat_history: JSON.stringify(currentMsgs) });
          });
        }
        return currentMsgs;
      });
    }

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
      console.log('[Chat] Loading rows on mount...');
      const rows = await fetchRowsFromDb();
      console.log('[Chat] fetchRowsFromDb returned:', rows?.length ?? 'null', 'rows');
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
  
  // handleSubmit and other logic extracted to ChatHandlers.ts
  const handleSubmit = (e: React.FormEvent) => {
    // ...
  };

  return (
    <div>
      <ChatHeader activeRow={activeRow} userEmail={userEmail} userPhone={userPhone} onLogout={handleLogout} />
      <ChatMessages ref={messagesEndRef} messages={messages} isLoading={isLoading} />
      {/* ... form ... */}
    </div>
  );
}
