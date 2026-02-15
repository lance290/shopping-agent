'use client';

import { useState, useEffect, useCallback } from 'react';
import { Mail, Phone, Globe, MessageCircle, Pause, CheckCheck, Edit3, Send, ChevronDown, ChevronUp } from 'lucide-react';

interface OutreachMessage {
  id: number;
  vendor_id: number;
  vendor: { id: number; name: string; domain?: string | null };
  direction: string;
  channel: string;
  status: string;
  subject: string;
  body: string;
  to_address: string;
  sent_at: string | null;
}

interface OutreachQuote {
  id: number;
  vendor_id: number;
  vendor: { id: number; name: string };
  price: number | null;
  currency: string;
  availability: string | null;
  terms: string | null;
  entry_method: string;
  is_finalist: boolean;
}

interface Campaign {
  id: number;
  row_id: number;
  status: string;
  request_summary: string;
  action_budget: number;
  actions_used: number;
  created_at: string;
}

interface CampaignDetails {
  campaign: Campaign;
  messages: OutreachMessage[];
  quotes: OutreachQuote[];
}

const CHANNEL_ICONS: Record<string, typeof Mail> = {
  email: Mail,
  phone: Phone,
  web_form: Globe,
  whatsapp: MessageCircle,
  manual: Edit3,
};

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  approved: 'bg-blue-100 text-blue-700',
  sent: 'bg-green-100 text-green-700',
  delivered: 'bg-green-200 text-green-800',
  replied: 'bg-purple-100 text-purple-700',
  failed: 'bg-red-100 text-red-700',
  ea_review: 'bg-yellow-100 text-yellow-700',
};

