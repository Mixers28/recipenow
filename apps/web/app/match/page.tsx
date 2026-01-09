/**
 * Match Results page - shows recipes that match pantry items
 */
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  matchAllRecipes,
  generateShoppingList,
  RecipeMatchResult,
  ShoppingListResponse,
  IngredientMatch,
} from '@/lib/api'

const DEMO_USER_ID = '550e8400-e29b-41d4-a716-446655440000' // Demo user for testing

export default function MatchPage() {
  const router = useRouter()

  // State
  const [matches, setMatches] = useState<RecipeMatchResult[]>([])
  const [shoppingList, setShoppingList] = useState<ShoppingListResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>()
  const [expandedRecipe, setExpandedRecipe] = useState<string | null>(null)
  const [showShoppingList, setShowShoppingList] = useState(false)

  // Load match results on mount
  useEffect(() => {
    fetchMatches()
  }, [])

  const fetchMatches = async () => {
    try {
      setLoading(true)
      setError(undefined)
      const response = await matchAllRecipes(DEMO_USER_ID, { min_match: 0 })
      setMatches(response.recipes)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load match results')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateShoppingList = async () => {
    try {
      setLoading(true)
      const recipes = matches.filter((m) => m.match_percentage > 0)
      const list = await generateShoppingList(
        DEMO_USER_ID,
        recipes.map((r) => r.recipe_id)
      )
      setShoppingList(list)
      setShowShoppingList(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate shopping list')
    } finally {
      setLoading(false)
    }
  }

  const getMatchColor = (percentage: number): string => {
    if (percentage >= 80) return 'text-green-600'
    if (percentage >= 50) return 'text-blue-600'
    if (percentage >= 20) return 'text-yellow-600'
    return 'text-gray-600'
  }

  const getMatchBgColor = (percentage: number): string => {
    if (percentage >= 80) return 'bg-green-50 border-green-200'
    if (percentage >= 50) return 'bg-blue-50 border-blue-200'
    if (percentage >= 20) return 'bg-yellow-50 border-yellow-200'
    return 'bg-gray-50 border-gray-200'
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">🔍 What Can You Cook?</h1>
        <button
          onClick={() => router.push('/pantry')}
          className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
        >
          ← Back to Pantry
        </button>
      </div>

      {/* Error message */}
      {error && <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">{error}</div>}

      {/* Stats */}
      {matches.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-sm text-gray-600">Total Recipes</p>
            <p className="text-2xl font-bold text-gray-900">{matches.length}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-sm text-gray-600">Fully Cookable</p>
            <p className="text-2xl font-bold text-green-600">{matches.filter((m) => m.match_percentage === 100).length}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-sm text-gray-600">Partially Cookable</p>
            <p className="text-2xl font-bold text-blue-600">
              {matches.filter((m) => m.match_percentage > 0 && m.match_percentage < 100).length}
            </p>
          </div>
        </div>
      )}

      {/* Shopping list button */}
      {matches.some((m) => m.match_percentage > 0) && (
        <button
          onClick={handleGenerateShoppingList}
          disabled={loading}
          className="w-full px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 transition-colors font-medium"
        >
          🛒 Generate Shopping List
        </button>
      )}

      {/* Shopping List */}
      {showShoppingList && shoppingList && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold text-purple-900">Shopping List</h2>
            <button
              onClick={() => setShowShoppingList(false)}
              className="text-purple-600 hover:text-purple-900"
            >
              ✕
            </button>
          </div>

          {shoppingList.missing_items.length === 0 ? (
            <p className="text-purple-800">You have all ingredients for your selected recipes!</p>
          ) : (
            <div className="space-y-3">
              {shoppingList.missing_items.map((item, idx) => (
                <div key={idx} className="flex justify-between items-start p-3 bg-white rounded-lg border border-purple-100">
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">{item.original_text}</p>
                    <p className="text-sm text-gray-600">
                      {item.total_quantity > 0 && item.unit ? `${item.total_quantity} ${item.unit}` : ''}
                      {item.total_quantity > 0 && !item.unit ? `${item.total_quantity}` : ''}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      Needed in: {item.recipes.join(', ')}
                    </p>
                  </div>
                  <span className="text-sm font-semibold text-purple-600">{item.count} recipe(s)</span>
                </div>
              ))}
            </div>
          )}

          <p className="text-sm text-purple-700">
            <strong>Total items needed:</strong> {shoppingList.total_missing}
          </p>
        </div>
      )}

      {/* Match Results */}
      {loading && matches.length === 0 ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading recipe matches...</p>
          </div>
        </div>
      ) : matches.length === 0 ? (
        <div className="bg-blue-50 border border-blue-200 text-blue-800 px-4 py-4 rounded-lg text-center">
          <p>No recipes to match. Add some recipes to your library first!</p>
        </div>
      ) : (
        <div className="space-y-4">
          {matches.map((match) => (
            <div
              key={match.recipe_id}
              className={`border rounded-lg p-5 transition-colors cursor-pointer ${getMatchBgColor(match.match_percentage)}`}
              onClick={() =>
                setExpandedRecipe(expandedRecipe === match.recipe_id ? null : match.recipe_id)
              }
            >
              {/* Header */}
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-semibold text-gray-900">{match.recipe_title}</h3>
                <div className="flex items-center gap-3">
                  <span className={`text-2xl font-bold ${getMatchColor(match.match_percentage)}`}>
                    {Math.round(match.match_percentage)}%
                  </span>
                  <span className="text-gray-600 text-sm">
                    {match.matched_ingredients}/{match.total_ingredients}
                  </span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
                <div
                  className={`h-2 rounded-full transition-all ${
                    match.match_percentage >= 80
                      ? 'bg-green-600'
                      : match.match_percentage >= 50
                        ? 'bg-blue-600'
                        : match.match_percentage >= 20
                          ? 'bg-yellow-600'
                          : 'bg-gray-400'
                  }`}
                  style={{ width: `${match.match_percentage}%` }}
                ></div>
              </div>

              {/* Summary */}
              <p className="text-sm text-gray-700 mb-3">
                {match.matched_ingredients} ingredient{match.matched_ingredients !== 1 ? 's' : ''} found
                {match.missing_ingredients.length > 0 &&
                  `, ${match.missing_ingredients.length} missing`}
              </p>

              {/* Expanded details */}
              {expandedRecipe === match.recipe_id && (
                <div className="mt-4 pt-4 border-t border-current border-opacity-20 space-y-3">
                  {/* Found ingredients */}
                  {match.ingredient_matches.filter((i) => i.found).length > 0 && (
                    <div>
                      <h4 className="font-medium text-gray-900 mb-2">✓ Found Ingredients:</h4>
                      <div className="space-y-2">
                        {match.ingredient_matches
                          .filter((i) => i.found)
                          .map((ing, idx) => (
                            <div key={idx} className="text-sm text-gray-700 bg-white bg-opacity-50 p-2 rounded">
                              <p>
                                <strong>{ing.original_text}</strong>
                              </p>
                              {ing.quantity && ing.unit && (
                                <p className="text-xs text-gray-600">
                                  {ing.quantity} {ing.unit}
                                </p>
                              )}
                            </div>
                          ))}
                      </div>
                    </div>
                  )}

                  {/* Missing ingredients */}
                  {match.ingredient_matches.filter((i) => !i.found).length > 0 && (
                    <div>
                      <h4 className="font-medium text-gray-900 mb-2">✕ Missing Ingredients:</h4>
                      <div className="space-y-2">
                        {match.ingredient_matches
                          .filter((i) => !i.found)
                          .map((ing, idx) => (
                            <div key={idx} className="text-sm text-gray-700 bg-white bg-opacity-50 p-2 rounded">
                              <p>
                                <strong>{ing.original_text}</strong>
                              </p>
                              {ing.quantity && ing.unit && (
                                <p className="text-xs text-gray-600">
                                  {ing.quantity} {ing.unit}
                                </p>
                              )}
                            </div>
                          ))}
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      router.push(`/review/${match.recipe_id}`)
                    }}
                    className="w-full mt-3 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors text-sm font-medium"
                  >
                    📖 View Recipe
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Info section */}
      <div className="bg-blue-50 border border-blue-200 p-6 rounded-lg space-y-3">
        <h3 className="font-semibold text-blue-900">💡 How Matching Works:</h3>
        <ul className="list-disc list-inside space-y-1 text-blue-800">
          <li>Recipes are scored based on how many ingredients you have in your pantry</li>
          <li>100% = You have everything for this recipe</li>
          <li>Green badges indicate recipes you can cook right now</li>
          <li>Blue badges indicate recipes where you're missing a few items</li>
          <li>Use the shopping list to see what you need to buy</li>
        </ul>
      </div>
    </div>
  )
}
