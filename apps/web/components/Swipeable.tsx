/**
 * Swipeable component - reveals action buttons on swipe
 * Common pattern on mobile for delete/archive actions
 */
'use client'

import { useState, useRef, ReactNode } from 'react'
import { useTouchGestures } from '@/hooks/useTouchGestures'

interface SwipeableProps {
  children: ReactNode
  onSwipeLeft?: () => void
  onSwipeRight?: () => void
  leftActions?: ReactNode
  rightActions?: ReactNode
  className?: string
  threshold?: number
}

export function Swipeable({
  children,
  onSwipeLeft,
  onSwipeRight,
  leftActions,
  rightActions,
  className = '',
  threshold = 50,
}: SwipeableProps) {
  const [swiped, setSwiped] = useState<'left' | 'right' | null>(null)
  const swipeTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const handleSwipeLeft = () => {
    if (onSwipeLeft) {
      setSwiped('left')
      if (swipeTimeoutRef.current) clearTimeout(swipeTimeoutRef.current)
      swipeTimeoutRef.current = setTimeout(() => {
        setSwiped(null)
        onSwipeLeft()
      }, 200)
    }
  }

  const handleSwipeRight = () => {
    if (onSwipeRight) {
      setSwiped('right')
      if (swipeTimeoutRef.current) clearTimeout(swipeTimeoutRef.current)
      swipeTimeoutRef.current = setTimeout(() => {
        setSwiped(null)
        onSwipeRight()
      }, 200)
    }
  }

  const { handleTouchStart, handleTouchMove, handleTouchEnd } = useTouchGestures({
    onSwipeLeft: handleSwipeLeft,
    onSwipeRight: handleSwipeRight,
    threshold,
  })

  return (
    <div
      className={`relative overflow-hidden transition-colors ${className}`}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {/* Right actions (revealed on swipe left) */}
      {leftActions && swiped === 'left' && (
        <div className="absolute inset-y-0 right-0 flex items-center bg-red-500 animate-slide-in-right">
          {leftActions}
        </div>
      )}

      {/* Left actions (revealed on swipe right) */}
      {rightActions && swiped === 'right' && (
        <div className="absolute inset-y-0 left-0 flex items-center bg-blue-500 animate-slide-in-right">
          {rightActions}
        </div>
      )}

      {/* Main content */}
      <div className={`relative z-10 ${swiped ? 'bg-gray-100' : ''} transition-colors`}>
        {children}
      </div>
    </div>
  )
}
