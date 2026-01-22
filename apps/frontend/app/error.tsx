'use client';

import { useEffect } from 'react';
import { useShoppingStore } from './store';
import { Button } from '../components/ui/Button';
import { AlertTriangle, Bug } from 'lucide-react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const openReportBug = useShoppingStore(state => state.setReportBugModalOpen);

  useEffect(() => {
    // Log the error to diagnostics (ring buffer) automatically
    console.error(`Next.js Error Boundary caught: ${error.message}`, error);
  }, [error]);

  return (
    <div className="flex h-screen w-full flex-col items-center justify-center bg-warm-white p-4 text-center">
      <div className="mb-4 rounded-full bg-rose-50 p-4 text-rose-500">
        <AlertTriangle size={48} />
      </div>
      <h2 className="mb-2 text-2xl font-semibold text-onyx">Something went wrong!</h2>
      <p className="mb-8 max-w-md text-onyx-muted">
        We apologize for the inconvenience. The application has encountered an unexpected error.
      </p>
      
      <div className="flex gap-4">
        <Button onClick={() => reset()} variant="secondary">
          Try again
        </Button>
        <Button 
          onClick={() => openReportBug(true)} 
          variant="primary"
          className="flex items-center gap-2"
        >
          <Bug size={16} />
          Report Bug
        </Button>
      </div>
    </div>
  );
}
