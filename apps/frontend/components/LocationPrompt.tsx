'use client';

import React, { useState, useCallback } from 'react';

type LocationState = 'idle' | 'requesting' | 'denied' | 'error' | 'manual' | 'saving' | 'done';

interface LocationPromptProps {
  onComplete: (zipCode: string) => void;
  onSkip?: () => void;
}

export default function LocationPrompt({ onComplete, onSkip }: LocationPromptProps) {
  const [state, setState] = useState<LocationState>('idle');
  const [zipInput, setZipInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [resolvedZip, setResolvedZip] = useState<string | null>(null);

  const saveLocation = useCallback(async (payload: { latitude?: number; longitude?: number; zip_code?: string }) => {
    setState('saving');
    setError(null);
    try {
      const res = await fetch('/api/auth/location', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.error || 'Failed to save location');
      }
      setResolvedZip(data.zip_code);
      setState('done');
      onComplete(data.zip_code);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to save location';
      setError(message);
      setState('manual');
    }
  }, [onComplete]);

  const requestGPS = useCallback(async () => {
    if (!navigator.geolocation) {
      setState('manual');
      return;
    }

    setState('requesting');
    setError(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        saveLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        });
      },
      (err) => {
        if (err.code === err.PERMISSION_DENIED) {
          setState('denied');
        } else {
          setState('error');
          setError('Could not get your location. Please enter your zip code.');
        }
        // Auto-fall to manual after a brief moment
        setTimeout(() => setState('manual'), 1500);
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 }
    );
  }, [saveLocation]);

  const handleZipSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const zip = zipInput.trim();
    if (!/^\d{5}$/.test(zip)) {
      setError('Please enter a valid 5-digit zip code.');
      return;
    }
    saveLocation({ zip_code: zip });
  };

  if (state === 'done') {
    return (
      <div className="text-center py-6">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 mb-4">
          <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <p className="text-lg font-semibold text-green-900">Location set!</p>
        <p className="text-sm text-gray-500 mt-1">Zip code: {resolvedZip}</p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-sm mx-auto">
      {/* GPS prompt */}
      {(state === 'idle' || state === 'requesting') && (
        <div className="text-center space-y-4">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 mb-2">
            <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-green-900">Find stores near you</h3>
          <p className="text-sm text-gray-600">
            We use your location to find the best grocery deals at stores near you.
          </p>
          <button
            onClick={requestGPS}
            disabled={state === 'requesting'}
            className="w-full py-3 px-6 bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white font-medium rounded-xl transition-colors"
          >
            {state === 'requesting' ? (
              <span className="inline-flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Getting location...
              </span>
            ) : (
              'Use my location'
            )}
          </button>
          <button
            onClick={() => setState('manual')}
            className="text-sm text-gray-500 hover:text-gray-700 underline"
          >
            Enter zip code instead
          </button>
        </div>
      )}

      {/* Denied / Error message (briefly shown before falling to manual) */}
      {(state === 'denied' || state === 'error') && (
        <div className="text-center space-y-3">
          <p className="text-sm text-amber-700 bg-amber-50 rounded-lg p-3">
            {state === 'denied'
              ? 'Location permission denied. No problem — enter your zip code below.'
              : error || 'Something went wrong. Please enter your zip code.'}
          </p>
        </div>
      )}

      {/* Manual zip code input */}
      {(state === 'manual' || state === 'saving') && (
        <form onSubmit={handleZipSubmit} className="space-y-4">
          <div className="text-center mb-2">
            <h3 className="text-lg font-semibold text-green-900">Enter your zip code</h3>
            <p className="text-sm text-gray-600 mt-1">
              We&apos;ll find grocery stores and deals near you.
            </p>
          </div>
          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded-lg p-3 text-center">{error}</p>
          )}
          <input
            type="text"
            inputMode="numeric"
            pattern="\d{5}"
            maxLength={5}
            placeholder="e.g. 92130"
            value={zipInput}
            onChange={(e) => {
              setZipInput(e.target.value.replace(/\D/g, ''));
              setError(null);
            }}
            className="w-full text-center text-2xl tracking-widest font-mono py-3 px-4 border-2 border-green-200 focus:border-green-500 focus:ring-2 focus:ring-green-200 rounded-xl outline-none transition-colors"
            autoFocus
          />
          <button
            type="submit"
            disabled={state === 'saving' || zipInput.length < 5}
            className="w-full py-3 px-6 bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white font-medium rounded-xl transition-colors"
          >
            {state === 'saving' ? (
              <span className="inline-flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Saving...
              </span>
            ) : (
              'Continue'
            )}
          </button>
          <button
            type="button"
            onClick={() => { setState('idle'); setError(null); }}
            className="w-full text-sm text-gray-500 hover:text-gray-700 underline"
          >
            Try GPS instead
          </button>
        </form>
      )}

      {/* Skip option */}
      {onSkip && (
        <div className="text-center mt-4">
          <button
            onClick={onSkip}
            className="text-xs text-gray-400 hover:text-gray-600"
          >
            Skip for now
          </button>
        </div>
      )}
    </div>
  );
}
