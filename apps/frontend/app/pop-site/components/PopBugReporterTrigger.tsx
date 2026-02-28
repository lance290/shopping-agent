'use client';

import { Bug } from 'lucide-react';
import { useShoppingStore } from '../../store';

export default function PopBugReporterTrigger() {
  const setReportBugModalOpen = useShoppingStore((state) => state.setReportBugModalOpen);

  return (
    <button
      onClick={() => setReportBugModalOpen(true)}
      className="fixed bottom-4 right-4 md:bottom-6 md:right-6 bg-white text-gray-400 hover:text-green-600 p-3 rounded-full shadow-sm hover:shadow-md border border-gray-200 hover:border-green-300 transition-all z-50 flex items-center justify-center group"
      title="Report a bug"
      aria-label="Report a bug"
    >
      <Bug size={20} className="group-hover:scale-110 transition-transform" />
    </button>
  );
}
