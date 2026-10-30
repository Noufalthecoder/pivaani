import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import './globals.css'

export const metadata: Metadata = { title: 'Pi Vaani — Bharosa Layer', description: 'No customer pays twice. No merchant loses a sale.', generator: 'v0.app' }
export const viewport: Viewport = { colorScheme: 'dark', themeColor: '#0A0B0F' }

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body className="antialiased">{children}{process.env.NODE_ENV === 'production' && <Analytics />}</body></html>
}
