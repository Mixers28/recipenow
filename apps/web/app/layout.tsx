import type { Metadata } from 'next'
import './globals.css'
import { Navigation } from '@/components/Navigation'
import { BottomNav } from '@/components/BottomNav'

export const metadata: Metadata = {
  title: 'RecipeNow',
  description: 'Convert recipe media into canonical recipes with provenance tracking',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <Navigation />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 pb-20 lg:pb-8">
          {children}
        </main>
        {/* Bottom navigation - mobile only */}
        <div className="lg:hidden">
          <BottomNav />
        </div>
      </body>
    </html>
  )
}
