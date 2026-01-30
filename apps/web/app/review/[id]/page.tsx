/**
 * Recipe Review page
 * - For verified recipes: Shows flip card (image front, recipe back)
 * - For draft/needs_review: Shows edit form with tabs
 */
'use client'

import { useState, lazy, Suspense, useEffect } from 'react'
import { useParams, useSearchParams } from 'next/navigation'
import { useRecipe } from '@/hooks/useRecipes'
import { Tabs } from '@/components/Tabs'
import { SourceSpan, Recipe, getAsset } from '@/lib/api'
import { SkeletonImageViewer, SkeletonRecipeForm } from '@/components/SkeletonLoader'
import { FlipRecipeCard } from '@/components/FlipRecipeCard'

const ImageViewer = lazy(() => import('@/components/ImageViewer').then(m => ({ default: m.ImageViewer })))
const RecipeForm = lazy(() => import('@/components/RecipeForm').then(m => ({ default: m.RecipeForm })))

const DEMO_USER_ID = '550e8400-e29b-41d4-a716-446655440000' // Demo user for testing

export default function ReviewPage() {
  const params = useParams()
  const searchParams = useSearchParams()
  const recipeId = params.id as string
  const assetId = searchParams.get('asset_id')

  const [highlightedField, setHighlightedField] = useState<string>()
  const [verifyLoading, setVerifyLoading] = useState(false)
  const [verifyError, setVerifyError] = useState<string>()
  const [imageUrl, setImageUrl] = useState<string>('')
  const [imageLoading, setImageLoading] = useState(false)
  const [editMode, setEditMode] = useState(false)

  const { recipe, spans, fieldStatuses, loading, error, update, verify } = useRecipe(
    DEMO_USER_ID,
    recipeId
  )

  // Fetch actual image from asset; fall back to spans to discover asset_id
  useEffect(() => {
    const resolvedAssetId =
      assetId || (spans && spans.length > 0 ? spans[0].asset_id : undefined)

    if (!resolvedAssetId) {
      // No asset provided, use placeholder
      setImageUrl(
        `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='600'%3E%3Crect fill='%23ddd' width='800' height='600'/%3E%3Ctext x='50' y='50' font-size='24' fill='%23666'%3ERecipe Image Placeholder%3C/text%3E%3Ctext x='50' y='100' font-size='14' fill='%23999'%3ENo image available%3C/text%3E%3C/svg%3E`
      )
      return
    }

    let objectUrl: string | null = null

    const fetchImage = async () => {
      setImageLoading(true)
      try {
        const blob = await getAsset(resolvedAssetId)
        objectUrl = URL.createObjectURL(blob)
        setImageUrl(objectUrl)
      } catch (err) {
        console.error('Failed to fetch image:', err)
        // Fall back to placeholder
        setImageUrl(
          `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='600'%3E%3Crect fill='%23fdd' width='800' height='600'/%3E%3Ctext x='50' y='50' font-size='24' fill='%23c33'%3EFailed to load image%3C/text%3E%3C/svg%3E`
        )
      } finally {
        setImageLoading(false)
      }
    }

    fetchImage()

    // Cleanup object URL on unmount or asset change
    return () => {
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl)
      }
    }
  }, [assetId, spans])

  const handleBboxClick = (bbox: SourceSpan['bbox'], fieldPath: string) => {
    setHighlightedField(fieldPath)
  }

  const handleFieldClick = (fieldPath: string) => {
    setHighlightedField(fieldPath)
  }

  const handleUpdate = async (data: Partial<Recipe>) => {
    await update(data)
  }

  const handleVerify = async () => {
    setVerifyLoading(true)
    setVerifyError(undefined)
    try {
      const result = await verify()
      if (result.errors.length > 0) {
        setVerifyError(result.errors.join(', '))
      } else {
        setVerifyError(undefined)
        setEditMode(false) // Exit edit mode on successful verify
      }
    } catch (err) {
      setVerifyError(err instanceof Error ? err.message : 'Failed to verify recipe')
    } finally {
      setVerifyLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading recipe...</p>
        </div>
      </div>
    )
  }

  if (error || !recipe) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
        {error || 'Recipe not found'}
      </div>
    )
  }

  // Show flip card for verified recipes (unless in edit mode)
  const isVerified = recipe.status === 'verified'
  const showCardView = isVerified && !editMode

  if (showCardView) {
    return (
      <div className="space-y-4 py-4">
        {/* Header */}
        <div className="flex justify-between items-center max-w-2xl mx-auto">
          <h1 className="text-xl font-bold text-gray-900">
            {recipe.title || 'Recipe'}
          </h1>
          <a
            href="/library"
            className="text-sm text-gray-600 hover:text-gray-800"
          >
            ← Back to Library
          </a>
        </div>

        {/* Flip Card */}
        <FlipRecipeCard
          recipe={recipe}
          imageUrl={imageUrl}
          onEdit={() => setEditMode(true)}
        />
      </div>
    )
  }

  // Show edit form for draft/needs_review or when edit mode is active
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">
          {recipe.title || 'Untitled Recipe'} - Review
        </h1>
        <div className="flex gap-2">
          {editMode && (
            <button
              onClick={() => setEditMode(false)}
              className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              ← Back to Card
            </button>
          )}
          <a
            href="/library"
            className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            ← Library
          </a>
        </div>
      </div>

      {/* Verify error message */}
      {verifyError && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
          <strong>Verification failed:</strong> {verifyError}
        </div>
      )}

      {/* Tabbed View */}
      <div className="h-[calc(100vh-200px)]">
        <Tabs
          tabs={[
            {
              id: 'image',
              label: 'Image',
              content: (
                <div className="h-full overflow-hidden">
                  <Suspense fallback={<SkeletonImageViewer />}>
                    <ImageViewer
                      imageUrl={imageUrl}
                      spans={spans}
                      highlightedFieldPath={highlightedField}
                      onBboxClick={handleBboxClick}
                    />
                  </Suspense>
                </div>
              ),
            },
            {
              id: 'form',
              label: 'Recipe',
              content: (
                <div className="h-full overflow-y-auto">
                  <Suspense fallback={<SkeletonRecipeForm />}>
                    <RecipeForm
                      recipe={recipe}
                      fieldStatuses={fieldStatuses}
                      spans={spans}
                      onUpdate={handleUpdate}
                      onVerify={handleVerify}
                      loading={loading || verifyLoading}
                      highlightedField={highlightedField}
                      onFieldClick={handleFieldClick}
                    />
                  </Suspense>
                </div>
              ),
            },
          ]}
          defaultTab="image"
        />
      </div>

      {/* Info Section */}
      <div className="mt-8 bg-blue-50 border border-blue-200 p-4 rounded-lg text-sm text-blue-900">
        <p>
          <strong>Tips:</strong> Click on any field in the form to highlight its location on the
          image. Edit fields as needed and click "Save Changes" to update. When complete, click
          "Verify Recipe" to mark it as verified.
        </p>
      </div>
    </div>
  )
}
