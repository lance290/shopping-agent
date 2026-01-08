'use client';

import { useState, useEffect } from 'react';
import { Package, Truck, DollarSign, Calendar, ExternalLink } from 'lucide-react';

interface Row {
  id: number;
  title: string;
  status: string;
  budget_max: number | null;
  currency: string;
}

export default function ProcurementBoard() {
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchRows = async () => {
    try {
        const res = await fetch('/api/rows');
        if (res.ok) {
            const data = await res.json();
            setRows(data);
        }
    } catch (e) {
        console.error("Failed to fetch rows", e);
    } finally {
        setLoading(false);
    }
  };

  useEffect(() => {
    fetchRows();
    // Poll for updates every 5 seconds (MVP realtime)
    const interval = setInterval(fetchRows, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex-1 bg-gray-100 p-6 overflow-x-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Procurement Board</h1>
        <button onClick={fetchRows} className="text-sm text-blue-600 hover:underline">
            Refresh
        </button>
      </div>

      <div className="space-y-6">
        {loading && rows.length === 0 && (
            <div className="text-center text-gray-500 py-10">Loading rows...</div>
        )}

        {!loading && rows.length === 0 && (
            <div className="text-center text-gray-500 py-10 bg-white rounded-lg border border-dashed border-gray-300">
                <Package className="mx-auto h-10 w-10 text-gray-400 mb-2" />
                <p>No requests yet. Use the chat to start one!</p>
            </div>
        )}

        {rows.map((row) => (
          <div key={row.id} className="flex gap-4 items-start min-w-max">
            {/* Request Tile (Leftmost) */}
            <div className="w-80 bg-white rounded-lg shadow-sm border border-gray-200 p-4 shrink-0 border-l-4 border-l-blue-500">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-semibold text-gray-900 line-clamp-2">{row.title}</h3>
                <span className={`text-xs px-2 py-1 rounded-full capitalize ${
                    row.status === 'sourcing' ? 'bg-yellow-100 text-yellow-800' : 
                    row.status === 'closed' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                }`}>
                  {row.status}
                </span>
              </div>
              <div className="text-sm text-gray-500 space-y-1">
                {row.budget_max && (
                    <div className="flex items-center gap-2">
                        <DollarSign size={14} />
                        <span>Max: {row.currency} {row.budget_max}</span>
                    </div>
                )}
                <div className="text-xs text-gray-400 mt-2">
                    ID: #{row.id}
                </div>
              </div>
            </div>

            {/* Bid Tiles (Placeholder for MVP) */}
            <div className="flex gap-4 overflow-x-auto py-1">
                <div className="w-64 bg-white/50 rounded-lg border border-dashed border-gray-300 p-4 flex items-center justify-center text-gray-400 text-sm shrink-0">
                    Waiting for bids...
                </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