export default function OutreachQueue({ rowId }: { rowId: number }) {
  const [campaign, setCampaign] = useState<CampaignDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [expandedMessage, setExpandedMessage] = useState<number | null>(null);
  const [editingMessage, setEditingMessage] = useState<number | null>(null);
  const [editBody, setEditBody] = useState('');

  const fetchCampaign = useCallback(async () => {
    try {
      const res = await fetch(`/api/outreach/campaigns/row/${rowId}`);
      if (res.ok) {
        const campaigns = await res.json();
        if (campaigns.length > 0) {
          const latest = campaigns[campaigns.length - 1];
          const detailRes = await fetch(`/api/outreach/campaigns/${latest.id}`);
          if (detailRes.ok) {
            setCampaign(await detailRes.json());
          }
        }
      }
    } catch {
      // No campaign yet
    }
  }, [rowId]);

  useEffect(() => {
    fetchCampaign();
  }, [fetchCampaign]);

  const createCampaign = async () => {
    setCreating(true);
    try {
      const res = await fetch('/api/outreach/campaigns', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ row_id: rowId }),
      });
      if (res.ok) {
        setCampaign(await res.json());
      }
    } finally {
      setCreating(false);
    }
  };

  const approveAll = async () => {
    if (!campaign) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/outreach/campaigns/${campaign.campaign.id}/approve-all`, {
        method: 'POST',
      });
      if (res.ok) {
        await fetchCampaign();
      }
    } finally {
      setLoading(false);
    }
  };

  const pauseAll = async () => {
    if (!campaign) return;
    setLoading(true);
    try {
      await fetch(`/api/outreach/campaigns/${campaign.campaign.id}/pause`, {
        method: 'POST',
      });
      await fetchCampaign();
    } finally {
      setLoading(false);
    }
  };

  const approveMessage = async (messageId: number, body?: string) => {
    setLoading(true);
    try {
      await fetch(`/api/outreach/campaigns/messages/${messageId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ edited_body: body || undefined }),
      });
      setEditingMessage(null);
      await fetchCampaign();
    } finally {
      setLoading(false);
    }
  };

  // No campaign yet — show create button
  if (!campaign) {
    return (
      <div className="border border-dashed border-gray-300 rounded-lg p-6 text-center">
        <Send className="w-8 h-8 mx-auto mb-3 text-gray-400" />
        <p className="text-sm text-gray-600 mb-3">
          Ready to contact vendors? The agent will draft personalized outreach for each one.
        </p>
        <button
          onClick={createCampaign}
          disabled={creating}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {creating ? 'Drafting...' : 'Draft Outreach'}
        </button>
      </div>
    );
  }

  const { campaign: camp, messages, quotes } = campaign;
  const draftCount = messages.filter(m => m.status === 'draft').length;
  const sentCount = messages.filter(m => m.status === 'sent' || m.status === 'delivered').length;

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="bg-gray-50 px-4 py-3 flex items-center justify-between border-b">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Outreach Queue</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            {camp.actions_used} of {camp.action_budget} contacts used
          </p>
        </div>
        <div className="flex gap-2">
          {draftCount > 0 && (
            <button
              onClick={approveAll}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600 text-white rounded text-xs font-medium hover:bg-green-700 disabled:opacity-50"
            >
              <CheckCheck className="w-3.5 h-3.5" />
              Approve All ({draftCount})
            </button>
          )}
          {camp.status === 'active' && (
            <button
              onClick={pauseAll}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-red-100 text-red-700 rounded text-xs font-medium hover:bg-red-200 disabled:opacity-50"
            >
              <Pause className="w-3.5 h-3.5" />
              Pause All
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="divide-y divide-gray-100">
        {messages.map(msg => {
          const ChannelIcon = CHANNEL_ICONS[msg.channel] || Mail;
          const isExpanded = expandedMessage === msg.id;
          const isEditing = editingMessage === msg.id;

          return (
            <div key={msg.id} className="px-4 py-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <ChannelIcon className="w-4 h-4 text-gray-400" />
                  <div>
                    <span className="text-sm font-medium text-gray-900">{msg.vendor.name}</span>
                    {msg.to_address && (
                      <span className="text-xs text-gray-400 ml-2">{msg.to_address}</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[msg.status] || STATUS_COLORS.draft}`}>
                    {msg.status}
                  </span>
                  {msg.status === 'draft' && (
                    <>
                      <button
                        onClick={() => {
                          setEditingMessage(isEditing ? null : msg.id);
                          setEditBody(msg.body);
                        }}
                        className="text-xs text-gray-500 hover:text-gray-700 px-2 py-1 rounded hover:bg-gray-100"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => approveMessage(msg.id)}
                        disabled={loading}
                        className="text-xs text-green-600 hover:text-green-800 px-2 py-1 rounded hover:bg-green-50 font-medium"
                      >
                        Approve
                      </button>
                    </>
                  )}
                  <button
                    onClick={() => setExpandedMessage(isExpanded ? null : msg.id)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Expanded preview */}
              {isExpanded && !isEditing && (
                <div className="mt-3 ml-7 p-3 bg-gray-50 rounded text-sm text-gray-700 whitespace-pre-wrap">
                  {msg.subject && <p className="font-medium mb-2">Subject: {msg.subject}</p>}
                  {msg.body}
                </div>
              )}

              {/* Edit mode */}
              {isEditing && (
                <div className="mt-3 ml-7">
                  <textarea
                    value={editBody}
                    onChange={e => setEditBody(e.target.value)}
                    className="w-full p-3 border border-gray-200 rounded text-sm text-gray-700 min-h-[150px] focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={() => approveMessage(msg.id, editBody)}
                      disabled={loading}
                      className="px-3 py-1.5 bg-green-600 text-white rounded text-xs font-medium hover:bg-green-700"
                    >
                      Save & Approve
                    </button>
                    <button
                      onClick={() => setEditingMessage(null)}
                      className="px-3 py-1.5 text-gray-600 rounded text-xs hover:bg-gray-100"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Quotes section (if any) */}
      {quotes.length > 0 && (
        <div className="border-t border-gray-200 bg-gray-50 px-4 py-3">
          <h4 className="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wide">Quotes Received</h4>
          <div className="space-y-2">
            {quotes.map(q => (
              <div key={q.id} className="flex items-center justify-between text-sm">
                <span className="text-gray-900 font-medium">{q.vendor.name}</span>
                <span className="text-gray-700">
                  {q.price != null ? `${q.currency} ${q.price.toLocaleString()}` : 'Pending'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer status */}
      <div className="border-t border-gray-100 px-4 py-2 bg-white">
        <p className="text-xs text-gray-400">
          {sentCount > 0 && `${sentCount} sent`}
          {sentCount > 0 && draftCount > 0 && ' · '}
          {draftCount > 0 && `${draftCount} drafts pending review`}
          {sentCount === 0 && draftCount === 0 && 'All messages processed'}
        </p>
      </div>
    </div>
  );
}
