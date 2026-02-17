import Link from 'next/link';
import AffiliateDisclosure from './AffiliateDisclosure';

export default function PublicFooter() {
  return (
    <footer className="bg-gray-900 text-gray-300 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          <div>
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-4">Product</h3>
            <ul className="space-y-2">
              <li><a href="/how-it-works" className="text-sm hover:text-white transition-colors">How It Works</a></li>
              <li><a href="/search" className="text-sm hover:text-white transition-colors">Search</a></li>
              <li><Link href="/vendors" className="text-sm hover:text-white transition-colors">Vendor Directory</Link></li>
              <li><Link href="/guides" className="text-sm hover:text-white transition-colors">Guides</Link></li>
            </ul>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-4">Company</h3>
            <ul className="space-y-2">
              <li><a href="/about" className="text-sm hover:text-white transition-colors">About</a></li>
              <li><a href="/contact" className="text-sm hover:text-white transition-colors">Contact</a></li>
            </ul>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-4">Legal</h3>
            <ul className="space-y-2">
              <li><a href="/privacy" className="text-sm hover:text-white transition-colors">Privacy Policy</a></li>
              <li><a href="/terms" className="text-sm hover:text-white transition-colors">Terms of Service</a></li>
              <li><a href="/disclosure" className="text-sm hover:text-white transition-colors">Affiliate Disclosure</a></li>
            </ul>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-4">Get Started</h3>
            <ul className="space-y-2">
              <li><a href="/login" className="text-sm hover:text-white transition-colors">Sign In</a></li>
              <li><a href="/sign-up" className="text-sm hover:text-white transition-colors">Create Account</a></li>
            </ul>
          </div>
        </div>
        <div className="mt-8 pt-8 border-t border-gray-700 flex flex-col sm:flex-row justify-between items-center gap-4">
          <p className="text-xs text-gray-500">&copy; {new Date().getFullYear()} BuyAnything. All rights reserved.</p>
          <AffiliateDisclosure variant="footer" />
        </div>
      </div>
    </footer>
  );
}
