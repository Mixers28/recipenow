/**
 * FlipRecipeCard - A flip card showing image on front, recipe on back
 * Click to flip between the two views
 */
'use client'

import { useState } from 'react'
import { Recipe, ThumbnailCrop } from '@/lib/api'

interface FlipRecipeCardProps {
  recipe: Recipe
  imageUrl: string
  onEdit?: () => void
  onSetThumbnail?: () => void
}

export function FlipRecipeCard({ recipe, imageUrl, onEdit, onSetThumbnail }: FlipRecipeCardProps) {
  const [isFlipped, setIsFlipped] = useState(false)
  const crop = recipe.thumbnail_crop

  const handleFlip = () => {
    setIsFlipped(!isFlipped)
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Flip Card Container */}
      <div
        className="relative w-full cursor-pointer"
        style={{ perspective: '1000px' }}
        onClick={handleFlip}
      >
        <div
          className={`relative w-full transition-transform duration-500 ease-in-out`}
          style={{
            transformStyle: 'preserve-3d',
            transform: isFlipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
          }}
        >
          {/* Front - Image */}
          <div
            className="w-full bg-white rounded-lg shadow-lg overflow-hidden"
            style={{ backfaceVisibility: 'hidden' }}
          >
            <div className="aspect-[4/5] relative">
              {imageUrl ? (
                crop && crop.width > 0 && crop.height > 0 ? (
                  // Display cropped portion using overflow hidden container
                  // Scale to cover the 4:5 container while showing only the crop area
                  <div className="w-full h-full overflow-hidden relative">
                    <img
                      src={imageUrl}
                      alt={recipe.title || 'Recipe image'}
                      className="absolute object-cover"
                      style={{
                        // Calculate scale: container is 4:5 (0.8), crop ratio varies
                        // Scale based on the dimension that needs more scaling to fill
                        // For width-based: 100 / (crop.width/100) = 100 * 100 / crop.width
                        // For height-based: 100 / (crop.height/100) = 100 * 100 / crop.height
                        // The card is 4:5 (80% width:height), so we need to scale to cover
                        width: `${100 / (crop.width / 100)}%`,
                        height: `${100 / (crop.height / 100)}%`,
                        // Position so crop area is in view
                        left: `${-crop.x / (crop.width / 100)}%`,
                        top: `${-crop.y / (crop.height / 100)}%`,
                        objectFit: 'cover',
                      }}
                    />
                  </div>
                ) : (
                  // No crop set - show full image
                  <img
                    src={imageUrl}
                    alt={recipe.title || 'Recipe image'}
                    className="w-full h-full object-cover"
                  />
                )
              ) : (
                <div className="w-full h-full bg-gray-200 flex items-center justify-center">
                  <span className="text-gray-500">No image</span>
                </div>
              )}
              {/* Title overlay at bottom */}
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-4">
                <h2 className="text-xl font-serif font-bold text-white">
                  {recipe.title || 'Untitled Recipe'}
                </h2>
                <p className="text-sm text-white/80 mt-1">Tap to view recipe</p>
              </div>
            </div>
          </div>

          {/* Back - Recipe Card */}
          <div
            className="absolute top-0 left-0 w-full bg-white rounded-lg shadow-lg overflow-hidden"
            style={{
              backfaceVisibility: 'hidden',
              transform: 'rotateY(180deg)',
            }}
          >
            <div className="aspect-[4/5] overflow-y-auto">
              {/* Recipe Content */}
              <div className="p-6">
                {/* Header */}
                <div className="border-b-2 border-gray-200 pb-4 mb-4">
                  <h1 className="text-2xl font-serif font-bold text-gray-900 text-center mb-3">
                    {recipe.title}
                  </h1>

                  {/* Meta info */}
                  <div className="flex justify-center gap-4 text-sm text-gray-600">
                    {recipe.servings && (
                      <span><strong>Serves:</strong> {recipe.servings}</span>
                    )}
                  </div>
                </div>

                {/* Ingredients */}
                <div className="mb-4">
                  <h2 className="text-base font-serif font-semibold text-gray-800 mb-2 border-b border-gray-200 pb-1">
                    Ingredients
                  </h2>
                  <ul className="space-y-1 text-sm text-gray-700">
                    {recipe.ingredients && recipe.ingredients.length > 0 ? (
                      recipe.ingredients.map((ingredient, index) => (
                        <li key={index} className="leading-snug">
                          {typeof ingredient === 'string'
                            ? ingredient
                            : ingredient.original_text || `${ingredient.quantity || ''} ${ingredient.unit || ''} ${ingredient.name_norm || ''}`.trim()
                          }
                        </li>
                      ))
                    ) : (
                      <li className="text-gray-400 italic">No ingredients</li>
                    )}
                  </ul>
                </div>

                {/* Method */}
                <div>
                  <h2 className="text-base font-serif font-semibold text-gray-800 mb-2 border-b border-gray-200 pb-1">
                    Method
                  </h2>
                  <ol className="space-y-2 text-sm text-gray-700">
                    {recipe.steps && recipe.steps.length > 0 ? (
                      recipe.steps.map((step, index) => (
                        <li key={index} className="leading-snug">
                          <span className="font-semibold">{index + 1}.</span>{' '}
                          {typeof step === 'string' ? step : step.text}
                        </li>
                      ))
                    ) : (
                      <li className="text-gray-400 italic">No method</li>
                    )}
                  </ol>
                </div>

                {/* Tap hint */}
                <p className="text-xs text-gray-400 text-center mt-4">Tap to see image</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Status and actions below card */}
      <div className="mt-4 flex justify-between items-center">
        <span className={`text-sm px-2 py-1 rounded ${
          recipe.status === 'verified'
            ? 'bg-green-100 text-green-700'
            : 'bg-yellow-100 text-yellow-700'
        }`}>
          {recipe.status === 'verified' ? '✓ Verified' : '⚠ Needs Review'}
        </span>
        <div className="flex gap-3">
          {onSetThumbnail && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onSetThumbnail()
              }}
              className="text-sm text-gray-600 hover:text-gray-800 underline"
            >
              {crop ? 'Change Photo' : 'Set Photo'}
            </button>
          )}
          {onEdit && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onEdit()
              }}
              className="text-sm text-blue-600 hover:text-blue-700 underline"
            >
              Edit Recipe
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
