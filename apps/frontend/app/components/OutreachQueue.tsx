'use client';

import { useState, useEffect } from 'react';
import {
  Mail, Send, Sparkles, Loader2,
  User, AlertCircle, Eye, CheckCircle2, X,
} from 'lucide-react';
import { Offer } from '../store';
import { getMe } from '../utils/auth';
import { createOutreachCampaign, approveAndSendCampaign } from '../utils/api-outreach';
import type { CampaignDetails, CampaignMessage } from '../utils/api-outreach';

interface VendorMatchPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onSent?: (bidIds: number[]) => void;
  rowId: number;
  desireTier: string;
  offers: Offer[];
  selectedBidIds: number[];
}

type FlowState = 'idle' | 'capture' | 'drafting' | 'review' | 'sending' | 'sent' | 'error';

export default function OutreachQueue({ isOpen, onClose, onSent, rowId, desireTier, offers, selectedBidIds }: VendorMatchPanelProps) {
  const [flowState, setFlowState] = useState<FlowState>('idle');
  const [senderName, setSenderName] = useState('');
  const [senderEmail, setSenderEmail] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [pendingBidIds, setPendingBidIds] = useState<number[]>([]);

  // Campaign review
  const [campaign, setCampaign] = useState<CampaignDetails | null>(null);
  const [previewIdx, setPreviewIdx] = useState(0);

  // Pre-fill sender info from user profile
  useEffect(() => {
    getMe().then(user => {
      if (user?.name) setSenderName(user.name);
      if (user?.email) setSenderEmail(user.email);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!isOpen) {
      setFlowState('idle');
      setCampaign(null);
      setPreviewIdx(0);
      setErrorMsg('');
      return;
    }
    setPendingBidIds(selectedBidIds);
    setCampaign(null);
    setPreviewIdx(0);
    setErrorMsg('');
    setFlowState('capture');
  }, [isOpen, selectedBidIds]);

  const outreachEligibleOffers = offers.filter(o =>
    o.source === 'vendor_directory'
    || o.is_service_provider === true
    || (o.vendor_id != null && o.source?.startsWith('apify_'))
  );
  const selectedOffers = outreachEligibleOffers.filter((offer) => typeof offer.bid_id === 'number' && selectedBidIds.includes(offer.bid_id));
  if (!isOpen || outreachEligibleOffers.length === 0) return null;

  const draftCampaign = async (bidIds: number[], name: string, email: string) => {
    if (!name.trim()) { setErrorMsg('Please enter your name.'); return; }
    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setErrorMsg('Please enter a valid email address.'); return;
    }
    setErrorMsg('');
    setFlowState('drafting');
    setSenderName(name);
    setSenderEmail(email);

    const result = await createOutreachCampaign(rowId, bidIds, name, email);
    if (result) {
      setCampaign(result);
      setPreviewIdx(0);
      setFlowState('review');
    } else {
      setErrorMsg('Failed to draft emails. Please try again.');
      setFlowState('error');
    }
  };

  const handleApproveAndSend = async () => {
    if (!campaign) return;
    setFlowState('sending');
    const result = await approveAndSendCampaign(campaign.campaign.id);
    if (result) {
      onSent?.(pendingBidIds);
      setFlowState('sent');
      setTimeout(() => {
        setFlowState('idle');
        onClose();
      }, 2000);
    } else {
      setErrorMsg('Failed to send emails. Please try again.');
      setFlowState('error');
    }
  };

  const closeModal = () => {
    setErrorMsg('');
    setFlowState('idle');
    onClose();
  };

  const tierLabel = desireTier === 'service' ? 'Service Providers'
    : desireTier === 'bespoke' ? 'Specialists'
    : desireTier === 'high_value' ? 'Brokers & Specialists'
    : 'Matched Vendors';

  const currentMsg: CampaignMessage | undefined = campaign?.messages[previewIdx];

  return (
    <>
      {flowState !== 'idle' && flowState !== 'sent' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={closeModal} />
          <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-2xl mx-4 overflow-hidden max-h-[85vh] flex flex-col">
            {/* Modal Header */}
            <div className="bg-navy px-6 py-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">
                {flowState === 'capture' && 'Your Contact Info'}
                {flowState === 'drafting' && 'Drafting Emails...'}
                {flowState === 'review' && `Review Emails (${campaign?.messages.length || 0})`}
                {flowState === 'sending' && 'Sending...'}
                {flowState === 'error' && 'Error'}
              </h2>
              <button onClick={closeModal} className="text-white/80 hover:text-white">
                <X size={20} />
              </button>
            </div>

            <div className="p-6 space-y-4 overflow-y-auto flex-1">
              {/* Error banner */}
              {errorMsg && (
                <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 flex items-start gap-2">
                  <AlertCircle size={16} className="text-red-500 mt-0.5 flex-shrink-0" />
                  <p className="text-sm text-red-700">{errorMsg}</p>
                </div>
              )}

              {/* Capture: name + email */}
              {flowState === 'capture' && (
                <>
                  <p className="text-sm text-ink-muted">
                    Vendors will reply directly to your email. This personalizes every outreach.
                  </p>
                  <div className="rounded-lg border border-warm-grey bg-canvas-dark px-4 py-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-ink-muted flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5" />
                      {selectedOffers.length} {tierLabel.toLowerCase()} selected
                    </p>
                    <div className="mt-2 space-y-1 max-h-28 overflow-y-auto">
                      {selectedOffers.map((offer) => (
                        <div key={offer.bid_id} className="text-sm text-ink">
                          {offer.vendor_company || offer.vendor_name || offer.merchant}
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs text-ink-muted mb-1 block">Your name</label>
                      <div className="relative">
                        <User size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted" />
                        <input
                          value={senderName}
                          onChange={e => setSenderName(e.target.value)}
                          placeholder="Jane Smith"
                          className="w-full pl-9 pr-3 py-2 bg-white border border-warm-grey rounded-lg text-sm text-ink focus:border-gold focus:ring-1 focus:ring-gold outline-none"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="text-xs text-ink-muted mb-1 block">Your email</label>
                      <div className="relative">
                        <Mail size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted" />
                        <input
                          value={senderEmail}
                          onChange={e => setSenderEmail(e.target.value)}
                          placeholder="jane@company.com"
                          type="email"
                          className="w-full pl-9 pr-3 py-2 bg-white border border-warm-grey rounded-lg text-sm text-ink focus:border-gold focus:ring-1 focus:ring-gold outline-none"
                        />
                      </div>
                    </div>
                  </div>
                  <div className="bg-gold/5 border border-gold/20 rounded-lg px-4 py-3">
                    <p className="text-xs text-ink-muted">
                      <strong>How it works:</strong> We draft a personalized email for each vendor using AI that
                      recognizes the vendor type (jet charter, luxury goods, local service, etc.) and tailors
                      the ask accordingly. You review before anything sends.
                    </p>
                  </div>
                </>
              )}

              {/* Drafting spinner */}
              {flowState === 'drafting' && (
                <div className="flex flex-col items-center justify-center py-12 gap-3">
                  <Loader2 size={32} className="text-gold animate-spin" />
                  <p className="text-sm text-ink-muted">
                    AI is classifying vendors and drafting personalized emails...
                  </p>
                  <p className="text-xs text-onyx-muted">
                    {pendingBidIds.length} vendor{pendingBidIds.length !== 1 ? 's' : ''}
                  </p>
                </div>
              )}

              {/* Review: email previews */}
              {flowState === 'review' && campaign && currentMsg && (
                <>
                  {/* Tabs for multiple messages */}
                  {campaign.messages.length > 1 && (
                    <div className="flex gap-1 overflow-x-auto pb-1">
                      {campaign.messages.map((msg, i) => (
                        <button
                          key={msg.id}
                          onClick={() => setPreviewIdx(i)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                            i === previewIdx
                              ? 'bg-navy text-white'
                              : 'bg-canvas-dark text-ink-muted hover:bg-warm-grey'
                          }`}
                        >
                          {msg.vendor?.name || `Vendor ${i + 1}`}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Email preview */}
                  <div className="border border-warm-grey rounded-xl overflow-hidden">
                    <div className="bg-canvas-dark px-4 py-3 border-b border-warm-grey">
                      <div className="flex items-center gap-2 text-xs text-ink-muted">
                        <Mail size={12} />
                        <span>To: <strong className="text-ink">{currentMsg.to_address || 'No email'}</strong></span>
                      </div>
                      <div className="text-xs text-ink-muted mt-1">
                        Subject: <strong className="text-ink">{currentMsg.subject}</strong>
                      </div>
                      <div className="text-xs text-ink-muted mt-0.5">
                        Reply-to: <strong className="text-ink">{senderEmail}</strong>
                      </div>
                    </div>
                    <div className="px-4 py-4 text-sm text-ink whitespace-pre-wrap leading-relaxed max-h-64 overflow-y-auto">
                      {currentMsg.body}
                    </div>
                    {/* Deal Card preview */}
                    <div className="mx-4 mb-4 border border-slate-200 rounded-xl overflow-hidden">
                      <div className="bg-gradient-to-br from-navy to-slate-700 px-5 py-3">
                        <p className="text-[10px] uppercase tracking-widest text-gold font-bold">Deal Card</p>
                        <p className="text-sm font-bold text-white mt-1">{campaign.campaign.request_summary}</p>
                      </div>
                      <div className="px-5 py-2 bg-slate-50 text-center">
                        <p className="text-[10px] text-slate-500">Powered by <strong>BuyAnything.ai</strong></p>
                      </div>
                    </div>
                  </div>

                  <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
                    <p className="text-xs text-amber-800">
                      <Eye size={12} className="inline mr-1" />
                      Review each email above. Every email includes a <strong>deal card</strong>, a tracked
                      quote link, and our <strong>Try BuyAnything</strong> viral footer.
                    </p>
                  </div>
                </>
              )}

              {/* Sending spinner */}
              {flowState === 'sending' && (
                <div className="flex flex-col items-center justify-center py-12 gap-3">
                  <Loader2 size={32} className="text-gold animate-spin" />
                  <p className="text-sm text-ink-muted">Approving and sending emails...</p>
                </div>
              )}
            </div>

            {/* Footer actions */}
            {(flowState === 'capture' || flowState === 'review' || flowState === 'error') && (
              <div className="px-6 pb-6 flex gap-3">
                <button
                  onClick={closeModal}
                  className="flex-1 px-4 py-2.5 bg-canvas-dark text-ink rounded-lg text-sm font-medium hover:bg-warm-grey transition-colors"
                >
                  Cancel
                </button>
                {flowState === 'capture' && (
                  <button
                    onClick={() => draftCampaign(pendingBidIds, senderName, senderEmail)}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gold text-navy rounded-lg text-sm font-medium hover:bg-gold-dark transition-colors"
                  >
                    <Sparkles size={16} />
                    Draft RFPs ({pendingBidIds.length})
                  </button>
                )}
                {flowState === 'review' && (
                  <button
                    onClick={handleApproveAndSend}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gold text-navy rounded-lg text-sm font-medium hover:bg-gold-dark transition-colors"
                  >
                    <Send size={16} />
                    Approve &amp; Send All ({campaign?.messages.length || 0})
                  </button>
                )}
                {flowState === 'error' && (
                  <button
                    onClick={() => draftCampaign(pendingBidIds, senderName, senderEmail)}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gold text-navy rounded-lg text-sm font-medium hover:bg-gold-dark transition-colors"
                  >
                    Retry
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Sent toast */}
      {flowState === 'sent' && (
        <div className="fixed bottom-6 right-6 z-50 bg-green-600 text-white px-6 py-3 rounded-xl shadow-lg flex items-center gap-2 animate-in slide-in-from-bottom-4">
          <CheckCircle2 size={18} />
          <span className="text-sm font-medium">Emails sent successfully!</span>
        </div>
      )}
    </>
  );
}
