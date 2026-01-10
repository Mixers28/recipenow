/**
 * Application-wide constants for mobile-first design
 */

// Touch target sizes (WCAG 2.1 AAA minimum 48px)
export const TOUCH_TARGETS = {
  small: 40, // Below standard but used for secondary actions
  standard: 48, // Minimum recommended
  large: 56, // Extra comfortable for primary actions
}

// Responsive breakpoints (matches Tailwind)
export const BREAKPOINTS = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
}

// Z-index layers
export const Z_INDEX = {
  // Fixed elements
  navigation: 100,
  mobileNav: 110,
  overlay: 105,
  bottomNav: 100,

  // Modals and overlays
  modal: 200,
  tooltip: 150,
  dropdown: 120,

  // Notifications
  toast: 300,
  notification: 250,
}

// Animation durations (in milliseconds)
export const ANIMATIONS = {
  fast: 150,
  normal: 300,
  slow: 500,
  verySlow: 800,
}

// Gesture thresholds
export const GESTURES = {
  // Swipe gesture minimum distance (pixels)
  swipeThreshold: 50,

  // Pull-to-refresh threshold (pixels)
  pullThreshold: 80,

  // Long press duration (milliseconds)
  longPressDuration: 500,

  // Double tap duration (milliseconds)
  doubleTapDuration: 300,

  // Debounce delay for touch events (milliseconds)
  touchDebounce: 50,
}

// Safe area insets (for notched devices)
export const SAFE_AREAS = {
  top: 'env(safe-area-inset-top)',
  bottom: 'env(safe-area-inset-bottom)',
  left: 'env(safe-area-inset-left)',
  right: 'env(safe-area-inset-right)',
}

// Common padding/spacing
export const SPACING = {
  mobile: '1rem', // 16px
  tablet: '1.5rem', // 24px
  desktop: '2rem', // 32px
}

// Mobile layout dimensions
export const MOBILE_LAYOUT = {
  // Bottom navigation bar height
  bottomNavHeight: 64,

  // Mobile menu width
  mobileMenuWidth: 320,

  // Max content width on mobile
  mobileMaxWidth: 'min(100vw - 2rem, 420px)',
}
