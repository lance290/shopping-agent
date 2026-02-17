/**
 * Reusable affiliate disclosure — inline and footer variants.
 * Appears on search results, guides, vendor pages, and public footer.
 */

interface AffiliateDisclosureProps {
  variant?: 'inline' | 'footer';
  className?: string;
}

export default function AffiliateDisclosure({ variant = 'inline', className = '' }: AffiliateDisclosureProps) {
  if (variant === 'footer') {
    return (
      <p className={`text-xs text-gray-400 ${className}`}>
        Some links on this site are affiliate links. We may earn a commission at no extra cost to you.{' '}
        <a href="/disclosure" className="underline hover:text-gray-300">
          Full disclosure
        </a>
      </p>
    );
  }

  return (
    <div className={`text-xs text-gray-500 bg-gray-50 border border-gray-200 rounded-md px-3 py-2 ${className}`}>
      Some links on this page are affiliate links. We may earn a commission at no extra cost to you.{' '}
      <a href="/disclosure" className="underline hover:text-gray-600">
        Learn more
      </a>
    </div>
  );
}
