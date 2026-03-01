'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import LocationPrompt from '@/components/LocationPrompt';
import { getMe, type AuthMeResponse } from '@/app/utils/auth';

export default function OnboardingPage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthMeResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const me = await getMe();
      if (!me?.authenticated) {
        router.replace('/login');
        return;
      }
      if (me.zip_code) {
        router.replace('/chat');
        return;
      }
      setUser(me);
      setLoading(false);
    })();
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-green-50/50 flex items-center justify-center">
        <div className="animate-pulse text-green-600 text-lg">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-green-50/50 flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-sm border border-green-100 p-8 space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-green-100 mb-4">
            <span className="text-4xl">🛒</span>
          </div>
          <h1 className="text-2xl font-bold text-green-900">Welcome to Pop!</h1>
          <p className="text-gray-600 mt-2">
            {user?.name ? `Hey ${user.name}, one` : 'One'} quick step — let us know where you shop so we can find the best local deals.
          </p>
        </div>

        <LocationPrompt
          onComplete={() => {
            router.push('/chat');
          }}
          onSkip={() => {
            router.push('/chat');
          }}
        />
      </div>

      <p className="text-xs text-gray-400 mt-6 text-center max-w-sm">
        Your location is only used to find nearby grocery stores and local pricing. We never share your exact location.
      </p>
    </div>
  );
}
