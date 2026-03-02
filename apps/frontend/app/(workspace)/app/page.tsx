'use client';

import ErrorBoundary from '../../../components/ErrorBoundary';
import Chat from '../../components/Chat';
import ReportBugModal from '../../components/ReportBugModal';
import { AppView } from '../../components/sdui';

export default function WorkspacePage() {
  return (
    <ErrorBoundary>
      <main className="h-[100dvh] w-full overflow-hidden font-sans">
        <AppView>
          <Chat />
        </AppView>
        <ReportBugModal />
      </main>
    </ErrorBoundary>
  );
}
