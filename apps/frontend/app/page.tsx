'use client';

import Chat from './components/Chat';
import ProcurementBoard from './components/Board';

export default function Home() {
  return (
    <main className="flex h-screen w-full bg-white overflow-hidden">
      {/* Chat Pane (Center Left) */}
      <Chat />
      
      {/* Board Pane (Right) */}
      <ProcurementBoard />
    </main>
  );
}
