'use client';

import Chat from './components/Chat';
import ProcurementBoard from './components/Board';
import RequestsSidebar from './components/RequestsSidebar';

export default function Home() {
  return (
    <main className="flex h-screen w-full bg-white overflow-hidden">
      {/* Requests Sidebar (Far Left) */}
      <RequestsSidebar />

      {/* Chat Pane (Center Left) */}
      <Chat />
      
      {/* Board Pane (Right) */}
      <ProcurementBoard />
    </main>
  );
}
