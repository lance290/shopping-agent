export default function PrivacyPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
      <h1 className="text-4xl font-bold text-gray-900 mb-2">Privacy Policy</h1>
      <p className="text-sm text-gray-500 mb-12">Last updated: February 2026</p>

      <div className="prose prose-gray max-w-none space-y-8">
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">1. Information We Collect</h2>
          <p className="text-gray-600 leading-relaxed">
            <strong>Public surface (no account required):</strong> When you search without an account, we do not store your search queries. We log clickout events (which products you click through to buy) with anonymized data including: merchant domain, affiliate handler used, browser user-agent, and a hashed IP address. We do not associate this data with any personal identity.
          </p>
          <p className="text-gray-600 leading-relaxed mt-3">
            <strong>Registered accounts:</strong> When you create an account, we collect your phone number (for authentication), and any information you provide in your procurement requests. Your search history and vendor interactions are stored to provide the workspace experience.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">2. How We Use Your Information</h2>
          <ul className="text-gray-600 space-y-2">
            <li>• To provide search results from retail APIs and our vendor network</li>
            <li>• To facilitate introductions between you and vendors (when you request a quote)</li>
            <li>• To track affiliate clickouts for revenue attribution (anonymized for non-logged-in users)</li>
            <li>• To improve our search ranking and recommendation algorithms</li>
            <li>• To communicate with you about your account and requests</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">3. Affiliate Links & Third-Party Services</h2>
          <p className="text-gray-600 leading-relaxed">
            Some links on BuyAnything are affiliate links. When you click through to a retailer (e.g., Amazon, eBay), the retailer may collect information about your visit according to their own privacy policy. We may earn a commission on qualifying purchases at no additional cost to you. See our <a href="/disclosure" className="text-blue-600 hover:underline">Affiliate Disclosure</a> for details.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">4. Data Sharing</h2>
          <p className="text-gray-600 leading-relaxed">
            We do not sell your personal information. We share data only in these limited circumstances: with vendors you explicitly request an introduction to, with service providers necessary to operate the platform (hosting, email delivery), and when required by law.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">5. Cookies</h2>
          <p className="text-gray-600 leading-relaxed">
            We use a session cookie (<code>sa_session</code>) for authentication. We use the Skimlinks script for universal affiliate link conversion. No tracking cookies are used for non-logged-in users beyond what is necessary for affiliate attribution.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">6. Vendor Privacy</h2>
          <p className="text-gray-600 leading-relaxed">
            Vendor contact information (email addresses, phone numbers) is never displayed on public pages. Only business name, description, and website URL are shown publicly. Contact is facilitated through our platform, not by exposing vendor PII.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">7. Contact</h2>
          <p className="text-gray-600 leading-relaxed">
            For privacy questions, contact us at <a href="mailto:privacy@buyanything.ai" className="text-blue-600 hover:underline">privacy@buyanything.ai</a>.
          </p>
        </section>
      </div>
    </div>
  );
}
