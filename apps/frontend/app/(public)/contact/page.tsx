import { Mail, MessageSquare } from 'lucide-react';

export default function ContactPage() {
  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
      <h1 className="text-4xl font-bold text-ink mb-4">Contact Us</h1>
      <p className="text-lg text-ink-muted mb-10">
        Have a question, feedback, or want to partner with us? We&apos;d love to hear from you.
      </p>

      <div className="space-y-8">
        <div className="flex items-start gap-4 p-6 bg-white rounded-xl border border-warm-grey">
          <div className="w-12 h-12 bg-gold/10 rounded-xl flex items-center justify-center shrink-0">
            <Mail className="h-6 w-6 text-gold-dark" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-ink mb-1">General Inquiries</h2>
            <p className="text-ink-muted mb-2">For questions about BuyAnything or how we work.</p>
            <a href="mailto:hello@buyanything.ai" className="text-accent-blue hover:underline font-medium">
              hello@buyanything.ai
            </a>
          </div>
        </div>

        <div className="flex items-start gap-4 p-6 bg-white rounded-xl border border-warm-grey">
          <div className="w-12 h-12 bg-status-success/10 rounded-xl flex items-center justify-center shrink-0">
            <MessageSquare className="h-6 w-6 text-status-success" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-ink mb-1">Vendor Partnerships</h2>
            <p className="text-ink-muted mb-2">Want to join our vendor network? We work with businesses of all sizes.</p>
            <a href="mailto:vendors@buyanything.ai" className="text-accent-blue hover:underline font-medium">
              vendors@buyanything.ai
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
