'use client';

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { X, Copy, Check, Mail, Building2, User } from 'lucide-react';
import { Button } from '../../components/ui/Button';

interface VendorContactModalProps {
  isOpen: boolean;
  onClose: () => void;
  vendorName: string;
  vendorCompany: string;
  vendorEmail: string;
}

export default function VendorContactModal({
  isOpen,
  onClose,
  vendorName,
  vendorCompany,
  vendorEmail,
}: VendorContactModalProps) {
  const [copied, setCopied] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!isOpen || !mounted) return null;

  const handleCopyEmail = async () => {
    try {
      await navigator.clipboard.writeText(vendorEmail);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy email:', err);
    }
  };

  const handleEmailClick = () => {
    window.location.href = `mailto:${vendorEmail}`;
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Contact Provider</h2>
            <button
              onClick={onClose}
              className="text-white/80 hover:text-white transition-colors"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-4">
          <div className="flex items-center gap-3 text-ink">
            <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
              <Building2 size={20} className="text-blue-600" />
            </div>
            <div>
              <div className="text-sm text-ink-muted">Company</div>
              <div className="font-semibold">{vendorCompany}</div>
            </div>
          </div>

          <div className="flex items-center gap-3 text-ink">
            <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
              <User size={20} className="text-blue-600" />
            </div>
            <div>
              <div className="text-sm text-ink-muted">Contact</div>
              <div className="font-semibold">{vendorName}</div>
            </div>
          </div>

          <div className="flex items-center gap-3 text-ink">
            <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
              <Mail size={20} className="text-blue-600" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm text-ink-muted">Email</div>
              <div className="font-semibold truncate">{vendorEmail}</div>
            </div>
          </div>
        </div>

        <div className="px-6 pb-6 flex gap-3">
          <Button
            variant="secondary"
            onClick={handleCopyEmail}
            className="flex-1 gap-2"
          >
            {copied ? (
              <>
                <Check size={16} className="text-green-600" />
                Copied!
              </>
            ) : (
              <>
                <Copy size={16} />
                Copy Email
              </>
            )}
          </Button>
          <Button
            variant="primary"
            onClick={handleEmailClick}
            className="flex-1 gap-2"
          >
            <Mail size={16} />
            Open Email App
          </Button>
        </div>
      </div>
    </div>,
    document.body
  );
}
