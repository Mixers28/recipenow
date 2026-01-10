/**
 * Image viewer component with bbox highlighting
 */
'use client'

import { useEffect, useRef, useState } from 'react'
import { SourceSpan } from '@/lib/api'
import { GESTURES } from '@/lib/constants'

interface ImageViewerProps {
  imageUrl: string
  spans?: SourceSpan[]
  highlightedFieldPath?: string
  onBboxClick?: (bbox: SourceSpan['bbox'], fieldPath: string) => void
}

export function ImageViewer({
  imageUrl,
  spans = [],
  highlightedFieldPath,
  onBboxClick,
}: ImageViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [scale, setScale] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })

  // Touch gesture tracking
  const touchStartRef = useRef<{ x: number; y: number } | null>(null)
  const touchInitialDistanceRef = useRef<number>(0)
  const lastTapRef = useRef<number>(0)
  const [showGestureHint, setShowGestureHint] = useState(true)

  // Load and draw image with bboxes
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const img = new Image()
    img.onload = () => {
      // Set canvas size to match image
      canvas.width = img.width
      canvas.height = img.height

      // Draw image
      ctx.drawImage(img, 0, 0)

      // Draw bboxes
      spans.forEach((span) => {
        const [x, y, w, h] = span.bbox
        const isHighlighted = span.field_path === highlightedFieldPath

        // Draw rectangle
        ctx.strokeStyle = isHighlighted ? '#3b82f6' : '#10b981'
        ctx.lineWidth = isHighlighted ? 3 : 2
        ctx.strokeRect(x, y, w, h)

        // Draw label background
        ctx.fillStyle = isHighlighted ? '#3b82f6' : '#10b981'
        ctx.fillRect(x, y - 20, Math.min(150, w), 20)

        // Draw label text
        ctx.fillStyle = 'white'
        ctx.font = '12px sans-serif'
        ctx.textBaseline = 'top'
        const label = span.field_path.split('[')[0].split('.').pop()
        ctx.fillText(`${label} (${Math.round(span.ocr_confidence * 100)}%)`, x + 5, y - 16)
      })
    }
    img.src = imageUrl
  }, [imageUrl, spans, highlightedFieldPath])

  // Mouse events for pan and zoom
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(true)
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y })
  }

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (isDragging) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      })
    }

    // Check if hovering over bbox
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = (e.clientX - rect.left - pan.x) / scale
    const y = (e.clientY - rect.top - pan.y) / scale

    const hoveredSpan = spans.find((span) => {
      const [bx, by, bw, bh] = span.bbox
      return x >= bx && x <= bx + bw && y >= by && y <= by + bh
    })

    if (canvas.style.cursor !== (hoveredSpan ? 'pointer' : 'grab')) {
      canvas.style.cursor = hoveredSpan ? 'pointer' : 'grab'
    }
  }

  const handleMouseUp = () => {
    setIsDragging(false)
  }

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!onBboxClick) return

    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = (e.clientX - rect.left - pan.x) / scale
    const y = (e.clientY - rect.top - pan.y) / scale

    const clickedSpan = spans.find((span) => {
      const [bx, by, bw, bh] = span.bbox
      return x >= bx && x <= bx + bw && y >= by && y <= by + bh
    })

    if (clickedSpan) {
      onBboxClick(clickedSpan.bbox, clickedSpan.field_path)
    }
  }

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? 0.8 : 1.2
    setScale((prev) => Math.min(Math.max(prev * delta, 0.5), 3))
  }

  // Touch event handlers for mobile gestures
  const handleTouchStart = (e: React.TouchEvent<HTMLCanvasElement>) => {
    if (e.touches.length === 1) {
      // Single touch - start pan
      const touch = e.touches[0]
      const canvas = canvasRef.current
      if (!canvas) return

      const rect = canvas.getBoundingClientRect()
      touchStartRef.current = {
        x: touch.clientX - rect.left - pan.x,
        y: touch.clientY - rect.top - pan.y,
      }

      // Detect double-tap
      const now = Date.now()
      if (now - lastTapRef.current < GESTURES.doubleTapDuration) {
        // Double-tap: toggle zoom between 1x and 2x
        setScale((s) => (s > 1.5 ? 1 : 2))
        lastTapRef.current = 0
      } else {
        lastTapRef.current = now
      }
    } else if (e.touches.length === 2) {
      // Two-finger touch - start pinch
      const touch1 = e.touches[0]
      const touch2 = e.touches[1]
      const dx = touch1.clientX - touch2.clientX
      const dy = touch1.clientY - touch2.clientY
      touchInitialDistanceRef.current = Math.sqrt(dx * dx + dy * dy)
    }
  }

  const handleTouchMove = (e: React.TouchEvent<HTMLCanvasElement>) => {
    e.preventDefault()

    if (e.touches.length === 1) {
      // Single touch - pan
      const touch = e.touches[0]
      const canvas = canvasRef.current
      if (!canvas || !touchStartRef.current) return

      const rect = canvas.getBoundingClientRect()
      setPan({
        x: touch.clientX - rect.left - touchStartRef.current.x,
        y: touch.clientY - rect.top - touchStartRef.current.y,
      })
    } else if (e.touches.length === 2) {
      // Two-finger touch - pinch zoom
      const touch1 = e.touches[0]
      const touch2 = e.touches[1]
      const dx = touch1.clientX - touch2.clientX
      const dy = touch1.clientY - touch2.clientY
      const currentDistance = Math.sqrt(dx * dx + dy * dy)

      if (touchInitialDistanceRef.current > 0) {
        const scaleRatio = currentDistance / touchInitialDistanceRef.current
        setScale((prev) => Math.min(Math.max(prev * scaleRatio, 0.5), 3))
        touchInitialDistanceRef.current = currentDistance
      }
    }
  }

  const handleTouchEnd = () => {
    touchStartRef.current = null
    touchInitialDistanceRef.current = 0
  }

  return (
    <div className="bg-gray-100 rounded-lg overflow-hidden flex flex-col h-full">
      {/* Toolbar */}
      <div className="bg-white border-b border-gray-200 p-2 space-x-1 flex items-center flex-wrap gap-2">
        <button
          onClick={() => setScale((s) => Math.max(s - 0.2, 0.5))}
          className="px-3 py-2 text-sm bg-gray-200 hover:bg-gray-300 rounded transition-colors min-h-touch flex items-center justify-center"
          title="Zoom out"
        >
          −
        </button>
        <span className="inline-block px-3 py-2 text-sm text-gray-600 min-w-14 text-center">
          {Math.round(scale * 100)}%
        </span>
        <button
          onClick={() => setScale((s) => Math.min(s + 0.2, 3))}
          className="px-3 py-2 text-sm bg-gray-200 hover:bg-gray-300 rounded transition-colors min-h-touch flex items-center justify-center"
          title="Zoom in"
        >
          +
        </button>
        <button
          onClick={() => {
            setScale(1)
            setPan({ x: 0, y: 0 })
          }}
          className="px-3 py-2 text-sm bg-gray-200 hover:bg-gray-300 rounded transition-colors min-h-touch flex items-center justify-center"
          title="Reset view"
        >
          ↺ Reset
        </button>
        <span className="text-xs text-gray-500 ml-auto hidden sm:inline-block">
          Tap fields • Pinch zoom • Swipe pan • Double-tap 2x
        </span>
      </div>

      {/* Canvas */}
      <div className="flex-1 overflow-auto bg-gray-900 flex items-center justify-center relative">
        <canvas
          ref={canvasRef}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onClick={handleClick}
          onWheel={handleWheel}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})`,
            transformOrigin: '0 0',
            cursor: 'grab',
            userSelect: 'none',
            touchAction: 'none',
          }}
          className="max-w-full max-h-full"
        />
      </div>
    </div>
  )
}
