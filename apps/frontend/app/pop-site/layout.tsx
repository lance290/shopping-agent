import type { Metadata } from 'next';
import { BrandProvider } from '../utils/brand';
import ReportBugModal from '../components/ReportBugModal';
import PopBugReporterTrigger from './components/PopBugReporterTrigger';

export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  title: 'Pop — Save Money on Groceries with AI',
  description:
    'Pop is your AI family shopping assistant. Build shared grocery lists, discover savings, and earn money back on every trip.',
  manifest: '/pop-manifest.json',
  themeColor: '#16a34a',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: 'Pop Savings',
  },
  icons: {
    apple: '/pop-apple-icon.png',
  },
  openGraph: {
    title: 'Pop — Save Money on Groceries with AI',
    description:
      'Build shared grocery lists, discover savings, and earn money back on every trip.',
    siteName: 'Pop Savings',
    type: 'website',
  },
};

export default function PopLayout({ children }: { children: React.ReactNode }) {
  return (
    <BrandProvider brand="pop">
      {children}
      <ReportBugModal />
      <PopBugReporterTrigger />
    </BrandProvider>
  );
}
