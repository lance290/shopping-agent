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
    <header className="sticky top-0 z-40">
      {/* Top bar — dark charcoal */}
      <div className="bg-navy text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14 gap-4">
            <Link href="/" className="flex items-center gap-1 shrink-0">
              <span className="text-xl font-bold tracking-tight text-white">Buy</span>
              <span className="text-xl font-bold tracking-tight text-gold">Anything</span>
            </Link>

            <form onSubmit={handleSearch} className="flex-1 max-w-2xl hidden sm:flex">
              <div className="flex w-full">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search products, services, anything..."
                  className="flex-1 px-4 py-2 text-sm text-ink bg-white rounded-l-md border-0 focus:outline-none focus:ring-2 focus:ring-gold placeholder:text-onyx-muted"
                />
                <button
                  type="submit"
                  className="px-4 py-2 bg-gold hover:bg-gold-dark rounded-r-md transition-colors"
                  aria-label="Search"
                >
                  <Search className="h-5 w-5 text-navy" />
                </button>
              </div>
            </form>

            <div className="flex items-center gap-4 shrink-0">
              {isAuthenticated ? (
                <Link
                  href="/app"
                  className="inline-flex items-center gap-2 text-sm font-medium text-white hover:text-gold transition-colors"
                >
                  <LayoutGrid size={16} />
                  <span className="hidden md:inline">Workspace</span>
                </Link>
              ) : (
                <Link
                  href="/login"
                  className="text-sm font-medium text-white hover:text-gold transition-colors"
                >
                  Sign In
                </Link>
              )}
            </div>
          </div>
        </div>
      </div>
      {/* Secondary nav bar */}
      <div className="bg-navy-light text-white text-sm border-t border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-6 h-10 overflow-x-auto scrollbar-hide">
            <Link href="/vendors" className="whitespace-nowrap hover:text-gold transition-colors">Vendors</Link>
            <Link href="/guides" className="whitespace-nowrap hover:text-gold transition-colors">Guides</Link>
            <Link href="/how-it-works" className="whitespace-nowrap hover:text-gold transition-colors">How It Works</Link>
            <Link href="/about" className="whitespace-nowrap hover:text-gold transition-colors">About</Link>
            <Link href="/contact" className="whitespace-nowrap hover:text-gold transition-colors">Contact</Link>
          </div>
        </div>
      </div>
    </header>
  );
}
