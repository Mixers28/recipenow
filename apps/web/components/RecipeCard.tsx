/**
 * RecipeCard - Classic recipe card display for verified recipes
 * Clean, simple format inspired by traditional recipe cards
 */
'use client'

import { Recipe } from '@/lib/api'

interface RecipeCardProps {
  recipe: Recipe
  onEdit?: () => void
}

export function RecipeCard({ recipe, onEdit }: RecipeCardProps) {
  return (
    <div className="max-w-2xl mx-auto">
      {/* Recipe Card */}
      <div className="bg-white border-2 border-gray-200 rounded-lg shadow-sm">
        {/* Header */}
        <div className="border-b-2 border-gray-200 p-6 pb-4">
          <h1 className="text-2xl font-serif font-bold text-gray-900 text-center mb-4">
            {recipe.title}
          </h1>

          {/* Meta info row */}
          <div className="flex justify-center gap-6 text-sm text-gray-600">
            {recipe.servings && (
              <div className="flex items-center gap-1">
                <span className="font-medium">Serves:</span>
                <span>{recipe.servings}</span>
              </div>
            )}
          </div>
        </div>

        {/* Content - Two columns on larger screens */}
        <div className="p-6 grid grid-cols-1 md:grid-cols-[1fr,1.5fr] gap-6">
          {/* Ingredients */}
          <div>
            <h2 className="text-lg font-serif font-semibold text-gray-800 mb-3 border-b border-gray-300 pb-1">
              Ingredients
            </h2>
            <ul className="space-y-1.5 text-sm text-gray-700">
              {recipe.ingredients && recipe.ingredients.length > 0 ? (
                recipe.ingredients.map((ingredient, index) => (
                  <li key={index} className="leading-relaxed">
                    {typeof ingredient === 'string'
                      ? ingredient
                      : ingredient.original_text || `${ingredient.quantity || ''} ${ingredient.unit || ''} ${ingredient.name || ''}`.trim()
                    }
                  </li>
                ))
              ) : (
                <li className="text-gray-400 italic">No ingredients listed</li>
              )}
            </ul>
          </div>

          {/* Method */}
          <div>
            <h2 className="text-lg font-serif font-semibold text-gray-800 mb-3 border-b border-gray-300 pb-1">
              Method
            </h2>
            <ol className="space-y-3 text-sm text-gray-700">
              {recipe.steps && recipe.steps.length > 0 ? (
                recipe.steps.map((step, index) => (
                  <li key={index} className="leading-relaxed">
                    <span className="font-semibold text-gray-800 mr-1">{index + 1}.</span>
                    {typeof step === 'string' ? step : step.text || step.instruction || ''}
                  </li>
                ))
              ) : (
                <li className="text-gray-400 italic">No method listed</li>
              )}
            </ol>
          </div>
        </div>

        {/* Footer with tags */}
        {recipe.tags && recipe.tags.length > 0 && (
          <div className="border-t border-gray-200 px-6 py-3 bg-gray-50">
            <div className="flex flex-wrap gap-2">
              {recipe.tags.map((tag) => (
                <span
                  key={tag}
                  className="text-xs text-gray-500 bg-white px-2 py-0.5 rounded border border-gray-200"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Edit button */}
      {onEdit && (
        <div className="mt-4 text-center">
          <button
            onClick={onEdit}
            className="text-sm text-blue-600 hover:text-blue-700 underline"
          >
            Edit Recipe
          </button>
        </div>
      )}
    </div>
  )
}
