'use client';

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { X, Send, Building2, Loader2, Check, AlertCircle } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { generateOutreachEmail, sendOutreachEmail } from '../utils/api';
import { getMe } from '../utils/auth';

interface VendorContactModalProps {
  isOpen: boolean;
  onClose: () => void;
  rowId: number;
  rowTitle: string;
  rowChoiceAnswers?: string;
  serviceCategory?: string;
  vendorName: string;
  vendorCompany: string;
  vendorEmail: string;
}

type ModalState = 'loading' | 'review' | 'sending' | 'sent' | 'error';

export default function VendorContactModal({
  isOpen,
  onClose,
  rowId,
  rowTitle,
  vendorName,
  vendorCompany,
  vendorEmail,
}: VendorContactModalProps) {
  const [mounted, setMounted] = useState(false);
  const [state, setState] = useState<ModalState>('loading');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [replyToEmail, setReplyToEmail] = useState('');
  const [senderName, setSenderName] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    setMounted(true);
  }, []);

  // When modal opens: fetch user email + generate LLM email
  useEffect(() => {
    if (!isOpen) return;

    setState('loading');
    setErrorMsg('');

    const init = async () => {
      // Get user's profile for reply-to, name, company
      let userEmail = '';
      let userName = '';
      let userCompany = '';
      try {
        const user = await getMe();
        if (user?.email) {
          userEmail = user.email;
          setReplyToEmail(user.email);
        }
        if (user?.name) {
          userName = user.name;
          setSenderName(user.name);
        }
        if (user?.company) {
          userCompany = user.company;
          setCompanyName(user.company);
        }
      } catch { /* no-op */ }

      // Generate email via LLM
      const result = await generateOutreachEmail(
        rowId,
        vendorEmail,
        vendorCompany,
        userEmail || 'your@email.com',
        userName || undefined,
        userCompany ? `${userCompany}` : undefined,
      );

      if (result) {
        setSubject(result.subject);
        setBody(result.body);
        setState('review');
      } else {
        // Fallback if LLM fails
        setSubject(`Inquiry — ${rowTitle}`);
        const fallbackName = senderName || 'Your Name';
        const fallbackCompany = companyName || 'Your Company';
        setBody(
          `Hi ${vendorCompany},\n\nI'm reaching out regarding:\n\n  ${rowTitle}\n\nCould you please let us know about pricing, availability, and any relevant details?\n\nThanks,\n${fallbackName}\n${fallbackCompany}`
        );
        setState('review');
      }
    };

    init();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  const handleSend = async () => {
    if (!replyToEmail.trim()) {
      setErrorMsg('Please enter your email address so the vendor can reply to you.');
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(replyToEmail.trim())) {
      setErrorMsg('Please enter a valid email address.');
      return;
    }
    if (!subject.trim() || !body.trim()) {
      setErrorMsg('Subject and body cannot be empty.');
      return;
    }

    setState('sending');
    setErrorMsg('');

    const result = await sendOutreachEmail(
      rowId,
      vendorEmail,
      vendorCompany,
      replyToEmail,
      subject,
      body,
      vendorName,
      senderName || undefined,
      companyName || undefined,
    );

    if (result?.status === 'sent') {
      setState('sent');
    } else {
      setErrorMsg(result?.error || 'Failed to send email. Please try again.');
      setState('error');
    }
  };

  if (!isOpen || !mounted) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-xl mx-4 overflow-hidden max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">
              {state === 'sent' ? 'Email Sent!' : 'Send Outreach'}
            </h2>
            <button
              onClick={onClose}
              className="text-white/80 hover:text-white transition-colors"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Vendor info bar */}
        <div className="px-6 py-3 bg-gray-50 border-b border-gray-200 flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
            <Building2 size={16} className="text-blue-600" />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-semibold text-gray-900 truncate">{vendorCompany}</div>
            <div className="text-xs text-gray-500 truncate">{vendorEmail}</div>
          </div>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4 overflow-y-auto flex-1">
          {/* Loading state */}
          {state === 'loading' && (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <Loader2 size={32} className="text-blue-600 animate-spin" />
              <p className="text-sm text-gray-500">Generating personalized email from your conversation...</p>
            </div>
          )}

          {/* Sent state */}
          {state === 'sent' && (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center">
                <Check size={32} className="text-green-600" />
              </div>
              <p className="text-lg font-semibold text-gray-900">Email sent to {vendorCompany}!</p>
              <p className="text-sm text-gray-500 text-center">
                Replies will go directly to <strong>{replyToEmail}</strong>.
                <br />A tracked quote link was included in the email.
              </p>
              <Button variant="primary" onClick={onClose} className="mt-4">
                Done
              </Button>
            </div>
          )}

          {/* Review / Edit state */}
          {(state === 'review' || state === 'sending' || state === 'error') && (
            <>
              {errorMsg && (
                <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 flex items-start gap-2">
                  <AlertCircle size={16} className="text-red-500 mt-0.5 flex-shrink-0" />
                  <p className="text-sm text-red-700">{errorMsg}</p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="text-xs text-gray-500 mb-1">Your name</div>
                  <input
                    value={senderName}
                    onChange={(e) => setSenderName(e.target.value)}
                    placeholder="Your Name"
                    className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-1">Company</div>
                  <input
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="Your Company"
                    className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                </div>
              </div>

              <div>
                <div className="text-xs text-gray-500 mb-1">Reply-to (your email)</div>
                <input
                  value={replyToEmail}
                  onChange={(e) => setReplyToEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                />
                <p className="text-[10px] text-gray-400 mt-1">Vendor replies go directly to this address.</p>
              </div>

              <div>
                <div className="text-xs text-gray-500 mb-1">Subject</div>
                <input
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                />
              </div>

              <div>
                <div className="text-xs text-gray-500 mb-1">Email body</div>
                <textarea
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  rows={10}
                  className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-y"
                />
                <p className="text-[10px] text-gray-400 mt-1">
                  A &quot;Submit Your Quote&quot; button and tracking link will be appended automatically.
                </p>
              </div>

              <div className="bg-blue-50 border border-blue-100 rounded-lg px-4 py-3">
                <p className="text-xs text-blue-700">
                  <strong>How it works:</strong> Email is sent from <em>BuyAnything</em> via our verified domain for best deliverability.
                  The vendor&apos;s reply goes directly to <strong>{replyToEmail || 'your email'}</strong>.
                  A tracked quote link is included so the vendor can submit a formal quote on our platform.
                </p>
              </div>
            </>
          )}
        </div>

        {/* Footer actions */}
        {(state === 'review' || state === 'sending' || state === 'error') && (
          <div className="px-6 pb-6 flex gap-3">
            <Button
              variant="secondary"
              onClick={onClose}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleSend}
              disabled={state === 'sending'}
              className="flex-1 gap-2"
            >
              {state === 'sending' ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Send size={16} />
                  Send Email
                </>
              )}
            </Button>
          </div>
        )}
      </div>
    </div>,
    document.body
  );
}
