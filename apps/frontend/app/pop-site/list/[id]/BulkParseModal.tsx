'use client';

import { useState } from 'react';

interface BulkParseModalProps {
  projectId: number;
  onClose: () => void;
  onParsed: (newItems: any[]) => void;
}

export default function BulkParseModal({ projectId, onClose, onParsed }: BulkParseModalProps) {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleParse = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/pop/projects/${projectId}/bulk_parse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) throw new Error('Failed to parse items');
      const data = await res.json();
      if (data.rows && data.rows.length > 0) {
        onParsed(data.rows);
      } else {
        setError("Couldn't find any grocery items in that text.");
        setLoading(false);
      }
    } catch (e: any) {
      setError(e.message || 'An error occurred');
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white w-full max-w-lg rounded-t-3xl sm:rounded-2xl p-6 pb-8 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-gray-900">Paste Recipe or List</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">
            &times;
          </button>
        </div>

        <p className="text-sm text-gray-500 mb-4">
          Paste a recipe, an email from your partner, or a wall of text. Pop will extract the grocery items for you.
        </p>

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="e.g. Need 2 lbs chicken, taco seasoning, and a bag of tortillas..."
          className="w-full h-40 p-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm resize-none"
          disabled={loading}
        />

        {error && <p className="text-red-500 text-xs mt-2">{error}</p>}

        <button
          onClick={handleParse}
          disabled={loading || !text.trim()}
          className="w-full mt-4 bg-green-600 text-white font-medium py-3 rounded-xl hover:bg-green-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
              Parsing...
            </>
          ) : (
            'Extract Items'
          )}
        </button>
      </div>
    </div>
  );
}
