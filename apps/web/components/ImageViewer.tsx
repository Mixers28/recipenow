/**
 * Image viewer component with bbox highlighting
 */
'use client'

import { useEffect, useRef, useState } from 'react'
import { SourceSpan } from '@/lib/api'

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

  return (
    <div className="bg-gray-100 rounded-lg overflow-hidden flex flex-col h-full">
      {/* Toolbar */}
      <div className="bg-white border-b border-gray-200 p-3 space-x-2">
        <button
          onClick={() => setScale((s) => Math.max(s - 0.2, 0.5))}
          className="px-3 py-1 text-sm bg-gray-200 hover:bg-gray-300 rounded transition-colors"
          title="Zoom out"
        >
          −
        </button>
        <span className="inline-block px-3 py-1 text-sm text-gray-600 min-w-12">
          {Math.round(scale * 100)}%
        </span>
        <button
          onClick={() => setScale((s) => Math.min(s + 0.2, 3))}
          className="px-3 py-1 text-sm bg-gray-200 hover:bg-gray-300 rounded transition-colors"
          title="Zoom in"
        >
          +
        </button>
        <button
          onClick={() => {
            setScale(1)
            setPan({ x: 0, y: 0 })
          }}
          className="px-3 py-1 text-sm bg-gray-200 hover:bg-gray-300 rounded transition-colors ml-2"
          title="Reset view"
        >
          ↺ Reset
        </button>
        <span className="inline-block text-xs text-gray-500 ml-4">
          Click fields to highlight • Scroll to zoom • Drag to pan
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
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})`,
            transformOrigin: '0 0',
            cursor: 'grab',
            userSelect: 'none',
          }}
          className="max-w-full max-h-full"
        />
      </div>
    </div>
  )
}
