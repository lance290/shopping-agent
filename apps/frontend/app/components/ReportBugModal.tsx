'use client';

import { X, Bug } from 'lucide-react';
import { useShoppingStore } from '../store';
import { Button } from '../../components/ui/Button';

export default function ReportBugModal() {
  const isOpen = useShoppingStore((state) => state.isReportBugModalOpen);
  const close = useShoppingStore((state) => state.setReportBugModalOpen);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/20 backdrop-blur-sm p-4">
      <div 
        className="w-full max-w-lg bg-white rounded-2xl shadow-2xl border border-warm-grey overflow-hidden flex flex-col max-h-[90vh]"
        role="dialog"
        aria-modal="true"
        aria-labelledby="report-bug-title"
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-warm-grey/50 flex justify-between items-center bg-warm-light/50">
          <div className="flex items-center gap-2 text-onyx">
            <div className="p-1.5 bg-rose-100 text-rose-600 rounded-lg">
              <Bug size={18} />
            </div>
            <h2 id="report-bug-title" className="font-medium">Report a Bug</h2>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => close(false)}
            className="text-onyx-muted hover:text-onyx -mr-2"
            aria-label="Close"
          >
            <X size={20} />
          </Button>
        </div>

        {/* Content Skeleton (Task 002 will fill this) */}
        <div className="p-6 overflow-y-auto">
          <div className="flex flex-col items-center justify-center text-center py-8 text-onyx-muted">
            <p>Bug reporting form coming in Task 002.</p>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-warm-light/30 border-t border-warm-grey/50 flex justify-end gap-3">
          <Button variant="secondary" onClick={() => close(false)}>
            Cancel
          </Button>
          <Button disabled>
            Submit Report
          </Button>
        </div>
      </div>
    </div>
  );
}
