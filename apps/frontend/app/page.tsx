'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import PublicHeader from '../components/PublicHeader';
import PublicFooter from '../components/PublicFooter';
import { Search } from 'lucide-react';
import { useRouter } from 'next/navigation';

const WorkspaceView = dynamic(() => import('./components/WorkspaceView'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-screen">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
    </div>
  ),
});

import { getMe } from '../utils/auth';

export default function RootPage() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const user = await getMe();
        console.log('[RootPage] Session check:', user ? 'AUTHENTICATED' : 'ANONYMOUS');
        setIsAuthenticated(!!user?.authenticated);
      } catch (err) {
        console.error('[RootPage] Session check failed', err);
        setIsAuthenticated(false);
      }
    };
    checkAuth();
  }, []);

  // Loading state while checking auth
  if (isAuthenticated === null) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  // Logged in → render workspace
  if (isAuthenticated) {
    return <WorkspaceView />;
  }

  // Anonymous → render public homepage
  return <PublicHomePage />;
}

function PublicHomePage() {
  const router = useRouter();
  const [query, setQuery] = useState('');

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (trimmed) {
      router.push(`/search?q=${encodeURIComponent(trimmed)}`);
    }
  };

  const exampleSearches = [
    'Roblox gift cards',
    'local caterers',
    'private jet charter',
    'running shoes',
    'custom jewelry',
  ];

  return (
    <div className="min-h-screen flex flex-col">
      <PublicHeader />
      <main className="flex-1">
        {/* Hero Section */}
        <section className="bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 text-white">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-20 sm:py-28 text-center">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight mb-6">
              Buy <span className="text-blue-200">anything</span>
            </h1>
            <p className="text-lg sm:text-xl text-blue-100 mb-10 max-w-2xl mx-auto">
              From gift cards to private jets. We search every source, rank by what you actually need, and connect you with the right seller.
            </p>

            <form onSubmit={handleSearch} className="max-w-xl mx-auto">
              <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="What are you looking for?"
                  className="w-full pl-12 pr-4 py-4 rounded-full text-gray-900 text-lg shadow-lg focus:outline-none focus:ring-4 focus:ring-blue-300"
                />
              </div>
            </form>

            <div className="mt-6 flex flex-wrap justify-center gap-2">
              <span className="text-sm text-blue-200">Try:</span>
              {exampleSearches.map((example) => (
                <button
                  key={example}
                  onClick={() => router.push(`/search?q=${encodeURIComponent(example)}`)}
                  className="text-sm px-3 py-1 rounded-full bg-white/10 hover:bg-white/20 text-blue-100 transition-colors"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section className="py-16 sm:py-20 bg-white">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">How it works</h2>
            <div className="grid md:grid-cols-3 gap-8">
              <div className="text-center">
                <div className="w-14 h-14 bg-blue-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl font-bold text-blue-600">1</span>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Tell us what you need</h3>
                <p className="text-gray-600">Type any request — from everyday products to hard-to-find services. Our AI understands what you&apos;re really looking for.</p>
              </div>
              <div className="text-center">
                <div className="w-14 h-14 bg-blue-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl font-bold text-blue-600">2</span>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">We find the best options</h3>
                <p className="text-gray-600">We search retail APIs and our vendor network simultaneously, then rank results by how well they match your actual needs.</p>
              </div>
              <div className="text-center">
                <div className="w-14 h-14 bg-blue-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl font-bold text-blue-600">3</span>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">You choose</h3>
                <p className="text-gray-600">Buy directly from retailers or request a quote from vendors. We make the introduction — you make the decision.</p>
              </div>
            </div>
          </div>
        </section>

        {/* Guides Preview */}
        <section className="py-16 sm:py-20 bg-gray-50">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold text-center text-gray-900 mb-4">Explore our guides</h2>
            <p className="text-center text-gray-600 mb-10">Expert buying advice for every category</p>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {[
                { title: 'How BuyAnything Works', slug: 'how-buyanything-works', desc: 'Your complete guide to finding anything' },
                { title: 'Gift Vault: Tech Lovers', slug: 'gift-vault-tech-lovers', desc: 'Curated tech gifts for every budget' },
                { title: 'Best Luggage for Travel', slug: 'best-luggage-for-travel', desc: 'Top-rated luggage reviewed and compared' },
                { title: 'Support Local Vendors', slug: 'support-local-vendors', desc: 'Why and how to buy from local businesses' },
                { title: 'Home Office Setup', slug: 'home-office-setup-guide', desc: 'Everything you need for the perfect workspace' },
              ].map((guide) => (
                <a
                  key={guide.slug}
                  href={`/guides/${guide.slug}`}
                  className="bg-white rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow border border-gray-100"
                >
                  <h3 className="font-semibold text-gray-900 mb-1">{guide.title}</h3>
                  <p className="text-sm text-gray-500">{guide.desc}</p>
                </a>
              ))}
            </div>
          </div>
        </section>
      </main>
      <PublicFooter />
    </div>
  );
}
