'use client';

import { useParams } from 'next/navigation';
import { getGuideBySlug } from '../guide-data';
import AffiliateDisclosure from '../../../../components/AffiliateDisclosure';
import { Search, BookOpen, Clock, User } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function GuidePage() {
  const params = useParams();
  const slug = params?.slug as string;
  const guide = getGuideBySlug(slug);
  const router = useRouter();

  if (!guide) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-20 text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Guide Not Found</h1>
        <p className="text-gray-500 mb-6">The guide you&apos;re looking for doesn&apos;t exist.</p>
        <a href="/guides" className="text-blue-600 hover:underline">Browse all guides</a>
      </div>
    );
  }

  const hasAffiliateLinks = guide.sections.some(
    (s) => (s.affiliateLinks && s.affiliateLinks.length > 0) || s.searchCta
  );

  return (
    <article className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <header className="mb-10">
        <a href="/guides" className="text-sm text-blue-600 hover:underline mb-4 inline-block">← All Guides</a>
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4 leading-tight">{guide.title}</h1>
        <p className="text-lg text-gray-600 mb-4">{guide.description}</p>
        <div className="flex items-center gap-4 text-sm text-gray-400">
          <span className="flex items-center gap-1"><User size={14} /> {guide.author}</span>
          <span className="flex items-center gap-1"><Clock size={14} /> {guide.readTime}</span>
          <span className="flex items-center gap-1"><BookOpen size={14} /> {guide.date}</span>
        </div>
      </header>

      {hasAffiliateLinks && (
        <AffiliateDisclosure className="mb-8" />
      )}

      <div className="space-y-10">
        {guide.sections.map((section, idx) => (
          <section key={idx}>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">{section.heading}</h2>
            <div className="text-gray-600 leading-relaxed whitespace-pre-line">{section.content}</div>

            {section.affiliateLinks && section.affiliateLinks.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2">
                {section.affiliateLinks.map((link, i) => (
                  <button
                    key={i}
                    onClick={() => router.push(`/search?q=${encodeURIComponent(link.query)}`)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 text-sm rounded-full transition-colors"
                  >
                    <Search size={12} />
                    {link.text}
                  </button>
                ))}
              </div>
            )}

            {section.searchCta && (
              <div className="mt-4">
                <button
                  onClick={() => {
                    if (section.searchCta!.query) {
                      router.push(`/search?q=${encodeURIComponent(section.searchCta!.query)}`);
                    } else {
                      router.push('/search');
                    }
                  }}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-full transition-colors"
                >
                  <Search size={14} />
                  {section.searchCta.label}
                </button>
              </div>
            )}
          </section>
        ))}
      </div>

      <footer className="mt-12 pt-8 border-t border-gray-200">
        <div className="bg-gray-50 rounded-xl p-6 text-center">
          <h3 className="font-semibold text-gray-900 mb-2">Ready to find what you need?</h3>
          <p className="text-sm text-gray-500 mb-4">Search across retailers and our vendor network simultaneously.</p>
          <button
            onClick={() => router.push('/search')}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-full transition-colors"
          >
            <Search size={16} />
            Try our search
          </button>
        </div>
        {hasAffiliateLinks && (
          <AffiliateDisclosure className="mt-6" />
        )}
      </footer>
    </article>
  );
}
