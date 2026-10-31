import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import './globals.css'

export const metadata: Metadata = { title: 'Pi Vaani — Bharosa Layer', description: 'No customer pays twice. No merchant loses a sale.', generator: 'v0.app' }
export const viewport: Viewport = { colorScheme: 'light', themeColor: '#F3F5F9' }

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased" suppressHydrationWarning>
        {children}
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
