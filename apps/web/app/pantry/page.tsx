/**
 * Pantry page - manage pantry items and match recipes
 */
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  listPantryItems,
  createPantryItem,
  deletePantryItem,
  matchAllRecipes,
  PantryItem,
  PantryItemRequest,
} from '@/lib/api'
import { Swipeable } from '@/components/Swipeable'
import { PullToRefresh } from '@/components/PullToRefresh'

const DEMO_USER_ID = '550e8400-e29b-41d4-a716-446655440000' // Demo user for testing

export default function PantryPage() {
  const router = useRouter()

  // Pantry state
  const [pantryItems, setPantryItems] = useState<PantryItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>()

  // New item form state
  const [newItem, setNewItem] = useState('')
  const [newQuantity, setNewQuantity] = useState('')
  const [newUnit, setNewUnit] = useState('')
  const [isAdding, setIsAdding] = useState(false)

  // Search state
  const [searchQuery, setSearchQuery] = useState('')

  // Load pantry items on mount
  useEffect(() => {
    fetchPantryItems()
  }, [])

  const fetchPantryItems = async () => {
    try {
      setLoading(true)
      setError(undefined)
      const response = await listPantryItems(DEMO_USER_ID, {
        limit: 100,
        query: searchQuery || undefined,
      })
      setPantryItems(response.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load pantry items')
    } finally {
      setLoading(false)
    }
  }

  const handleAddItem = async () => {
    if (!newItem.trim()) return

    try {
      setIsAdding(true)
      const itemData: PantryItemRequest = {
        name_original: newItem.trim(),
        quantity: newQuantity ? parseFloat(newQuantity) : undefined,
        unit: newUnit || undefined,
      }
      await createPantryItem(DEMO_USER_ID, itemData)

      // Reset form and refresh list
      setNewItem('')
      setNewQuantity('')
      setNewUnit('')
      await fetchPantryItems()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add pantry item')
    } finally {
      setIsAdding(false)
    }
  }

  const handleDeleteItem = async (itemId: string) => {
    if (!confirm('Remove this item from pantry?')) return

    try {
      await deletePantryItem(DEMO_USER_ID, itemId)
      await fetchPantryItems()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete pantry item')
    }
  }

  const handleWhatCanICook = async () => {
    try {
      setLoading(true)
      await matchAllRecipes(DEMO_USER_ID)
      // Navigate to match results page
      router.push('/match')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to match recipes')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h1 className="text-2xl md:text-3xl font-bold text-gray-900">🥘 Pantry</h1>

      {/* Error message */}
      {error && <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">{error}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pantry items */}
        <PullToRefresh
          onRefresh={fetchPantryItems}
          className="lg:col-span-2 bg-white rounded-lg shadow p-6"
        >
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Your Pantry Items ({pantryItems.length})</h2>

          {/* Search */}
          <div className="mb-4">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && fetchPantryItems()}
              placeholder="Search pantry items..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm min-h-touch"
            />
          </div>

          {/* Items list */}
          <div className="space-y-3 mb-6 max-h-96 overflow-y-auto">
            {loading && pantryItems.length === 0 ? (
              <p className="text-gray-500 italic">Loading pantry items...</p>
            ) : pantryItems.length === 0 ? (
              <p className="text-gray-500 italic">No items in pantry yet. Add some below!</p>
            ) : (
              pantryItems.map((item) => (
                <Swipeable
                  key={item.id}
                  onSwipeLeft={() => handleDeleteItem(item.id)}
                  leftActions={
                    <button
                      onClick={() => handleDeleteItem(item.id)}
                      className="bg-red-600 text-white px-4 py-3 h-full flex items-center justify-center font-medium"
                    >
                      Delete
                    </button>
                  }
                >
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer">
                    <div className="flex-1">
                      <p className="text-gray-900 font-medium">{item.name_original}</p>
                      <p className="text-sm text-gray-500">
                        {item.quantity && item.unit ? `${item.quantity} ${item.unit}` : ''}
                        {item.quantity && !item.unit ? `${item.quantity}` : ''}
                        {item.name_norm && item.name_norm !== item.name_original && (
                          <span className="text-xs text-gray-400 ml-2">(norm: {item.name_norm})</span>
                        )}
                      </p>
                    </div>
                    <span className="text-gray-400 text-sm">Swipe to delete</span>
                  </div>
                </Swipeable>
              ))
            )}
          </div>

          {/* Add new item */}
          <div className="pt-4 border-t space-y-3">
            <h3 className="text-sm font-semibold text-gray-700">Add New Item</h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <input
                type="text"
                value={newItem}
                onChange={(e) => setNewItem(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAddItem()}
                placeholder="Ingredient (e.g., flour)"
                className="col-span-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm min-h-touch"
                disabled={isAdding}
              />
              <input
                type="number"
                value={newQuantity}
                onChange={(e) => setNewQuantity(e.target.value)}
                placeholder="Qty"
                step="0.1"
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm min-h-touch"
                disabled={isAdding}
              />
              <input
                type="text"
                value={newUnit}
                onChange={(e) => setNewUnit(e.target.value)}
                placeholder="Unit (cups, g)"
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm min-h-touch"
                disabled={isAdding}
              />
            </div>
            <button
              onClick={handleAddItem}
              disabled={!newItem.trim() || isAdding}
              className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors font-medium min-h-touch flex items-center justify-center"
            >
              {isAdding ? '⏳ Adding...' : '+ Add Item'}
            </button>
          </div>
        </PullToRefresh>

        {/* Actions */}
        <div className="bg-white rounded-lg shadow p-6 space-y-4">
          <h2 className="text-xl font-semibold text-gray-900">Quick Actions</h2>

          <button
            onClick={handleWhatCanICook}
            disabled={loading || pantryItems.length === 0}
            title={pantryItems.length === 0 ? 'Add pantry items first' : ''}
            className="w-full px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium min-h-touch flex items-center justify-center"
          >
            🔍 What Can I Cook?
          </button>

          <button
            onClick={() => router.push('/match')}
            disabled={loading}
            className="w-full px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 transition-colors font-medium min-h-touch flex items-center justify-center"
          >
            📊 View Match Results
          </button>

          <button
            onClick={() => router.push('/library')}
            className="w-full px-4 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors font-medium min-h-touch flex items-center justify-center"
          >
            📚 Back to Library
          </button>
        </div>
      </div>

      {/* Info section */}
      <div className="bg-blue-50 border border-blue-200 p-6 rounded-lg space-y-3">
        <h3 className="font-semibold text-blue-900">💡 About Pantry Matching:</h3>
        <p className="text-blue-800">
          Add ingredients to your pantry to see which recipes you can cook. The system will show you the
          match percentage for each recipe based on available ingredients.
        </p>
        <p className="text-blue-800">
          Once you add pantry items, click "What Can I Cook?" to discover recipes you can prepare with
          what you have on hand!
        </p>
        <p className="text-sm text-blue-700 mt-2">
          <strong>Tip:</strong> Ingredient names are automatically normalized for accurate matching.
        </p>
      </div>
    </div>
  )
}
