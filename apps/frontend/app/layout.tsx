import type { Metadata } from 'next';
import Script from 'next/script';
import { ClerkProvider } from '@clerk/nextjs';
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
  const disableClerk = process.env.NEXT_PUBLIC_DISABLE_CLERK === '1';

  if (disableClerk) {
    return (
      <html lang="en">
        <body className="font-sans bg-canvas text-onyx">
          <DiagnosticsInit />
          {children}
          {/* Skimlinks affiliate link conversion */}
          <Script
            src="https://s.skimresources.com/js/297674X1785170.skimlinks.js"
            strategy="afterInteractive"
          />
        </body>
      </html>
    );
  }

  return (
    <ClerkProvider>
      <html lang="en">
        <body className="font-sans bg-canvas text-onyx">
          <DiagnosticsInit />
          {children}
          {/* Skimlinks affiliate link conversion */}
          <Script
            src="https://s.skimresources.com/js/297674X1785170.skimlinks.js"
            strategy="afterInteractive"
          />
        </body>
      </html>
    </ClerkProvider>
  );
}
