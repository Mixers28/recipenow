/**
 * Recipe Review page - split view with image and editable form
 */
'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import { useRecipe } from '@/hooks/useRecipes'
import { ImageViewer } from '@/components/ImageViewer'
import { RecipeForm } from '@/components/RecipeForm'
import { SourceSpan } from '@/lib/api'

const DEMO_USER_ID = '550e8400-e29b-41d4-a716-446655440000' // Demo user for testing

export default function ReviewPage() {
  const params = useParams()
  const recipeId = params.id as string
  const [highlightedField, setHighlightedField] = useState<string>()
  const [verifyLoading, setVerifyLoading] = useState(false)
  const [verifyError, setVerifyError] = useState<string>()

  const { recipe, spans, fieldStatuses, loading, error, update, verify } = useRecipe(
    DEMO_USER_ID,
    recipeId
  )

  // Mock image URL - in production would come from asset API
  const imageUrl = `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='600'%3E%3Crect fill='%23ddd' width='800' height='600'/%3E%3Ctext x='50' y='50' font-size='24' fill='%23666'%3ERecipe Image Placeholder%3C/text%3E%3Ctext x='50' y='100' font-size='14' fill='%23999'%3EImage from asset would be displayed here%3C/text%3E%3C/svg%3E`

  const handleBboxClick = (bbox: SourceSpan['bbox'], fieldPath: string) => {
    setHighlightedField(fieldPath)
  }

  const handleFieldClick = (fieldPath: string) => {
    setHighlightedField(fieldPath)
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

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">
          {recipe.title || 'Untitled Recipe'} - Review
        </h1>
        <a
          href="/library"
          className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
        >
          ← Back to Library
        </a>
      </div>

      {/* Verify error message */}
      {verifyError && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
          <strong>Verification failed:</strong> {verifyError}
        </div>
      )}

      {/* Split View Container */}
      <div className="grid grid-cols-2 gap-6 h-screen -mb-8">
        {/* Left: Image Viewer */}
        <div className="overflow-hidden rounded-lg">
          <ImageViewer
            imageUrl={imageUrl}
            spans={spans}
            highlightedFieldPath={highlightedField}
            onBboxClick={handleBboxClick}
          />
        </div>

        {/* Right: Recipe Form */}
        <div className="overflow-hidden rounded-lg">
          <RecipeForm
            recipe={recipe}
            fieldStatuses={fieldStatuses}
            spans={spans}
            onUpdate={update}
            onVerify={handleVerify}
            loading={loading || verifyLoading}
            highlightedField={highlightedField}
            onFieldClick={handleFieldClick}
          />
        </div>
      </div>

      {/* Info Section */}
      <div className="mt-8 bg-blue-50 border border-blue-200 p-4 rounded-lg text-sm text-blue-900">
        <p>
          <strong>💡 Tips:</strong> Click on any field in the form to highlight its location on the
          image. Click on any bbox on the image to select that field. Edit fields as needed and click
          "Save Changes" to update. When complete, click "Verify Recipe" to mark it as verified.
        </p>
      </div>
    </div>
  )
}
