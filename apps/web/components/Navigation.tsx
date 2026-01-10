/**
 * Navigation component for RecipeNow
 * Desktop: Horizontal navigation
 * Mobile: Hamburger menu with MobileNav drawer
 */
'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { MobileNav } from './MobileNav'

export function Navigation() {
  const pathname = usePathname()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const isActive = (path: string) => pathname === path

  return (
    <>
      <nav className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <div className="flex items-center flex-shrink-0">
              <Link href="/" className="flex items-center space-x-2 font-bold text-xl text-gray-900">
                <span>🍳</span>
                <span className="hidden sm:inline">RecipeNow</span>
              </Link>
            </div>

            {/* Desktop Navigation links */}
            <div className="hidden lg:flex items-center space-x-1">
              <Link
                href="/"
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors min-h-touch flex items-center ${
                  isActive('/')
                    ? 'bg-blue-100 text-blue-900'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`}
              >
                Home
              </Link>

              <Link
                href="/library"
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors min-h-touch flex items-center ${
                  isActive('/library')
                    ? 'bg-blue-100 text-blue-900'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`}
              >
                📚 Library
              </Link>

              <Link
                href="/upload"
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors min-h-touch flex items-center ${
                  isActive('/upload')
                    ? 'bg-blue-100 text-blue-900'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`}
              >
                ⬆️ Upload
              </Link>

              <Link
                href="/pantry"
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors min-h-touch flex items-center ${
                  isActive('/pantry')
                    ? 'bg-blue-100 text-blue-900'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`}
              >
                🥘 Pantry
              </Link>

              <Link
                href="/match"
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors min-h-touch flex items-center ${
                  isActive('/match')
                    ? 'bg-blue-100 text-blue-900'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`}
              >
                🔍 Match
              </Link>
            </div>

            {/* Right side - User menu (desktop) and hamburger (mobile) */}
            <div className="flex items-center space-x-2">
              {/* Desktop user menu */}
              <button className="hidden lg:block px-3 py-2 rounded-md text-sm font-medium text-gray-600 hover:bg-gray-100 min-h-touch transition-colors">
                👤 Demo User
              </button>

              {/* Mobile hamburger menu button */}
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="lg:hidden p-2 rounded-md text-gray-600 hover:bg-gray-100 transition-colors min-h-touch flex items-center justify-center"
                aria-label="Toggle navigation menu"
                aria-expanded={mobileMenuOpen}
              >
                <span className="text-2xl">{mobileMenuOpen ? '✕' : '☰'}</span>
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Mobile navigation drawer */}
      <MobileNav isOpen={mobileMenuOpen} onClose={() => setMobileMenuOpen(false)} />
    </>
  )
}
