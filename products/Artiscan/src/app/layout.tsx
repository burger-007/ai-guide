import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { AnalyticsProvider } from '@/components/Analytics';

const inter = Inter({ subsets: ['latin'] });

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
};

export const metadata: Metadata = {
  title: 'Artiscan — Transform Barcodes into Art',
  description: 'Generate beautiful, artistic barcodes and QR codes as SVG. Free, fast, and fully customizable. No signup required.',
  openGraph: {
    title: 'Artiscan — Transform Barcodes into Art',
    description: 'Turn boring barcodes into stunning SVG designs. Free online barcode art generator.',
    type: 'website',
    locale: 'en_US',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className} antialiased`}>
        <AnalyticsProvider>
          {children}
        </AnalyticsProvider>
      </body>
    </html>
  );
}
