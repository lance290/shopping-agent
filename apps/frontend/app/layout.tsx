import type { Metadata } from 'next';
import Script from 'next/script';
import './globals.css';

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
      <body>
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
