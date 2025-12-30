/**
 * Root Layout for CF-X Dashboard
 * Required by Next.js App Router
 */
import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'CF-X Dashboard',
  description: 'Monitor your AI orchestration usage and performance',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

