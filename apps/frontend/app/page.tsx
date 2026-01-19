'use client';

import Chat from './components/Chat';
import ProcurementBoard from './components/Board';
import ChoiceFactorPanel from './components/ChoiceFactorPanel';

export default function Home() {
  return (
    <main className="flex h-screen w-full bg-white overflow-hidden">
      {/* Specifications Sidebar (Leftmost, collapsible) */}
      <ChoiceFactorPanel />

      {/* Chat Pane (Center Left) */}
      <Chat />
      
      {/* Board Pane (Right) */}
      <ProcurementBoard />
    </main>
  );
}
