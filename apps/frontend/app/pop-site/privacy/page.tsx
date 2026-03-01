export const metadata = {
  title: "Privacy Policy | Pop Savings",
  description: "Privacy Policy for Pop Savings.",
};

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-green-50/50 py-12 px-4 sm:px-6 lg:px-8 font-sans text-gray-900">
      <div className="max-w-3xl mx-auto bg-white p-8 md:p-12 rounded-2xl shadow-sm border border-green-100">
        <h1 className="text-3xl font-bold mb-6 text-green-900">Privacy Policy</h1>
        <p className="text-sm text-gray-500 mb-8">Last Updated: March 2026</p>

        <div className="space-y-6 text-gray-700 leading-relaxed">
          <section>
            <h2 className="text-xl font-semibold mb-3 text-green-800">1. Information We Collect</h2>
            <p>
              We collect information you provide directly to us, such as your phone number, email address, shopping list items, and uploaded receipts. We also collect usage data automatically when you interact with our Service.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3 text-green-800">2. How We Use Your Information</h2>
            <p>
              We use your information to provide and improve the Service, process cash back rewards, understand shopping intent, and communicate with you about brand-sponsored swaps.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3 text-green-800">3. Information Sharing</h2>
            <p>
              We may share aggregated, non-personally identifiable information with brand partners for the purpose of serving relevant swap offers. We do not sell your personal data to third parties.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3 text-green-800">4. Data Security</h2>
            <p>
              We implement reasonable security measures to protect your information, but no method of transmission over the Internet is 100% secure.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3 text-green-800">5. Contact Us</h2>
            <p>
              If you have any questions about this Privacy Policy, please contact us at privacy@popsavings.com.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
