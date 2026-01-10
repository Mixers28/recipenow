/**
 * PullToRefresh component - pull-down gesture to refresh content
 */
'use client'

import { useState, useRef, ReactNode, useEffect } from 'react'
import { GESTURES } from '@/lib/constants'

interface PullToRefreshProps {
  children: ReactNode
  onRefresh: () => Promise<void>
  threshold?: number
  disabled?: boolean
  className?: string
}

export function PullToRefresh({
  children,
  onRefresh,
  threshold = 80,
  disabled = false,
  className = '',
}: PullToRefreshProps) {
  const [pullDistance, setPullDistance] = useState(0)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [showIndicator, setShowIndicator] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const touchStartYRef = useRef<number>(0)
  const maxPullRef = useRef<number>(0)

  const handleTouchStart = (e: React.TouchEvent) => {
    if (disabled || isRefreshing) return

    const container = containerRef.current
    if (!container) return

    // Only start if at the top of scroll
    if (container.scrollTop === 0) {
      touchStartYRef.current = e.touches[0].clientY
      setShowIndicator(true)
    }
  }

  const handleTouchMove = (e: React.TouchEvent) => {
    if (disabled || isRefreshing) return

    const container = containerRef.current
    if (!container) return

    // Only process if at top of scroll
    if (container.scrollTop !== 0) {
      setPullDistance(0)
      return
    }

    const currentY = e.touches[0].clientY
    const distance = Math.max(0, currentY - touchStartYRef.current)

    // Apply resistance (ease in)
    const easedDistance = distance * 0.5
    setPullDistance(easedDistance)
    maxPullRef.current = Math.max(maxPullRef.current, easedDistance)
  }

  const handleTouchEnd = async () => {
    if (disabled || isRefreshing) return

    if (pullDistance >= threshold) {
      setIsRefreshing(true)
      setPullDistance(threshold)

      try {
        await onRefresh()
      } finally {
        setIsRefreshing(false)
        setPullDistance(0)
        setShowIndicator(false)
        maxPullRef.current = 0
      }
    } else {
      // Animate back to 0
      setPullDistance(0)
      setTimeout(() => {
        setShowIndicator(false)
        maxPullRef.current = 0
      }, 200)
    }

    touchStartYRef.current = 0
  }

  const getIndicatorState = () => {
    if (isRefreshing) return 'loading'
    if (pullDistance >= threshold) return 'ready'
    return pullDistance > 0 ? 'pulling' : 'idle'
  }

  const state = getIndicatorState()
  const indicatorY = Math.min(pullDistance, 60)

  return (
    <div
      ref={containerRef}
      className={`relative overflow-y-auto ${className}`}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {/* Pull-to-refresh indicator */}
      {showIndicator && (
        <div
          className="absolute left-0 right-0 flex items-center justify-center transition-transform"
          style={{
            transform: `translateY(${indicatorY - 60}px)`,
            top: 0,
            height: '60px',
            zIndex: 10,
          }}
        >
          <div
            className={`flex flex-col items-center space-y-1 transition-transform ${
              state === 'loading' ? 'animate-spin' : ''
            }`}
            style={{
              transform:
                state === 'ready' || state === 'loading'
                  ? 'rotateZ(180deg)'
                  : `rotateZ(${Math.min(pullDistance / threshold, 1) * 180}deg)`,
            }}
          >
            <span className="text-xl">↑</span>
          </div>
        </div>
      )}

      {/* Content with pull offset */}
      <div
        className="transition-transform"
        style={{
          transform: `translateY(${Math.min(pullDistance * 0.5, 30)}px)`,
        }}
      >
        {children}
      </div>

      {/* Pull-to-refresh hint text */}
      {showIndicator && state !== 'loading' && (
        <div className="fixed bottom-4 left-1/2 transform -translate-x-1/2 bg-gray-800 text-white px-4 py-2 rounded-full text-sm pointer-events-none">
          {state === 'ready' ? '↓ Release to refresh' : '↑ Pull to refresh'}
        </div>
      )}
    </div>
  )
}
