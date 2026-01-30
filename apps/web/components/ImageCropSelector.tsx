/**
 * ImageCropSelector - Simple drag-to-select crop area for meal photo
 * Uses percentage-based coordinates for responsive handling
 */
'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { ThumbnailCrop } from '@/lib/api'

interface ImageCropSelectorProps {
  imageUrl: string
  initialCrop?: ThumbnailCrop
  onCropChange: (crop: ThumbnailCrop) => void
  onSave: () => void
  onCancel: () => void
}

export function ImageCropSelector({
  imageUrl,
  initialCrop,
  onCropChange,
  onSave,
  onCancel,
}: ImageCropSelectorProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null)
  const [crop, setCrop] = useState<ThumbnailCrop>(
    initialCrop || { x: 25, y: 10, width: 50, height: 40 }
  )

  // Update parent when crop changes
  useEffect(() => {
    onCropChange(crop)
  }, [crop, onCropChange])

  const getPercentagePosition = useCallback((clientX: number, clientY: number) => {
    if (!containerRef.current) return { x: 0, y: 0 }

    const rect = containerRef.current.getBoundingClientRect()
    const x = Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100))
    const y = Math.max(0, Math.min(100, ((clientY - rect.top) / rect.height) * 100))

    return { x, y }
  }, [])

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    const pos = getPercentagePosition(e.clientX, e.clientY)
    setDragStart(pos)
    setIsDragging(true)
  }, [getPercentagePosition])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging || !dragStart) return

    const pos = getPercentagePosition(e.clientX, e.clientY)

    const newCrop: ThumbnailCrop = {
      x: Math.min(dragStart.x, pos.x),
      y: Math.min(dragStart.y, pos.y),
      width: Math.abs(pos.x - dragStart.x),
      height: Math.abs(pos.y - dragStart.y),
    }

    setCrop(newCrop)
  }, [isDragging, dragStart, getPercentagePosition])

  const handleMouseUp = useCallback(() => {
    setIsDragging(false)
    setDragStart(null)
  }, [])

  // Handle touch events for mobile
  // preventDefault stops page scrolling while drawing crop box
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    if (e.touches.length !== 1) return
    e.preventDefault() // Prevent page scroll
    const touch = e.touches[0]
    const pos = getPercentagePosition(touch.clientX, touch.clientY)
    setDragStart(pos)
    setIsDragging(true)
  }, [getPercentagePosition])

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!isDragging || !dragStart || e.touches.length !== 1) return
    e.preventDefault() // Prevent page scroll

    const touch = e.touches[0]
    const pos = getPercentagePosition(touch.clientX, touch.clientY)

    const newCrop: ThumbnailCrop = {
      x: Math.min(dragStart.x, pos.x),
      y: Math.min(dragStart.y, pos.y),
      width: Math.abs(pos.x - dragStart.x),
      height: Math.abs(pos.y - dragStart.y),
    }

    setCrop(newCrop)
  }, [isDragging, dragStart, getPercentagePosition])

  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    e.preventDefault() // Prevent any follow-up actions
    setIsDragging(false)
    setDragStart(null)
  }, [])

  return (
    <div className="space-y-4">
      <div className="text-sm text-gray-600 mb-2">
        Drag on the image to select the meal photo area for the recipe card.
      </div>

      {/* Image with crop overlay */}
      {/* touch-action: none prevents browser from handling touch for scroll/zoom */}
      <div
        ref={containerRef}
        className="relative w-full bg-gray-100 rounded-lg overflow-hidden cursor-crosshair select-none"
        style={{ touchAction: 'none' }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {/* Base image - use object-contain so full image is visible and crop coords match */}
        <img
          src={imageUrl}
          alt="Recipe to crop"
          className="w-full h-auto pointer-events-none"
          draggable={false}
        />

        {/* Darkened overlay outside crop area */}
        <div className="absolute inset-0 pointer-events-none">
          {/* Top */}
          <div
            className="absolute left-0 right-0 top-0 bg-black/50"
            style={{ height: `${crop.y}%` }}
          />
          {/* Bottom */}
          <div
            className="absolute left-0 right-0 bottom-0 bg-black/50"
            style={{ height: `${100 - crop.y - crop.height}%` }}
          />
          {/* Left */}
          <div
            className="absolute left-0 bg-black/50"
            style={{
              top: `${crop.y}%`,
              height: `${crop.height}%`,
              width: `${crop.x}%`,
            }}
          />
          {/* Right */}
          <div
            className="absolute right-0 bg-black/50"
            style={{
              top: `${crop.y}%`,
              height: `${crop.height}%`,
              width: `${100 - crop.x - crop.width}%`,
            }}
          />
        </div>

        {/* Crop selection border */}
        <div
          className="absolute border-2 border-white shadow-lg pointer-events-none"
          style={{
            left: `${crop.x}%`,
            top: `${crop.y}%`,
            width: `${crop.width}%`,
            height: `${crop.height}%`,
          }}
        >
          {/* Corner handles for visual feedback */}
          <div className="absolute -top-1 -left-1 w-3 h-3 bg-white rounded-full shadow" />
          <div className="absolute -top-1 -right-1 w-3 h-3 bg-white rounded-full shadow" />
          <div className="absolute -bottom-1 -left-1 w-3 h-3 bg-white rounded-full shadow" />
          <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-white rounded-full shadow" />
        </div>
      </div>

      {/* Preview - 4:5 aspect ratio like the recipe card */}
      <div className="bg-gray-50 rounded-lg p-4">
        <div className="text-sm font-medium text-gray-700 mb-2">Preview (card aspect):</div>
        <div className="w-32 h-40 mx-auto overflow-hidden rounded-lg shadow border border-gray-200 relative">
          {crop.width > 0 && crop.height > 0 && (
            <img
              src={imageUrl}
              alt="Preview"
              className="absolute"
              style={{
                width: `${100 / (crop.width / 100)}%`,
                height: `${100 / (crop.height / 100)}%`,
                left: `${-crop.x / (crop.width / 100)}%`,
                top: `${-crop.y / (crop.height / 100)}%`,
              }}
            />
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3 justify-end">
        <button
          onClick={onCancel}
          className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={onSave}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Save Crop
        </button>
      </div>
    </div>
  )
}
