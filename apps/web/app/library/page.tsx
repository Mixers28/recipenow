/**
 * Library page - displays list of recipes
 */
'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRecipeList } from '@/hooks/useRecipes'
import { deleteRecipe, cleanupEmptyRecipes, cleanupAllRecipes } from '@/lib/api'
import { useDebounce } from '@/hooks/useDebounce'
import { RecipeThumbnailCard } from '@/components/RecipeThumbnailCard'
import { PullToRefresh } from '@/components/PullToRefresh'

const DEMO_USER_ID = '550e8400-e29b-41d4-a716-446655440000' // Demo user for testing

export default function LibraryPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [actionError, setActionError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [cleaningUp, setCleaningUp] = useState(false)
  const [cleanupMessage, setCleanupMessage] = useState<string | null>(null)
  const debouncedSearchQuery = useDebounce(searchQuery, 300)
  const { recipes, total, loading, error, fetch } = useRecipeList(DEMO_USER_ID)

  useEffect(() => {
    fetch({ query: debouncedSearchQuery, status: statusFilter || undefined })
  }, [debouncedSearchQuery, statusFilter, fetch])

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value)
  }

  const handleStatusFilter = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setStatusFilter(e.target.value)
  }

  const handleDelete = async (e: React.MouseEvent, recipeId: string) => {
    e.preventDefault()
    e.stopPropagation()
    const confirmed = confirm('Delete this recipe? This cannot be undone.')
    if (!confirmed) return

    try {
      setDeletingId(recipeId)
      setActionError(null)
      await deleteRecipe(DEMO_USER_ID, recipeId)
      await fetch({ query: searchQuery, status: statusFilter || undefined })
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to delete recipe')
    } finally {
      setDeletingId(null)
    }
  }

  const handleCleanup = async () => {
    const confirmed = confirm('Delete all failed recipes (no ingredients and no steps)? This cannot be undone.')
    if (!confirmed) return

    try {
      setCleaningUp(true)
      setActionError(null)
      setCleanupMessage(null)
      const result = await cleanupEmptyRecipes(DEMO_USER_ID)
      setCleanupMessage(result.message)
      await fetch({ query: searchQuery, status: statusFilter || undefined })
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to cleanup recipes')
    } finally {
      setCleaningUp(false)
    }
  }

  const handleCleanupAll = async () => {
    const confirmed = confirm('DELETE ALL RECIPES? This will remove everything and cannot be undone!')
    if (!confirmed) return

    try {
      setCleaningUp(true)
      setActionError(null)
      setCleanupMessage(null)
      const result = await cleanupAllRecipes(DEMO_USER_ID)
      setCleanupMessage(result.message)
      await fetch({ query: searchQuery, status: statusFilter || undefined })
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to cleanup all recipes')
    } finally {
      setCleaningUp(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center gap-4">
        <h1 className="text-2xl md:text-3xl font-bold text-gray-900">Recipe Library</h1>
        <div className="flex gap-2">
          <button
            onClick={handleCleanupAll}
            disabled={cleaningUp}
            className="px-3 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm min-h-touch flex items-center whitespace-nowrap disabled:opacity-50"
            title="Delete ALL recipes (for testing)"
          >
            {cleaningUp ? '...' : 'Reset All'}
          </button>
          <button
            onClick={handleCleanup}
            disabled={cleaningUp}
            className="px-3 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors text-sm min-h-touch flex items-center whitespace-nowrap disabled:opacity-50"
            title="Delete all recipes with no ingredients and no steps"
          >
            {cleaningUp ? '...' : 'Clean Failed'}
          </button>
          <Link
            href="/upload"
            className="px-3 py-2 md:px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm md:text-base min-h-touch flex items-center whitespace-nowrap"
          >
            <span className="hidden md:inline">Upload Recipe</span>
            <span className="md:hidden">+</span>
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Search */}
          <div>
            <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-2">
              Search by title
            </label>
            <input
              id="search"
              type="text"
              value={searchQuery}
              onChange={handleSearch}
              placeholder="e.g., Pasta Carbonara..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent min-h-touch"
            />
          </div>

          {/* Status Filter */}
          <div>
            <label htmlFor="status" className="block text-sm font-medium text-gray-700 mb-2">
              Filter by status
            </label>
            <select
              id="status"
              value={statusFilter}
              onChange={handleStatusFilter}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent min-h-touch"
            >
              <option value="">All Statuses</option>
              <option value="draft">Draft</option>
              <option value="needs_review">Needs Review</option>
              <option value="verified">Verified</option>
            </select>
          </div>
        </div>

        {/* Results count */}
        <div className="text-sm text-gray-600">
          {loading ? 'Loading...' : `${recipes.length} of ${total} recipes`}
        </div>
      </div>

      {/* Success message */}
      {cleanupMessage && (
        <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-lg flex justify-between items-center">
          <span>{cleanupMessage}</span>
          <button onClick={() => setCleanupMessage(null)} className="text-green-600 hover:text-green-800">
            ✕
          </button>
        </div>
      )}

      {/* Error display */}
      {(error || actionError) && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
          {actionError || error}
        </div>
      )}

      {/* Recipes Grid with Pull-to-Refresh */}
      <PullToRefresh onRefresh={() => fetch({ query: searchQuery, status: statusFilter || undefined })} className="h-96">
        {recipes.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <p className="text-gray-600 mb-4">No recipes found</p>
            <Link
              href="/upload"
              className="inline-block px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 min-h-touch"
            >
              Upload your first recipe
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {recipes.map((recipe) => (
              <Link key={recipe.id} href={`/review/${recipe.id}`}>
                <RecipeThumbnailCard
                  recipe={recipe}
                  onDelete={handleDelete}
                  isDeleting={deletingId === recipe.id}
                />
              </Link>
            ))}
          </div>
        )}
      </PullToRefresh>
    </div>
  )
}
