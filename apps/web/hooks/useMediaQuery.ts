'use client'

import { useState, useEffect } from 'react'

/**
 * Hook to detect responsive breakpoints
 * Provides boolean flags for common Tailwind breakpoints
 * SSR-safe with proper hydration handling
 */
export interface MediaQueryBreakpoints {
  isMobile: boolean // < 640px (sm)
  isTablet: boolean // >= 640px && < 1024px
  isDesktop: boolean // >= 1024px (lg)
  isSm: boolean // >= 640px
  isMd: boolean // >= 768px
  isLg: boolean // >= 1024px
  isXl: boolean // >= 1280px
}

export function useMediaQuery(): MediaQueryBreakpoints {
  const [breakpoints, setBreakpoints] = useState<MediaQueryBreakpoints>({
    isMobile: false,
    isTablet: false,
    isDesktop: false,
    isSm: false,
    isMd: false,
    isLg: false,
    isXl: false,
  })

  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)

    const updateBreakpoints = () => {
      const width = window.innerWidth

      setBreakpoints({
        isMobile: width < 640,
        isTablet: width >= 640 && width < 1024,
        isDesktop: width >= 1024,
        isSm: width >= 640,
        isMd: width >= 768,
        isLg: width >= 1024,
        isXl: width >= 1280,
      })
    }

    // Initial call
    updateBreakpoints()

    // Listen for resize events
    const debounceTimer = setTimeout(() => {}, 0)
    const handleResize = () => {
      clearTimeout(debounceTimer)
      updateBreakpoints()
    }

    window.addEventListener('resize', handleResize)
    return () => {
      window.removeEventListener('resize', handleResize)
    }
  }, [])

  // During SSR/hydration, return safe defaults
  if (!mounted) {
    return {
      isMobile: false,
      isTablet: false,
      isDesktop: true,
      isSm: true,
      isMd: true,
      isLg: true,
      isXl: true,
    }
  }

  return breakpoints
}
