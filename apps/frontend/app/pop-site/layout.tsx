import type { Metadata } from 'next';
import { BrandProvider } from '../utils/brand';

export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  title: 'Pop — Save Money on Groceries with AI',
  description:
    'Pop is your AI family shopping assistant. Build shared grocery lists, discover savings, and earn money back on every trip.',
  openGraph: {
    title: 'Pop — Save Money on Groceries with AI',
    description:
      'Build shared grocery lists, discover savings, and earn money back on every trip.',
    siteName: 'Pop Savings',
    type: 'website',
  },
};

export default function PopLayout({ children }: { children: React.ReactNode }) {
  return <BrandProvider brand="pop">{children}</BrandProvider>;
}
