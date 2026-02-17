'use client';

import dynamic from 'next/dynamic';
import ErrorBoundary from '../../../components/ErrorBoundary';

const WorkspaceView = dynamic(() => import('../../components/WorkspaceView'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-screen">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
    </div>
  ),
});

export default function WorkspacePage() {
  return (
    <ErrorBoundary>
      <WorkspaceView />
    </ErrorBoundary>
  );
}
