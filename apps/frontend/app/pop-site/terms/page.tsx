export const metadata = {
  title: "Terms of Service | Pop Savings",
  description: "Terms of Service for Pop Savings.",
};

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-green-50/50 py-12 px-4 sm:px-6 lg:px-8 font-sans text-gray-900">
      <div className="max-w-3xl mx-auto bg-white p-8 md:p-12 rounded-2xl shadow-sm border border-green-100">
        <h1 className="text-3xl font-bold mb-6 text-green-900">Terms of Service</h1>
        <p className="text-sm text-gray-500 mb-8">Last Updated: March 2026</p>

        <div className="space-y-6 text-gray-700 leading-relaxed">
          <section>
            <h2 className="text-xl font-semibold mb-3 text-green-800">1. Acceptance of Terms</h2>
            <p>
              By accessing or using Pop Savings (&ldquo;Service&rdquo;), you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use the Service.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3 text-green-800">2. Description of Service</h2>
            <p>
              Pop Savings provides an AI-powered grocery shopping assistant that helps users build lists, find deals, and earn cash back through brand-sponsored swaps.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3 text-green-800">3. User Accounts</h2>
            <p>
              To use certain features of the Service, you may be required to create an account using your phone number or email address. You are responsible for maintaining the confidentiality of your account credentials.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3 text-green-800">4. Cash Back and Rewards</h2>
            <p>
              Any cash back, rebates, or rewards offered through the Service are subject to verification. We reserve the right to withhold or reverse rewards in cases of suspected fraud, duplicate receipts, or violation of these terms.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3 text-green-800">5. Contact Us</h2>
            <p>
              If you have any questions about these Terms, please contact us at support@popsavings.com.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
