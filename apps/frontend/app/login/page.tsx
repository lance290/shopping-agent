'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { startAuth, verifyAuth } from '../utils/auth';
import { CheckCircle } from 'lucide-react';
import Link from 'next/link';

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isLoggedOut = searchParams.get('logged_out') === '1';
  const [mounted, setMounted] = useState(false);
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [step, setStep] = useState<'start' | 'verify'>('start');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (mounted && isLoggedOut) {
    return (
      <div className="min-h-screen bg-canvas">
      <header className="sticky top-0 z-40 bg-navy text-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center h-14">
            <Link href="/" className="text-lg font-bold tracking-tight">BuyAnything</Link>
          </div>
        </div>
      </header>
      <main className="flex items-center justify-center p-4" style={{ minHeight: 'calc(100vh - 56px)' }}>
        <div className="w-full max-w-md bg-white text-navy rounded-lg shadow-md p-8 text-center">
          <CheckCircle className="w-12 h-12 text-status-success mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-navy mb-2">You&apos;ve been signed out</h1>
          <p className="text-ink-muted mb-6">Thanks for using BuyAnything. See you next time!</p>
          <div className="flex flex-col gap-3">
            <Link
              href="/"
              className="w-full inline-block bg-navy text-white py-2.5 px-4 rounded-md hover:bg-navy-light transition-colors font-medium"
            >
              Back to Home
            </Link>
            <button
              onClick={() => router.replace('/login')}
              className="text-sm text-ink-muted hover:text-navy transition-colors"
            >
              Sign in again
            </button>
          </div>
        </div>
      </main>
      </div>
    );
  }

  const handleStart = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await startAuth(phone);
      setStep('verify');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to send verification code';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await verifyAuth(phone, code);
      router.push('/');
      router.refresh();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Invalid code';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  if (!mounted) {
    return (
      <div className="min-h-screen bg-canvas">
        <header className="sticky top-0 z-40 bg-navy text-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center h-14">
              <Link href="/" className="text-lg font-bold tracking-tight">BuyAnything</Link>
            </div>
          </div>
        </header>
        <main className="flex items-center justify-center p-4" style={{ minHeight: 'calc(100vh - 56px)' }}>
          <div className="w-full max-w-md bg-white text-navy rounded-lg shadow-md p-8">
            <div className="text-center mb-8">
              <h1 className="text-2xl font-bold text-navy">Sign in to BuyAnything</h1>
              <p className="text-ink-muted mt-2">Loading...</p>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-canvas">
      <header className="sticky top-0 z-40 bg-navy text-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center h-14">
            <Link href="/" className="text-lg font-bold tracking-tight">BuyAnything</Link>
          </div>
        </div>
      </header>
    <main className="flex items-center justify-center p-4" style={{ minHeight: 'calc(100vh - 56px)' }}>
      <div className="w-full max-w-md bg-white text-navy rounded-lg shadow-md p-8">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-navy">Sign in to BuyAnything</h1>
          <p className="text-ink-muted mt-2">Enter your phone number to get started</p>
        </div>

        {error && (
          <div className="bg-red-50 text-status-error p-3 rounded-md mb-6 text-sm">
            {error}
          </div>
        )}

        {step === 'start' ? (
          <form onSubmit={handleStart} className="space-y-6">
            <div>
              <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-1">
                Phone number
              </label>
              <input
                id="phone"
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+1 555 555 5555"
                className="w-full bg-white text-gray-900 placeholder:text-gray-400 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gold focus:border-transparent"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-navy text-white py-2 px-4 rounded-md hover:bg-navy-light focus:outline-none focus:ring-2 focus:ring-gold focus:ring-offset-2 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Sending...' : 'Continue'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleVerify} className="space-y-6">
            <div>
              <label htmlFor="code" className="block text-sm font-medium text-gray-700 mb-1">
                Verification Code
              </label>
              <input
                id="code"
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="123456"
                className="w-full bg-white text-gray-900 placeholder:text-gray-400 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gold focus:border-transparent tracking-widest text-lg"
                required
                maxLength={6}
              />
              <p className="mt-2 text-sm text-gray-500">
                Sent to {phone}. <button type="button" onClick={() => setStep('start')} className="text-navy hover:text-navy-light">Change?</button>
              </p>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-navy text-white py-2 px-4 rounded-md hover:bg-navy-light focus:outline-none focus:ring-2 focus:ring-gold focus:ring-offset-2 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Verifying...' : 'Sign In'}
            </button>
          </form>
        )}
      </div>
    </main>
    </div>
  );
}
