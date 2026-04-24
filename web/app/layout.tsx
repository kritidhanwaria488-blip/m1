import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'MF FAQ Assistant',
  description: 'Facts-only mutual fund information assistant',
  keywords: ['mutual funds', 'FAQ', 'HDFC', 'investment information'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased min-h-screen bg-background text-foreground">
        {children}
      </body>
    </html>
  );
}
