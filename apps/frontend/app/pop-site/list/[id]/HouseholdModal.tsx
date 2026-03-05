'use client';

import { useState, useEffect } from 'react';

interface Member {
  user_id: number;
  name: string;
  email: string;
  role: string;
  channel: string;
  joined_at: string | null;
  is_owner: boolean;
}

interface HouseholdModalProps {
  projectId: number;
  onClose: () => void;
}

export default function HouseholdModal({ projectId, onClose }: HouseholdModalProps) {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [removing, setRemoving] = useState<number | null>(null);

  useEffect(() => {
    async function fetchMembers() {
      try {
        const res = await fetch(`/api/pop/projects/${projectId}/members`);
        if (!res.ok) return;
        const data = await res.json();
        setMembers(data.members || []);
      } finally {
        setLoading(false);
      }
    }
    fetchMembers();
  }, [projectId]);

  const handleRemove = async (userId: number) => {
    setRemoving(userId);
    try {
      const res = await fetch(`/api/pop/projects/${projectId}/members/${userId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setMembers((prev) => prev.filter((m) => m.user_id !== userId));
      }
    } finally {
      setRemoving(null);
    }
  };

  const channelIcon = (ch: string) => {
    switch (ch) {
      case 'sms': return '💬';
      case 'email': return '📧';
      default: return '🌐';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white w-full max-w-lg rounded-t-3xl sm:rounded-2xl p-6 pb-8 shadow-xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-gray-900">Household Members</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
        </div>

        {loading ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-600" />
          </div>
        ) : members.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-6">
            No members yet. Share your list to invite family members!
          </p>
        ) : (
          <ul className="space-y-3">
            {members.map((m) => (
              <li
                key={m.user_id}
                className="flex items-center gap-3 bg-gray-50 rounded-xl px-4 py-3"
              >
                <div className="w-9 h-9 rounded-full bg-green-100 flex items-center justify-center text-green-700 font-bold text-sm flex-shrink-0">
                  {(m.name || '?')[0].toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {m.name}
                    {m.is_owner && (
                      <span className="ml-1.5 text-[10px] font-semibold bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full">
                        Owner
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-gray-400 truncate">
                    {channelIcon(m.channel)} {m.channel}
                  </p>
                </div>
                {!m.is_owner && (
                  <button
                    onClick={() => handleRemove(m.user_id)}
                    disabled={removing === m.user_id}
                    className="text-xs text-red-500 hover:text-red-700 font-medium disabled:opacity-50"
                  >
                    {removing === m.user_id ? '...' : 'Remove'}
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}

        <p className="text-xs text-gray-400 text-center mt-5">
          Members can add items via SMS, email, or the web app.
        </p>
      </div>
    </div>
  );
}
