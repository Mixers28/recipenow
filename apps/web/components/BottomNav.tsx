/**
 * Bottom navigation bar - mobile-only navigation for key actions
 */
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { MOBILE_LAYOUT, Z_INDEX } from '@/lib/constants'

const navItems = [
  { href: '/library', icon: '📚', label: 'Library' },
  { href: '/pantry', icon: '🥘', label: 'Pantry' },
  { href: '/match', icon: '🔍', label: 'Match' },
]

export function BottomNav() {
  const pathname = usePathname()

  return (
    <nav
      className={`fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-[${Z_INDEX.bottomNav}] safe-bottom safe-left safe-right`}
      style={{ height: MOBILE_LAYOUT.bottomNavHeight }}
      aria-label="Main navigation"
    >
      <div className="flex items-center justify-around h-full">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex flex-col items-center justify-center flex-1 h-full space-y-0.5 min-h-touch transition-colors ${
                isActive ? 'text-blue-600' : 'text-gray-600 hover:text-gray-900'
              }`}
              aria-current={isActive ? 'page' : undefined}
            >
              <span className="text-2xl" aria-hidden="true">
                {item.icon}
              </span>
              <span className="text-xs font-medium">{item.label}</span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
