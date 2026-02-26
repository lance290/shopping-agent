'use client';

import { useState } from 'react';

export default function ContactForm() {
  const [status, setStatus] = useState<'idle' | 'submitting' | 'success'>('idle');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setStatus('submitting');
    setTimeout(() => setStatus('success'), 1000);
  };

  if (status === 'success') {
    return (
      <div className="p-8 rounded-2xl bg-[#2B2F33] border border-status-success/30 text-center">
        <div className="w-12 h-12 bg-status-success/20 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-6 h-6 text-status-success" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h4 className="text-lg font-semibold text-white mb-2">Message Sent</h4>
        <p className="text-sm text-onyx-muted">
          Thanks for reaching out. Our concierge team will get back to you shortly.
        </p>
      </div>
    );
  }

  return (
    <div className="p-8 rounded-2xl bg-[#2B2F33] border border-white/10">
      <h3 className="text-xl font-semibold text-white mb-2">Speak to our concierge</h3>
      <p className="text-sm text-onyx-muted mb-6">
        Need help sourcing something specific? Reach out to our team directly.
      </p>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-onyx-muted mb-1.5 uppercase tracking-wide">Name</label>
            <input 
              required 
              type="text" 
              className="w-full bg-[#171717] border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white focus:outline-none focus:border-agent-blurple transition-colors" 
              placeholder="Jane Doe"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-onyx-muted mb-1.5 uppercase tracking-wide">Email</label>
            <input 
              required 
              type="email" 
              className="w-full bg-[#171717] border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white focus:outline-none focus:border-agent-blurple transition-colors" 
              placeholder="jane@example.com"
            />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-onyx-muted mb-1.5 uppercase tracking-wide">How can we help?</label>
          <textarea 
            required 
            rows={4} 
            className="w-full bg-[#171717] border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white focus:outline-none focus:border-agent-blurple transition-colors resize-none"
            placeholder="I'm looking to source..."
          />
        </div>
        <button 
          disabled={status === 'submitting'} 
          type="submit" 
          className="w-full py-3 px-4 bg-white text-black font-semibold rounded-lg hover:bg-white/90 transition-colors disabled:opacity-50 mt-2"
        >
          {status === 'submitting' ? 'Sending...' : 'Send Message'}
        </button>
      </form>
    </div>
  );
}
