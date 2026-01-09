/**
 * Navigation component for RecipeNow
 */
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

export function Navigation() {
  const pathname = usePathname()

  const isActive = (path: string) => pathname === path

  return (
    <nav className="bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link href="/" className="flex items-center space-x-2 font-bold text-xl text-gray-900">
              <span>🍳</span>
              <span>RecipeNow</span>
            </Link>
          </div>

          {/* Navigation links */}
          <div className="flex items-center space-x-1">
            <Link
              href="/"
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive('/')
                  ? 'bg-blue-100 text-blue-900'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`}
            >
              Home
            </Link>

            <Link
              href="/library"
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive('/library')
                  ? 'bg-blue-100 text-blue-900'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`}
            >
              📚 Library
            </Link>

            <Link
              href="/upload"
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive('/upload')
                  ? 'bg-blue-100 text-blue-900'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`}
            >
              ⬆️ Upload
            </Link>

            <Link
              href="/pantry"
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive('/pantry')
                  ? 'bg-blue-100 text-blue-900'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`}
            >
              🥘 Pantry
            </Link>
          </div>

          {/* User menu placeholder */}
          <div className="flex items-center space-x-2">
            <button className="px-3 py-2 rounded-md text-sm font-medium text-gray-600 hover:bg-gray-100">
              👤 Demo User
            </button>
          </div>
        </div>
      </div>
    </nav>
  )
}
