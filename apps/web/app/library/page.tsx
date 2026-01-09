/**
 * Library page - displays list of recipes
 */
'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRecipeList } from '@/hooks/useRecipes'
import { StatusBadge } from '@/components/StatusBadge'

const DEMO_USER_ID = '550e8400-e29b-41d4-a716-446655440000' // Demo user for testing

export default function LibraryPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const { recipes, total, loading, error, fetch } = useRecipeList(DEMO_USER_ID)

  useEffect(() => {
    fetch({ query: searchQuery, status: statusFilter || undefined })
  }, [searchQuery, statusFilter, fetch])

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value)
  }

  const handleStatusFilter = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setStatusFilter(e.target.value)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">📚 Recipe Library</h1>
        <Link
          href="/upload"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          ⬆️ Upload Recipe
        </Link>
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
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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

      {/* Error display */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* Recipes Grid */}
      {recipes.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <p className="text-gray-600 mb-4">No recipes found</p>
          <Link
            href="/upload"
            className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Upload your first recipe
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {recipes.map((recipe) => (
            <Link
              key={recipe.id}
              href={`/review/${recipe.id}`}
              className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow overflow-hidden"
            >
              {/* Recipe card */}
              <div className="p-6">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="text-lg font-semibold text-gray-900 line-clamp-2">
                    {recipe.title || 'Untitled Recipe'}
                  </h3>
                  <StatusBadge status={recipe.status} />
                </div>

                {/* Recipe info */}
                <div className="space-y-2 text-sm text-gray-600 mb-4">
                  {recipe.servings && <p>🍽️ Servings: {recipe.servings}</p>}
                  {recipe.ingredients && recipe.ingredients.length > 0 && (
                    <p>📋 {recipe.ingredients.length} ingredients</p>
                  )}
                  {recipe.steps && recipe.steps.length > 0 && (
                    <p>👣 {recipe.steps.length} steps</p>
                  )}
                </div>

                {/* Tags */}
                {recipe.tags && recipe.tags.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {recipe.tags.slice(0, 3).map((tag) => (
                      <span
                        key={tag}
                        className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded"
                      >
                        {tag}
                      </span>
                    ))}
                    {recipe.tags.length > 3 && (
                      <span className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
                        +{recipe.tags.length - 3} more
                      </span>
                    )}
                  </div>
                )}

                {/* Date */}
                <div className="mt-4 text-xs text-gray-500">
                  {recipe.created_at && new Date(recipe.created_at).toLocaleDateString()}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
