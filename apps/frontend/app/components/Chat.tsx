'use client';

import { useChat } from 'ai/react';
import { Send, Bot, User } from 'lucide-react';

export default function Chat() {
  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: '/api/chat',
  });

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
              className={`rounded-lg p-3 max-w-[85%] text-sm ${
                m.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white border border-gray-200 text-gray-800 shadow-sm'
              }`}
            >
              {m.content}
              {m.toolInvocations?.map((toolInvocation) => {
                const toolCallId = toolInvocation.toolCallId;
                
                // Render tool calls (optional visualization)
                if (toolInvocation.state === 'result') {
                    if (toolInvocation.toolName === 'createRow') {
                        return (
                            <div key={toolCallId} className="mt-2 text-xs bg-gray-50 p-2 rounded border border-gray-200 text-gray-600">
                                ✅ Created row: {JSON.stringify(toolInvocation.result.data.title)}
                            </div>
                        );
                    }
                    if (toolInvocation.toolName === 'searchListings') {
                        return (
                            <div key={toolCallId} className="mt-2 text-xs bg-gray-50 p-2 rounded border border-gray-200 text-gray-600">
                                🔍 Found {toolInvocation.result.count} listings
                            </div>
                        );
                    }
                }
                return null;
              })}
            </div>
          </div>
        ))}
        {isLoading && (
            <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-green-100 text-green-600 flex items-center justify-center shrink-0">
                    <Bot size={16} />
                </div>
                <div className="bg-white border border-gray-200 rounded-lg p-3 shadow-sm">
                    <span className="animate-pulse">Thinking...</span>
                </div>
            </div>
        )}
      </div>

      <div className="p-4 bg-white border-t border-gray-200">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            className="flex-1 p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-black"
            value={input}
            placeholder="What are you looking for?"
            onChange={handleInputChange}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="bg-blue-600 text-white p-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send size={20} />
          </button>
        </form>
      </div>
    </div>
  );
}
