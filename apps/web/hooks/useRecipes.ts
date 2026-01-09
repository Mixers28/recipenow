/**
 * Custom hook for managing recipes
 */
'use client'

import { useState, useCallback, useEffect } from 'react'
import {
  listRecipes,
  getRecipe,
  updateRecipe,
  verifyRecipe,
  listSpans,
  listFieldStatuses,
  type Recipe,
  type SourceSpan,
  type FieldStatus,
  type RecipeListResponse,
  type VerifyResponse,
} from '@/lib/api'

export function useRecipeList(userId: string) {
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(
    async (options?: { query?: string; status?: string; tags?: string[]; skip?: number; limit?: number }) => {
      setLoading(true)
      setError(null)
      try {
        const response = await listRecipes(userId, options)
        setRecipes(response.recipes)
        setTotal(response.total)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch recipes')
      } finally {
        setLoading(false)
      }
    },
    [userId]
  )

  return { recipes, total, loading, error, fetch }
}

export function useRecipe(userId: string, recipeId: string) {
  const [recipe, setRecipe] = useState<Recipe | null>(null)
  const [spans, setSpans] = useState<SourceSpan[]>([])
  const [fieldStatuses, setFieldStatuses] = useState<FieldStatus[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const recipeData = await getRecipe(userId, recipeId)
      const spansData = await listSpans(userId, recipeId)
      const statusesData = await listFieldStatuses(userId, recipeId)

      setRecipe(recipeData)
      setSpans(spansData)
      setFieldStatuses(statusesData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch recipe details')
    } finally {
      setLoading(false)
    }
  }, [userId, recipeId])

  useEffect(() => {
    fetch()
  }, [fetch])

  const update = useCallback(
    async (data: Partial<Recipe>) => {
      setLoading(true)
      setError(null)
      try {
        const updated = await updateRecipe(userId, recipeId, data)
        setRecipe(updated)
        // Refetch spans and statuses after update
        const spansData = await listSpans(userId, recipeId)
        const statusesData = await listFieldStatuses(userId, recipeId)
        setSpans(spansData)
        setFieldStatuses(statusesData)
        return updated
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update recipe'
        setError(message)
        throw err
      } finally {
        setLoading(false)
      }
    },
    [userId, recipeId]
  )

  const verify = useCallback(async (): Promise<VerifyResponse> => {
    setLoading(true)
    setError(null)
    try {
      const result = await verifyRecipe(userId, recipeId)
      if (result.status === 'verified') {
        setRecipe((prev) => (prev ? { ...prev, status: 'verified' } : null))
      }
      return result
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to verify recipe'
      setError(message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [userId, recipeId])

  return {
    recipe,
    spans,
    fieldStatuses,
    loading,
    error,
    fetch,
    update,
    verify,
  }
}

// Helper to get span for a field
export function getSpanForField(spans: SourceSpan[], fieldPath: string): SourceSpan | undefined {
  return spans.find((s) => s.field_path === fieldPath)
}

// Helper to get status for a field
export function getStatusForField(statuses: FieldStatus[], fieldPath: string): FieldStatus | undefined {
  return statuses.find((s) => s.field_path === fieldPath)
}

// Helper to get status color
export function getStatusColor(
  status: FieldStatus['status'] | undefined
): 'green' | 'blue' | 'red' | 'gray' {
  switch (status) {
    case 'extracted':
      return 'green'
    case 'user_entered':
      return 'blue'
    case 'missing':
      return 'red'
    case 'verified':
      return 'green'
    default:
      return 'gray'
  }
}
