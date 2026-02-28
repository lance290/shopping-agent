'use client';

import { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';

const HERO_FEATURES = [
  {
    icon: '💬',
    title: 'Text Your List',
    desc: 'Just text or email Pop what you need. Pop builds a shared family list automatically.',
  },
  {
    icon: '💰',
    title: 'Instant Savings',
    desc: 'Pop finds coupons, BOGOs, and brand deals for every item on your list.',
  },
  {
    icon: '🧾',
    title: 'Snap & Earn',
    desc: 'Photo your receipt after shopping. Pop verifies and adds savings to your wallet.',
  },
  {
    icon: '👨‍👩‍👧‍👦',
    title: 'Family Sync',
    desc: 'Everyone in the family adds to one list. No more duplicate trips.',
  },
];

const HOW_IT_WORKS = [
  { step: '1', title: 'Add Pop to your group chat', desc: 'Text, email, or chat with Pop on the web. Add your family members too.' },
  { step: '2', title: 'Build your list naturally', desc: '"We need milk" → Pop adds it. "Get eggs and bread" → done. Just talk normally.' },
  { step: '3', title: 'See instant savings', desc: 'Pop shows swaps and deals under each item. Tap to claim before you shop.' },
  { step: '4', title: 'Shop & earn', desc: 'Buy the swapped item, snap your receipt, and Pop adds cash to your wallet.' },
];

export default function PopHomePage() {
  const [phone, setPhone] = useState('');

  return (
    <div className="min-h-screen bg-white">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <Image src="/pop-avatar.png" alt="Pop" width={36} height={36} className="rounded-full" />
            <span className="text-xl font-bold text-green-700">Pop</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/chat" className="text-sm text-gray-600 hover:text-green-700 transition-colors">
              Chat with Pop
            </Link>
            <Link
              href="/login"
              className="text-sm bg-green-600 text-white px-4 py-2 rounded-full hover:bg-green-700 transition-colors"
            >
              Sign Up Free
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-green-50 via-white to-emerald-50" />
        <div className="relative max-w-6xl mx-auto px-4 pt-20 pb-28 text-center">
          <div className="mb-6">
            <Image src="/pop-avatar.png" alt="Pop" width={80} height={80} className="rounded-full mx-auto shadow-lg border-4 border-white" />
          </div>
          <div className="inline-flex items-center gap-2 bg-green-100 text-green-800 text-sm font-medium px-4 py-1.5 rounded-full mb-6">
            <span>🎉</span> Save $10–20/week on groceries
          </div>
          <h1 className="text-5xl sm:text-6xl font-extrabold text-gray-900 leading-tight max-w-3xl mx-auto">
            Your family&apos;s AI
            <span className="text-green-600"> grocery savings </span>
            assistant
          </h1>
          <p className="mt-6 text-xl text-gray-600 max-w-2xl mx-auto">
            Pop lives in your group chat. Text what you need, Pop finds the best deals,
            and you earn money back on every shopping trip.
          </p>
          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/chat"
              className="w-full sm:w-auto bg-green-600 text-white text-lg font-semibold px-8 py-4 rounded-2xl hover:bg-green-700 transition-all shadow-lg shadow-green-600/20 hover:shadow-green-600/30"
            >
              Try Pop Now — It&apos;s Free
            </Link>
            <a
              href="#how-it-works"
              className="w-full sm:w-auto text-gray-600 text-lg font-medium px-8 py-4 rounded-2xl border border-gray-200 hover:border-green-300 hover:text-green-700 transition-all"
            >
              See How It Works
            </a>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20 bg-white">
        <div className="max-w-6xl mx-auto px-4">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-4">
            Save money without the effort
          </h2>
          <p className="text-center text-gray-500 mb-14 max-w-xl mx-auto">
            Pop does the coupon hunting so you don&apos;t have to. Just shop your list.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-8">
            {HERO_FEATURES.map((f) => (
              <div
                key={f.title}
                className="bg-gray-50 rounded-2xl p-6 hover:bg-green-50 transition-colors group"
              >
                <span className="text-4xl block mb-4 group-hover:scale-110 transition-transform">
                  {f.icon}
                </span>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">{f.title}</h3>
                <p className="text-sm text-gray-600 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="py-20 bg-gradient-to-b from-green-50/50 to-white">
        <div className="max-w-4xl mx-auto px-4">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-14">
            How Pop works
          </h2>
          <div className="space-y-10">
            {HOW_IT_WORKS.map((item) => (
              <div key={item.step} className="flex gap-6 items-start">
                <div className="flex-shrink-0 w-12 h-12 bg-green-600 text-white rounded-2xl flex items-center justify-center text-xl font-bold">
                  {item.step}
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-1">{item.title}</h3>
                  <p className="text-gray-600">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Chat Demo / CTA */}
      <section className="py-20 bg-white">
        <div className="max-w-3xl mx-auto px-4 text-center">
          <div className="bg-gray-900 rounded-3xl p-8 sm:p-12 text-white">
            <h2 className="text-3xl font-bold mb-4">Try Pop right now</h2>
            <p className="text-gray-400 mb-8">
              No signup required. Just tell Pop what you need from the store.
            </p>
            <Link
              href="/chat"
              className="inline-block bg-green-500 text-white text-lg font-semibold px-10 py-4 rounded-2xl hover:bg-green-400 transition-all"
            >
              💬 Chat with Pop
            </Link>
          </div>
        </div>
      </section>

      {/* Phone Signup */}
      <section className="py-16 bg-green-50">
        <div className="max-w-xl mx-auto px-4 text-center">
          <h3 className="text-2xl font-bold text-gray-900 mb-3">Get Pop on your phone</h3>
          <p className="text-gray-600 mb-6">
            Enter your phone number to sign up and start building your family list.
          </p>
          <form
            className="flex gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              window.location.href = `/login?phone=${encodeURIComponent(phone)}&brand=pop`;
            }}
          >
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+1 (555) 000-0000"
              className="flex-1 px-5 py-3 rounded-xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 text-gray-900"
              required
            />
            <button
              type="submit"
              className="bg-green-600 text-white font-semibold px-6 py-3 rounded-xl hover:bg-green-700 transition-colors"
            >
              Get Started
            </button>
          </form>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-10 bg-white border-t border-gray-100">
        <div className="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-gray-500">
          <div className="flex items-center gap-2">
            <Image src="/pop-avatar.png" alt="Pop" width={24} height={24} className="rounded-full" />
            <span className="font-semibold text-gray-700">Pop</span>
            <span>by BuyAnything</span>
          </div>
          <div className="flex gap-6">
            <Link href="/privacy" className="hover:text-green-700 transition-colors">Privacy</Link>
            <Link href="/terms" className="hover:text-green-700 transition-colors">Terms</Link>
            <a href="mailto:pop@popsavings.com" className="hover:text-green-700 transition-colors">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
