import { Search, Zap, CheckCircle } from 'lucide-react';

export default function HowItWorksPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
      <h1 className="text-4xl font-bold text-gray-900 text-center mb-4">How BuyAnything Works</h1>
      <p className="text-lg text-gray-600 text-center mb-16 max-w-2xl mx-auto">
        We help you find and buy anything — from everyday products to hard-to-source services — all in one place.
      </p>

      <div className="space-y-16">
        <div className="flex flex-col md:flex-row items-center gap-8">
          <div className="w-20 h-20 bg-blue-100 rounded-2xl flex items-center justify-center shrink-0">
            <Search className="h-10 w-10 text-blue-600" />
          </div>
          <div>
            <h2 className="text-2xl font-semibold text-gray-900 mb-3">1. Tell us what you need</h2>
            <p className="text-gray-600 leading-relaxed">
              Type any request in natural language — &ldquo;Roblox gift cards under $50,&rdquo; &ldquo;a caterer for 50 people in San Francisco,&rdquo; or &ldquo;charter a light jet from Nashville to Aspen.&rdquo; Our AI understands context, constraints, and what you&apos;re really looking for — not just keywords.
            </p>
          </div>
        </div>

        <div className="flex flex-col md:flex-row items-center gap-8">
          <div className="w-20 h-20 bg-blue-100 rounded-2xl flex items-center justify-center shrink-0">
            <Zap className="h-10 w-10 text-blue-600" />
          </div>
          <div>
            <h2 className="text-2xl font-semibold text-gray-900 mb-3">2. We search everywhere simultaneously</h2>
            <p className="text-gray-600 leading-relaxed">
              We search major retailers (Amazon, eBay, Google Shopping) and our network of 3,000+ vendors at the same time. Each retailer gets an intelligently tailored query — not the same generic search string. Results are ranked by how well they match your actual needs, not just by keyword overlap.
            </p>
          </div>
        </div>

        <div className="flex flex-col md:flex-row items-center gap-8">
          <div className="w-20 h-20 bg-blue-100 rounded-2xl flex items-center justify-center shrink-0">
            <CheckCircle className="h-10 w-10 text-blue-600" />
          </div>
          <div>
            <h2 className="text-2xl font-semibold text-gray-900 mb-3">3. You choose</h2>
            <p className="text-gray-600 leading-relaxed">
              For everyday products, click &ldquo;Buy&rdquo; and go straight to the retailer. For services and specialty items, click &ldquo;Request Quote&rdquo; and we connect you with the right vendor. We make the introduction — you make the decision. No pressure, no hidden fees, no middleman markup.
            </p>
          </div>
        </div>
      </div>

      <div className="mt-16 text-center">
        <a
          href="/search"
          className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-full transition-colors"
        >
          <Search className="h-4 w-4" />
          Try it now
        </a>
      </div>
    </div>
  );
}
