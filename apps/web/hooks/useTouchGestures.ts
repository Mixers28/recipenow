'use client'

import { useRef, useCallback } from 'react'

export interface TouchGestureConfig {
  onSwipeLeft?: () => void
  onSwipeRight?: () => void
  onSwipeUp?: () => void
  onSwipeDown?: () => void
  onPinch?: (scale: number) => void
  onLongPress?: () => void
  threshold?: number
  longPressDuration?: number
}

interface TouchPosition {
  x: number
  y: number
}

/**
 * Custom hook for detecting touch gestures
 * Handles: swipe, pinch, long-press
 */
export function useTouchGestures(config: TouchGestureConfig) {
  const {
    onSwipeLeft,
    onSwipeRight,
    onSwipeUp,
    onSwipeDown,
    onPinch,
    onLongPress,
    threshold = 50,
    longPressDuration = 500,
  } = config

  const touchStartPos = useRef<TouchPosition | null>(null)
  const touchStartTime = useRef<number>(0)
  const longPressTimer = useRef<NodeJS.Timeout | null>(null)
  const initialDistance = useRef<number>(0)

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    const touch = e.touches[0]
    touchStartPos.current = { x: touch.clientX, y: touch.clientY }
    touchStartTime.current = Date.now()

    // Calculate initial distance for pinch
    if (e.touches.length === 2) {
      const touch2 = e.touches[1]
      const dx = touch.clientX - touch2.clientX
      const dy = touch.clientY - touch2.clientY
      initialDistance.current = Math.sqrt(dx * dx + dy * dy)
    }

    // Set long press timer
    if (onLongPress) {
      longPressTimer.current = setTimeout(() => {
        onLongPress()
      }, longPressDuration)
    }
  }, [onLongPress, longPressDuration])

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    // Cancel long press on move
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current)
    }

    // Handle pinch
    if (e.touches.length === 2 && onPinch && initialDistance.current > 0) {
      const touch1 = e.touches[0]
      const touch2 = e.touches[1]
      const dx = touch1.clientX - touch2.clientX
      const dy = touch1.clientY - touch2.clientY
      const currentDistance = Math.sqrt(dx * dx + dy * dy)
      const scale = currentDistance / initialDistance.current
      onPinch(scale)
    }
  }, [onPinch])

  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    // Clear long press timer
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current)
    }

    if (!touchStartPos.current) return

    const endX = e.changedTouches[0].clientX
    const endY = e.changedTouches[0].clientY

    const diffX = endX - touchStartPos.current.x
    const diffY = endY - touchStartPos.current.y
    const absDiffX = Math.abs(diffX)
    const absDiffY = Math.abs(diffY)

    // Only consider gestures above threshold
    const isSignificantSwipe = Math.max(absDiffX, absDiffY) > threshold

    if (isSignificantSwipe) {
      if (absDiffX > absDiffY) {
        // Horizontal swipe
        if (diffX > 0) {
          onSwipeRight?.()
        } else {
          onSwipeLeft?.()
        }
      } else {
        // Vertical swipe
        if (diffY > 0) {
          onSwipeDown?.()
        } else {
          onSwipeUp?.()
        }
      }
    }

    touchStartPos.current = null
    initialDistance.current = 0
  }, [threshold, onSwipeLeft, onSwipeRight, onSwipeUp, onSwipeDown])

  return { handleTouchStart, handleTouchMove, handleTouchEnd }
}
