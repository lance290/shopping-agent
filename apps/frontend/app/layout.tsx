import type { Metadata } from 'next';
import Script from 'next/script';
import { ClerkProvider } from '@clerk/nextjs';
import './globals.css';

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
    <ClerkProvider>
      <html lang="en">
        <body className="font-sans bg-canvas text-onyx">
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
