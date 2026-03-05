import Link from 'next/link';
import AffiliateDisclosure from './AffiliateDisclosure';

export default function PublicFooter() {
  return (
    <footer className="bg-navy text-white/50 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          <div>
            <h3 className="text-sm font-semibold text-gold uppercase tracking-wider mb-3">Shop</h3>
            <ul className="space-y-2">
              <li><Link href="/search" className="text-sm hover:text-white transition-colors">Search</Link></li>
              <li><Link href="/vendors" className="text-sm hover:text-white transition-colors">Vendor Directory</Link></li>
              <li><Link href="/guides" className="text-sm hover:text-white transition-colors">Guides</Link></li>
              <li><Link href="/how-it-works" className="text-sm hover:text-white transition-colors">How It Works</Link></li>
            </ul>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gold uppercase tracking-wider mb-3">Company</h3>
            <ul className="space-y-2">
              <li><Link href="/about" className="text-sm hover:text-white transition-colors">About</Link></li>
              <li><Link href="/contact" className="text-sm hover:text-white transition-colors">Contact</Link></li>
            </ul>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gold uppercase tracking-wider mb-3">Legal</h3>
            <ul className="space-y-2">
              <li><Link href="/privacy" className="text-sm hover:text-white transition-colors">Privacy Policy</Link></li>
              <li><Link href="/terms" className="text-sm hover:text-white transition-colors">Terms of Service</Link></li>
              <li><Link href="/disclosure" className="text-sm hover:text-white transition-colors">Affiliate Disclosure</Link></li>
            </ul>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gold uppercase tracking-wider mb-3">Get Started</h3>
            <ul className="space-y-2">
              <li><Link href="/login" className="text-sm hover:text-white transition-colors">Sign In</Link></li>
              <li><Link href="/" className="text-sm hover:text-white transition-colors">Start Shopping</Link></li>
            </ul>
          </div>
        </div>
        <div className="mt-8 pt-8 border-t border-white/10 flex flex-col sm:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-1">
            <span className="text-sm font-bold text-white">Buy</span>
            <span className="text-sm font-bold text-gold">Anything</span>
            <span className="text-xs text-white/50 ml-2">&copy; {new Date().getFullYear()}</span>
          </div>
          <AffiliateDisclosure variant="footer" />
        </div>
      </div>
    </footer>
  );
}
