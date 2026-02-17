export default function AboutPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
      <h1 className="text-4xl font-bold text-gray-900 mb-8">About BuyAnything</h1>

      <div className="prose prose-gray max-w-none">
        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Our Mission</h2>
        <p className="text-gray-600 leading-relaxed mb-6">
          BuyAnything exists to eliminate the friction of finding and buying anything — whether it&apos;s a $25 gift card or a $25 million yacht. We believe the process of procurement shouldn&apos;t require stitching together dozens of platforms, sending cold emails, or settling for whatever shows up on page one of a search engine.
        </p>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">The Problem We Solve</h2>
        <p className="text-gray-600 leading-relaxed mb-6">
          Today, buying anything beyond commodity products is fragmented and frustrating. Need a caterer for a corporate event? You&apos;re googling, reading reviews on five different sites, emailing strangers, and hoping someone responds. Need a custom piece of jewelry? Good luck finding the right artisan without word-of-mouth. Even buying everyday products means comparing prices across Amazon, eBay, and specialty retailers manually.
        </p>
        <p className="text-gray-600 leading-relaxed mb-6">
          We built BuyAnything to fix this. One search, every source, intelligently ranked by what you actually need.
        </p>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">How We&apos;re Different</h2>
        <ul className="space-y-3 text-gray-600 mb-6">
          <li className="flex items-start gap-2">
            <span className="text-blue-600 font-bold mt-0.5">•</span>
            <span><strong>We search everything simultaneously</strong> — retail APIs and our vendor network run in parallel, not sequentially.</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-blue-600 font-bold mt-0.5">•</span>
            <span><strong>Each retailer gets a tailored query</strong> — we don&apos;t send the same search string everywhere. Our AI adapts the query to each provider&apos;s language.</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-blue-600 font-bold mt-0.5">•</span>
            <span><strong>We rank by intent, not keywords</strong> — our scoring system understands that when you ask for &ldquo;a caterer for 50 people,&rdquo; you need someone who serves your area and handles that group size, not just someone with &ldquo;caterer&rdquo; in their title.</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-blue-600 font-bold mt-0.5">•</span>
            <span><strong>We&apos;re an introduction platform</strong> — we connect buyers with sellers. We don&apos;t sell anything ourselves, don&apos;t hold inventory, and don&apos;t mark up prices.</span>
          </li>
        </ul>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Our Vendor Network</h2>
        <p className="text-gray-600 leading-relaxed mb-6">
          We work with 3,000+ vendors across every tier — from mom-and-pop shops and local artisans to specialized B2B suppliers and premium service providers. Our vendor directory spans every category imaginable, and it&apos;s growing every day.
        </p>

        <div className="mt-12 text-center">
          <a
            href="/search"
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-full transition-colors"
          >
            Start searching
          </a>
        </div>
      </div>
    </div>
  );
}
