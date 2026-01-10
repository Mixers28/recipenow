/**
 * Mobile hamburger menu - slide-out drawer navigation
 */
'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Z_INDEX } from '@/lib/constants'

const navLinks = [
  { href: '/', label: 'Home', icon: '🏠' },
  { href: '/library', label: 'Library', icon: '📚' },
  { href: '/upload', label: 'Upload', icon: '⬆️' },
  { href: '/pantry', label: 'Pantry', icon: '🥘' },
  { href: '/match', label: 'Match', icon: '🔍' },
]

interface MobileNavProps {
  isOpen: boolean
  onClose: () => void
}

export function MobileNav({ isOpen, onClose }: MobileNavProps) {
  const pathname = usePathname()

  return (
    <>
      {/* Overlay backdrop */}
      {isOpen && (
        <div
          className={`fixed inset-0 bg-black bg-opacity-50 z-[${Z_INDEX.overlay}] transition-opacity duration-200`}
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Drawer menu */}
      <nav
        className={`fixed left-0 top-0 h-full w-64 bg-white shadow-lg z-[${Z_INDEX.mobileNav}] transition-transform duration-300 ease-out transform ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        aria-label="Mobile navigation"
      >
        {/* Close button */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">RecipeNow</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
            aria-label="Close menu"
          >
            ✕
          </button>
        </div>

        {/* Navigation links */}
        <div className="flex flex-col">
          {navLinks.map((link) => {
            const isActive = pathname === link.href
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={onClose}
                className={`flex items-center space-x-3 px-4 py-4 text-base font-medium transition-colors min-h-touch ${
                  isActive
                    ? 'bg-blue-50 text-blue-600 border-l-4 border-blue-600'
                    : 'text-gray-700 hover:bg-gray-50 border-l-4 border-transparent'
                }`}
              >
                <span className="text-xl">{link.icon}</span>
                <span>{link.label}</span>
              </Link>
            )
          })}
        </div>

        {/* Footer info */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 text-center text-xs text-gray-500">
          <p>RecipeNow v0.1.0</p>
        </div>
      </nav>
    </>
  )
}
