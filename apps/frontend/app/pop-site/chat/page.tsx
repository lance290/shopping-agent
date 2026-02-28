'use client';

import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

interface ListItem {
  id: number;
  title: string;
  status: string;
}

export default function PopChatPage() {
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
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || isLoading) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch('/api/pop/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();

      const assistantMsg: Message = {
        id: `asst-${Date.now()}`,
        role: 'assistant',
        content: data.reply || 'Got it!',
      };
      setMessages((prev) => [...prev, assistantMsg]);

      if (data.list_items?.length > 0) {
        setListItems(data.list_items);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: 'Oops, something went wrong. Try again!',
        },
      ]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
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
            {listItems.length > 0 && (
              <span className="text-xs bg-green-100 text-green-800 px-2.5 py-1 rounded-full font-medium">
                {listItems.length} item{listItems.length !== 1 ? 's' : ''} on list
              </span>
            )}
            <Link
              href="/login"
              className="text-sm text-gray-500 hover:text-green-700 transition-colors"
            >
              Sign In
            </Link>
          </div>
        </div>
      </nav>

      <div className="flex-1 flex flex-col lg:flex-row max-w-6xl mx-auto w-full">
        {/* Chat Panel */}
        <div className="flex-1 flex flex-col min-h-0">
          {/* Messages */}
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
                    msg.role === 'user'
                      ? 'bg-green-600 text-white'
                      : 'bg-gray-100 text-gray-900'
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

          {/* Input */}
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

        {/* List Sidebar (visible when items exist) */}
        {listItems.length > 0 && (
          <div className="lg:w-80 border-t lg:border-t-0 lg:border-l border-gray-100 bg-gray-50/50 p-4 overflow-y-auto">
            <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <span>🛒</span> Your List
            </h3>
            <ul className="space-y-2">
              {listItems.map((item) => (
                <li
                  key={item.id}
                  className="flex items-center gap-3 bg-white rounded-xl px-3 py-2.5 shadow-sm"
                >
                  <div
                    className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                      item.status === 'bought'
                        ? 'bg-green-500 border-green-500'
                        : 'border-gray-300'
                    }`}
                  >
                    {item.status === 'bought' && (
                      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                  <span className={`text-sm ${item.status === 'bought' ? 'line-through text-gray-400' : 'text-gray-900'}`}>
                    {item.title}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
