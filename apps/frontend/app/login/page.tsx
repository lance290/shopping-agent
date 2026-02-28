'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { startAuth, verifyAuth, setLoggedIn } from '../utils/auth';
import { claimGuestRows } from '../utils/api';
import Image from 'next/image';

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const brand = searchParams.get('brand');
  
  const [mounted, setMounted] = useState(false);
  const [phone, setPhone] = useState(searchParams.get('phone') || '');
  const [code, setCode] = useState('');
  const [step, setStep] = useState<'start' | 'verify'>('start');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const isPop = brand === 'pop';

  useEffect(() => {
    setMounted(true);
  }, []);

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
      setLoggedIn();

      // Claim anonymous rows created before login
      const pendingRaw = sessionStorage.getItem('pending_claim_rows');
      if (pendingRaw) {
        sessionStorage.removeItem('pending_claim_rows');
        try {
          const rowIds: number[] = JSON.parse(pendingRaw);
          if (rowIds.length) await claimGuestRows(rowIds);
        } catch (e) {
          console.error('[Login] Failed to claim guest rows:', e);
        }
      }

      router.push(isPop ? '/?brand=pop' : '/');
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
      <div className="w-full max-w-md bg-white rounded-lg shadow-md p-8">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Loading...</h1>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md bg-white rounded-3xl shadow-sm border border-gray-100 p-8">
      <div className="text-center mb-8">
        {isPop ? (
          <>
            <Image src="/pop-avatar.png" alt="Pop" width={64} height={64} className="rounded-full mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-gray-900">Sign in to Pop</h1>
            <p className="text-gray-600 mt-2">Enter your phone number to continue</p>
          </>
        ) : (
          <>
            <h1 className="text-2xl font-bold text-gray-900">Sign in to Shopping Agent</h1>
            <p className="text-gray-600 mt-2">Enter your phone number to get started</p>
          </>
        )}
      </div>

      {error && (
        <div className="bg-red-50 text-red-600 p-3 rounded-xl mb-6 text-sm">
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
              placeholder="+1 (555) 000-0000"
              className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition-colors"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className={`w-full text-white font-medium py-3 px-4 rounded-xl transition-colors ${
              isPop 
                ? 'bg-green-600 hover:bg-green-700 disabled:bg-green-400' 
                : 'bg-black hover:bg-gray-800 disabled:bg-gray-400'
            }`}
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
              placeholder="000000"
              className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition-colors text-center text-2xl tracking-widest"
              required
              maxLength={6}
              autoFocus
            />
            <p className="text-xs text-gray-500 mt-2 text-center">
              Code sent to {phone}
            </p>
          </div>
          <button
            type="submit"
            disabled={loading}
            className={`w-full text-white font-medium py-3 px-4 rounded-xl transition-colors ${
              isPop 
                ? 'bg-green-600 hover:bg-green-700 disabled:bg-green-400' 
                : 'bg-black hover:bg-gray-800 disabled:bg-gray-400'
            }`}
          >
            {loading ? 'Verifying...' : 'Verify & Sign In'}
          </button>
          <button
            type="button"
            onClick={() => setStep('start')}
            className="w-full text-gray-500 text-sm font-medium hover:text-gray-800"
          >
            Use a different number
          </button>
        </form>
      )}
    </div>
  );
}

export default function LoginPage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <Suspense fallback={<div className="animate-pulse w-32 h-8 bg-gray-200 rounded-lg" />}>
        <LoginForm />
      </Suspense>
    </main>
  );
}
