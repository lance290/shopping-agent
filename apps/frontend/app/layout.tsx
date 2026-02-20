import type { Metadata } from 'next';
import Script from 'next/script';
import './globals.css';
import DiagnosticsInit from './components/DiagnosticsInit';

export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  title: 'Shopping Agent',
  description: 'AI-powered procurement assistant',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans bg-canvas text-onyx">
        <DiagnosticsInit />
        {children}
        {/* Skimlinks affiliate link conversion */}
        <Script
          src="https://s.skimresources.com/js/299029X1786654.skimlinks.js"
          strategy="afterInteractive"
        />
      </body>
    </html>
  );
}
