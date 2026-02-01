'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';

interface QuoteFormData {
  row_id: number;
  row_title: string;
  buyer_request: string;
  choice_factors: Array<{ name: string; label: string; type: string }>;
  seller_email: string;
  seller_company: string | null;
  expires_at: string | null;
}

export default function QuotePage() {
  const params = useParams();
  const router = useRouter();
  const token = params.token as string;

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [formData, setFormData] = useState<QuoteFormData | null>(null);

  // Form state
  const [price, setPrice] = useState('');
  const [description, setDescription] = useState('');
  const [aircraftType, setAircraftType] = useState('');
  const [includesCatering, setIncludesCatering] = useState(false);
  const [contactName, setContactName] = useState('');
  const [contactPhone, setContactPhone] = useState('');

  useEffect(() => {
    async function loadFormData() {
      try {
        const res = await fetch(`/api/quotes/form/${token}`);
        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.detail || 'Invalid or expired link');
        }
        const data = await res.json();
        setFormData(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    loadFormData();
  }, [token]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!price || !description) {
      setError('Please fill in all required fields');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const res = await fetch(`/api/quotes/submit/${token}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          price: parseFloat(price),
          currency: 'USD',
          description,
          aircraft_type: aircraftType || null,
          includes_catering: includesCatering,
          availability_confirmed: true,
          contact_name: contactName || null,
          contact_phone: contactPhone || null,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to submit quote');
      }

      setSuccess(true);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error && !formData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
          <div className="text-red-500 text-5xl mb-4">⚠️</div>
          <h1 className="text-xl font-bold text-gray-900 mb-2">Link Error</h1>
          <p className="text-gray-600">{error}</p>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
          <div className="text-green-500 text-5xl mb-4">✅</div>
          <h1 className="text-xl font-bold text-gray-900 mb-2">Quote Submitted!</h1>
          <p className="text-gray-600 mb-4">
            Thank you for your quote. The buyer will be notified and may reach out soon.
          </p>
          <p className="text-sm text-gray-500">You can close this window.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="bg-blue-100 p-2 rounded-lg">
              <span className="text-2xl">✈️</span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Submit Your Quote</h1>
              <p className="text-sm text-gray-500">
                {formData?.seller_company || 'Vendor'}
              </p>
            </div>
          </div>

          <div className="bg-blue-50 rounded-lg p-4">
            <h2 className="font-semibold text-gray-900 mb-2">📋 Request Details</h2>
            <p className="text-gray-700">{formData?.buyer_request}</p>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Your Quote</h2>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}

          {/* Price */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Price (USD) *
            </label>
            <div className="relative">
              <span className="absolute left-3 top-2 text-gray-500">$</span>
              <input
                type="number"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                className="w-full pl-8 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="12,500"
                required
              />
            </div>
          </div>

          {/* Aircraft Type (for private jet demo) */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Aircraft Type
            </label>
            <input
              type="text"
              value={aircraftType}
              onChange={(e) => setAircraftType(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="e.g., Citation XLS, Gulfstream G450"
            />
          </div>

          {/* Description */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              What's Included *
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              rows={4}
              placeholder="Describe what's included in your quote (amenities, services, terms, etc.)"
              required
            />
          </div>

          {/* Includes Catering */}
          <div className="mb-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={includesCatering}
                onChange={(e) => setIncludesCatering(e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Includes catering/refreshments</span>
            </label>
          </div>

          <hr className="my-6" />

          <h3 className="text-md font-semibold mb-4">Contact Information</h3>

          {/* Contact Name */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Contact Name
            </label>
            <input
              type="text"
              value={contactName}
              onChange={(e) => setContactName(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Your name"
            />
          </div>

          {/* Contact Phone */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Contact Phone
            </label>
            <input
              type="tel"
              value={contactPhone}
              onChange={(e) => setContactPhone(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="(555) 123-4567"
            />
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {submitting ? 'Submitting...' : 'Submit Quote'}
          </button>

          <p className="text-xs text-gray-500 mt-4 text-center">
            By submitting, you agree to be contacted by the buyer regarding this request.
          </p>
        </form>
      </div>
    </div>
  );
}
