'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Building2, CheckCircle, Loader2, Bug } from 'lucide-react';
import { getToken } from '../../utils/auth';
import ReportBugModal from '../../components/ReportBugModal';
import { useShoppingStore } from '../../store';

const CATEGORIES = [
  { slug: 'electronics', label: 'Electronics' },
  { slug: 'private_aviation', label: 'Private Aviation' },
  { slug: 'automotive', label: 'Automotive' },
  { slug: 'real_estate', label: 'Real Estate' },
  { slug: 'catering', label: 'Catering & Events' },
  { slug: 'travel', label: 'Travel & Hospitality' },
  { slug: 'professional_services', label: 'Professional Services' },
  { slug: 'home_improvement', label: 'Home Improvement' },
  { slug: 'fashion', label: 'Fashion & Apparel' },
  { slug: 'other', label: 'Other' },
];

const INPUT_CLASS = 'w-full px-4 py-2 border border-gray-300 rounded-lg text-ink placeholder:text-ink-muted focus:ring-2 focus:ring-agent-blurple/30 focus:border-agent-blurple';
const LABEL_CLASS = 'block text-sm font-medium text-ink mb-1';

export default function MerchantRegisterPage() {
  const setReportBugModalOpen = useShoppingStore(state => state.setReportBugModalOpen);
  const [businessName, setBusinessName] = useState('');
  const [contactName, setContactName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [website, setWebsite] = useState('');
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleCategory = (slug: string) => {
    setSelectedCategories((prev) =>
      prev.includes(slug) ? prev.filter((c) => c !== slug) : [...prev, slug]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const token = getToken();
      if (!token) {
        setError('Please log in before registering as a seller.');
        setSubmitting(false);
        return;
      }

      const res = await fetch('/api/merchants/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          business_name: businessName,
          contact_name: contactName,
          email,
          phone: phone || null,
          website: website || null,
          categories: selectedCategories,
          service_areas: ['nationwide'],
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Registration failed');
      }

      setSuccess(true);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Registration failed';
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-gray-50 text-ink flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
          <CheckCircle className="mx-auto text-emerald-500 mb-4" size={48} />
          <h1 className="text-2xl font-bold text-ink mb-2">Registration Received!</h1>
          <p className="text-ink-muted mb-6">
            Thank you for registering. We&apos;ll review your application and contact you
            within 1-2 business days.
          </p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 bg-agent-blurple text-white px-6 py-2 rounded-lg font-medium hover:bg-agent-blurple/90 transition-colors"
          >
            Back to Home
          </Link>
        </div>
        <ReportBugModal />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 text-ink py-8 px-4">
      <div className="max-w-lg mx-auto">
        {/* Brand header */}
        <div className="text-center mb-6">
          <Link href="/" className="inline-flex items-center gap-2 text-agent-blurple font-bold text-lg hover:opacity-80 transition-opacity">
            Shopping Agent
          </Link>
        </div>

        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="flex items-center gap-3 mb-6">
            <div className="bg-agent-blurple/10 p-2 rounded-lg">
              <Building2 className="text-agent-blurple" size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-ink">Join Our Seller Network</h1>
              <p className="text-sm text-ink-muted">
                Register to receive RFQs from buyers looking for your services
              </p>
            </div>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg mb-6">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className={LABEL_CLASS}>
                Business Name *
              </label>
              <input
                type="text"
                value={businessName}
                onChange={(e) => setBusinessName(e.target.value)}
                className={INPUT_CLASS}
                placeholder="Acme Corp"
                required
              />
            </div>

            <div>
              <label className={LABEL_CLASS}>
                Contact Name *
              </label>
              <input
                type="text"
                value={contactName}
                onChange={(e) => setContactName(e.target.value)}
                className={INPUT_CLASS}
                placeholder="John Doe"
                required
              />
            </div>

            <div>
              <label className={LABEL_CLASS}>
                Email *
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={INPUT_CLASS}
                placeholder="john@acme.com"
                required
              />
            </div>

            <div>
              <label className={LABEL_CLASS}>
                Phone
              </label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className={INPUT_CLASS}
                placeholder="+1 (555) 123-4567"
              />
            </div>

            <div>
              <label className={LABEL_CLASS}>
                Website
              </label>
              <input
                type="url"
                value={website}
                onChange={(e) => setWebsite(e.target.value)}
                className={INPUT_CLASS}
                placeholder="https://acme.com"
              />
            </div>

            <div>
              <label className={`${LABEL_CLASS} !mb-2`}>
                Categories (select all that apply) *
              </label>
              <div className="grid grid-cols-2 gap-2">
                {CATEGORIES.map((cat) => (
                  <button
                    key={cat.slug}
                    type="button"
                    onClick={() => toggleCategory(cat.slug)}
                    className={`px-3 py-2 text-sm rounded-lg border transition-colors ${
                      selectedCategories.includes(cat.slug)
                        ? 'bg-agent-blurple/10 border-agent-blurple/40 text-agent-blurple font-medium'
                        : 'border-gray-200 text-ink-muted hover:border-gray-300 hover:text-ink'
                    }`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting || !businessName || !contactName || !email || selectedCategories.length === 0}
              className="w-full bg-agent-blurple text-white py-3 rounded-lg font-medium hover:bg-agent-blurple/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {submitting ? (
                <>
                  <Loader2 className="animate-spin" size={16} />
                  Submitting...
                </>
              ) : (
                'Register as Seller'
              )}
            </button>
          </form>
        </div>

        {/* Footer with bug reporter */}
        <div className="mt-6 text-center">
          <button
            onClick={() => setReportBugModalOpen(true)}
            className="inline-flex items-center gap-1.5 text-xs text-ink-muted hover:text-ink transition-colors"
          >
            <Bug size={12} />
            Report a Bug
          </button>
        </div>
      </div>

      <ReportBugModal />
    </div>
  );
}
