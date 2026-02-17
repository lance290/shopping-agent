import { guides } from './guide-data';
import { BookOpen } from 'lucide-react';

export default function GuidesIndexPage() {
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">Buying Guides</h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          Expert advice for every purchase — from everyday products to hard-to-find services.
        </p>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {guides.map((guide) => (
          <a
            key={guide.slug}
            href={`/guides/${guide.slug}`}
            className="bg-white rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow border border-gray-100 flex flex-col"
          >
            <div className="flex items-center gap-2 mb-3">
              <BookOpen size={16} className="text-blue-600" />
              <span className="text-xs text-gray-400">{guide.readTime}</span>
            </div>
            <h2 className="font-semibold text-gray-900 mb-2 text-lg">{guide.title}</h2>
            <p className="text-sm text-gray-500 flex-1">{guide.description}</p>
            <div className="mt-4 text-sm font-medium text-blue-600">Read guide →</div>
          </a>
        ))}
      </div>
    </div>
  );
}
