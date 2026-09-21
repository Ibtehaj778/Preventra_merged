import React, { useCallback, useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopNav from './TopNav';
import Chatbot from './Chatbot';

export default function Layout() {
  const [navOpen, setNavOpen] = useState(false);
  // Stable identity: Sidebar closes itself on every navigation via an effect,
  // and a fresh function each render would re-fire that effect constantly.
  const closeNav = useCallback(() => setNavOpen(false), []);

  return (
    <div className="flex h-dvh overflow-hidden bg-gray-50">
      <Sidebar open={navOpen} onClose={closeNav} />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopNav onMenuClick={() => setNavOpen(true)} />
        <main className="w-full flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
      <Chatbot />
    </div>
  );
}
