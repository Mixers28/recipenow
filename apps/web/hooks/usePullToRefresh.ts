'use client'

import { useState, useRef, useCallback } from 'react'

export interface UsePullToRefreshConfig {
  threshold?: number
  onRefresh: () => Promise<void>
  onComplete?: () => void
}

export interface PullToRefreshState {
  isPulling: boolean
  isRefreshing: boolean
  pullDistance: number
}

/**
 * Hook for implementing pull-to-refresh gesture
 * Call onRefresh callback when pull threshold is reached
 */
export function usePullToRefresh(config: UsePullToRefreshConfig) {
  const { threshold = 80, onRefresh, onComplete } = config

  const [state, setState] = useState<PullToRefreshState>({
    isPulling: false,
    isRefreshing: false,
    pullDistance: 0,
  })

  const touchStartY = useRef<number>(0)
  const scrollElement = useRef<HTMLElement | null>(null)

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    const scrollTop = e.currentTarget.scrollTop
    touchStartY.current = e.touches[0].clientY

    // Only trigger if at top of scroll
    if (scrollTop === 0) {
      setState((prev) => ({ ...prev, isPulling: true }))
    }
  }, [])

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    const scrollTop = e.currentTarget.scrollTop

    // Only process if at top of scroll
    if (scrollTop !== 0) {
      setState((prev) => ({ ...prev, isPulling: false, pullDistance: 0 }))
      return
    }

    if (!state.isPulling) return

    const currentY = e.touches[0].clientY
    const pullDistance = Math.max(0, currentY - touchStartY.current)

    setState((prev) => ({
      ...prev,
      pullDistance,
    }))
  }, [state.isPulling])

  const handleTouchEnd = useCallback(async () => {
    if (state.pullDistance >= threshold && !state.isRefreshing) {
      setState((prev) => ({
        ...prev,
        isRefreshing: true,
        isPulling: false,
      }))

      try {
        await onRefresh()
      } finally {
        setState((prev) => ({
          ...prev,
          isRefreshing: false,
          pullDistance: 0,
        }))
        onComplete?.()
      }
    } else {
      setState((prev) => ({
        ...prev,
        isPulling: false,
        pullDistance: 0,
      }))
    }
  }, [state.pullDistance, state.isRefreshing, threshold, onRefresh, onComplete])

  return {
    ...state,
    handleTouchStart,
    handleTouchMove,
    handleTouchEnd,
  }
}
