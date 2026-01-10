/**
 * Reusable Tabs component with mobile swipe support
 * Accessible ARIA tabs pattern with smooth transitions
 */
'use client'

import { useState, ReactNode } from 'react'
import { useTouchGestures } from '@/hooks/useTouchGestures'
import { ANIMATIONS } from '@/lib/constants'

export interface Tab {
  id: string
  label: string
  content: ReactNode
}

interface TabsProps {
  tabs: Tab[]
  defaultTab?: string
  onChange?: (tabId: string) => void
  className?: string
}

export function Tabs({ tabs, defaultTab, onChange, className = '' }: TabsProps) {
  const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.id || '')

  const currentIndex = tabs.findIndex((t) => t.id === activeTab)

  const { handleTouchStart, handleTouchMove, handleTouchEnd } = useTouchGestures({
    onSwipeLeft: () => {
      if (currentIndex < tabs.length - 1) {
        const nextTab = tabs[currentIndex + 1]
        handleTabChange(nextTab.id)
      }
    },
    onSwipeRight: () => {
      if (currentIndex > 0) {
        const prevTab = tabs[currentIndex - 1]
        handleTabChange(prevTab.id)
      }
    },
    threshold: 30,
  })

  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId)
    onChange?.(tabId)
  }

  const currentTab = tabs.find((t) => t.id === activeTab)

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Tab buttons */}
      <div
        className="flex border-b border-gray-200 bg-white"
        role="tablist"
      >
        {tabs.map((tab, index) => (
          <button
            key={tab.id}
            onClick={() => handleTabChange(tab.id)}
            className={`flex-1 px-4 py-3 font-medium text-sm transition-colors border-b-2 min-h-touch flex items-center justify-center space-x-2 ${
              activeTab === tab.id
                ? 'text-blue-600 border-blue-600 bg-blue-50'
                : 'text-gray-600 border-transparent hover:bg-gray-50'
            }`}
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`tabpanel-${tab.id}`}
            id={`tab-${tab.id}`}
          >
            <span>{tab.label}</span>
            {index < tabs.length - 1 && <span className="text-gray-300">|</span>}
          </button>
        ))}
      </div>

      {/* Tab content with swipe support */}
      <div
        className="flex-1 overflow-hidden"
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {currentTab && (
          <div
            id={`tabpanel-${currentTab.id}`}
            role="tabpanel"
            aria-labelledby={`tab-${currentTab.id}`}
            className="h-full overflow-y-auto animate-fade-in-up"
            style={{ animationDuration: `${ANIMATIONS.normal}ms` }}
          >
            {currentTab.content}
          </div>
        )}
      </div>
    </div>
  )
}
