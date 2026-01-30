/**
 * RecipeThumbnailCard - Thumbnail card for library grid
 * Shows cropped meal photo if available, title, status, and delete option
 */
'use client'

import { useState, useEffect } from 'react'
import { Recipe, listSpans, getAsset } from '@/lib/api'
import { RecipeStatusBadge } from '@/components/RecipeStatusBadge'

const DEMO_USER_ID = '550e8400-e29b-41d4-a716-446655440000'

interface RecipeThumbnailCardProps {
  recipe: Recipe
  onDelete: (e: React.MouseEvent, recipeId: string) => void
  isDeleting: boolean
}

export function RecipeThumbnailCard({ recipe, onDelete, isDeleting }: RecipeThumbnailCardProps) {
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [imageLoading, setImageLoading] = useState(false)
  const crop = recipe.thumbnail_crop

  // Fetch image if recipe has a crop set
  useEffect(() => {
    if (!crop || crop.width <= 0 || crop.height <= 0) {
      setImageUrl(null)
      return
    }

    let objectUrl: string | null = null
    let cancelled = false

    const fetchImage = async () => {
      setImageLoading(true)
      try {
        // Get spans to find the asset_id
        const spans = await listSpans(DEMO_USER_ID, recipe.id)
        if (cancelled || spans.length === 0) {
          setImageLoading(false)
          return
        }

        const assetId = spans[0].asset_id
        const blob = await getAsset(assetId)
        if (cancelled) return

        objectUrl = URL.createObjectURL(blob)
        setImageUrl(objectUrl)
      } catch (err) {
        console.error('Failed to fetch recipe image:', err)
      } finally {
        if (!cancelled) setImageLoading(false)
      }
    }

    fetchImage()

    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [recipe.id, crop])

  return (
    <div className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow overflow-hidden">
      {/* Thumbnail area */}
      <div className="aspect-[4/5] relative bg-gray-100">
        {imageUrl && crop && crop.width > 0 && crop.height > 0 ? (
          // Show cropped image
          <div className="w-full h-full overflow-hidden relative">
            <img
              src={imageUrl}
              alt={recipe.title || 'Recipe'}
              className="absolute"
              style={{
                width: `${100 / (crop.width / 100)}%`,
                height: `${100 / (crop.height / 100)}%`,
                left: `${-crop.x / (crop.width / 100)}%`,
                top: `${-crop.y / (crop.height / 100)}%`,
              }}
            />
          </div>
        ) : imageLoading ? (
          // Loading state
          <div className="w-full h-full flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-gray-300 border-t-blue-600"></div>
          </div>
        ) : (
          // Placeholder when no crop/image
          <div className="w-full h-full flex items-center justify-center text-gray-400">
            <div className="text-center">
              <div className="text-4xl mb-2">📷</div>
              <div className="text-xs">No photo</div>
            </div>
          </div>
        )}

        {/* Title overlay at bottom */}
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-3">
          <h3 className="text-base font-semibold text-white line-clamp-2">
            {recipe.title || 'Untitled Recipe'}
          </h3>
        </div>
      </div>

      {/* Footer with status and delete */}
      <div className="p-3 flex justify-between items-center">
        <RecipeStatusBadge status={recipe.status} />
        <button
          onClick={(e) => onDelete(e, recipe.id)}
          disabled={isDeleting}
          className="text-xs text-red-600 hover:text-red-700 disabled:text-gray-400 px-2 py-1"
          aria-label={`Delete ${recipe.title || 'recipe'}`}
          title="Delete recipe"
        >
          {isDeleting ? '...' : 'Delete'}
        </button>
      </div>
    </div>
  )
}
