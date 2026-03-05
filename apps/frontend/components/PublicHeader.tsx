'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Search, LayoutGrid } from 'lucide-react';
import Link from 'next/link';
import { getMe } from '../app/utils/auth';

export default function PublicHeader() {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    getMe().then((user) => {
      if (user?.authenticated) setIsAuthenticated(true);
    });
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (trimmed) {
      router.push(`/search?q=${encodeURIComponent(trimmed)}`);
    }
  };

  return (
    <header className="sticky top-0 z-40 bg-navy text-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14 gap-4">
          <Link href="/" className="flex items-center gap-2 shrink-0">
            <span className="text-lg font-bold tracking-tight">BuyAnything</span>
          </Link>

          <form onSubmit={handleSearch} className="flex-1 max-w-xl hidden sm:block">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-navy/40" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="What are you looking for?"
                className="w-full pl-10 pr-4 py-2 border border-white/20 rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-gold focus:border-transparent bg-white/10 text-white placeholder:text-white/50"
              />
            </div>
          </form>

          <div className="flex items-center gap-3 shrink-0">
            {isAuthenticated ? (
              <a
                href="/app"
                className="inline-flex items-center gap-2 text-sm font-medium text-gold-light hover:text-white transition-colors px-3 py-1.5 rounded-full border border-gold/30 hover:border-gold"
              >
                <LayoutGrid size={16} />
                Workspace
              </a>
            ) : (
              <a
                href="/login"
                className="text-sm font-medium text-white/80 hover:text-white transition-colors"
              >
                Sign In
              </a>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
