/**
 * Recipe edit form component
 */
'use client'

import { useState } from 'react'
import { Recipe, FieldStatus, SourceSpan } from '@/lib/api'
import { StatusBadge } from './StatusBadge'
import { RecipeStatusBadge } from './RecipeStatusBadge'

interface RecipeFormProps {
  recipe: Recipe
  fieldStatuses?: FieldStatus[]
  spans?: SourceSpan[]
  onUpdate?: (data: Partial<Recipe>) => Promise<void>
  onVerify?: () => Promise<void>
  loading?: boolean
  highlightedField?: string
  onFieldClick?: (fieldPath: string) => void
}

export function RecipeForm({
  recipe,
  fieldStatuses = [],
  spans = [],
  onUpdate,
  onVerify,
  loading = false,
  highlightedField,
  onFieldClick,
}: RecipeFormProps) {
  const [editedRecipe, setEditedRecipe] = useState<Partial<Recipe>>(recipe)
  const [isSaving, setIsSaving] = useState(false)

  const getStatusForField = (fieldPath: string) => {
    return fieldStatuses.find((s) => s.field_path === fieldPath)
  }

  const getSpanForField = (fieldPath: string) => {
    return spans.find((s) => s.field_path === fieldPath)
  }

  const handleFieldChange = (fieldPath: string, value: any) => {
    setEditedRecipe((prev) => {
      const newRecipe = { ...prev }

      // Handle nested paths like "ingredients[0].original_text"
      if (fieldPath.includes('[')) {
        const [arrayName, rest] = fieldPath.split('[')
        const indexMatch = rest.match(/(\d+)/)
        const index = indexMatch ? parseInt(indexMatch[1]) : 0
        const fieldName = rest.split('].')[1]

        if (!newRecipe[arrayName as keyof Recipe]) {
          newRecipe[arrayName as keyof Recipe] = [] as any
        }

        const arr = newRecipe[arrayName as keyof Recipe] as any[]
        arr[index] = { ...arr[index], [fieldName]: value }
      } else {
        newRecipe[fieldPath as keyof Recipe] = value
      }

      return newRecipe
    })
  }

  const handleSave = async () => {
    if (!onUpdate) return

    setIsSaving(true)
    try {
      await onUpdate(editedRecipe)
    } catch (err) {
      console.error('Failed to save:', err)
    } finally {
      setIsSaving(false)
    }
  }

  const hasChanges = JSON.stringify(editedRecipe) !== JSON.stringify(recipe)

  const isVerifyDisabled =
    !editedRecipe.title ||
    !editedRecipe.ingredients ||
    editedRecipe.ingredients.length === 0 ||
    !editedRecipe.steps ||
    editedRecipe.steps.length === 0

  return (
    <div className="bg-white rounded-lg shadow p-6 space-y-6 overflow-y-auto h-full">
      {/* Title */}
      <div
        className={`cursor-pointer p-4 rounded-lg border-2 ${
          highlightedField === 'title' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
        }`}
        onClick={() => onFieldClick?.('title')}
      >
        <div className="flex justify-between items-center mb-2">
          <label className="block text-sm font-medium text-gray-700">Recipe Title</label>
          <StatusBadge status={getStatusForField('title')?.status} className="text-xs" />
        </div>
        <input
          type="text"
          value={editedRecipe.title || ''}
          onChange={(e) => handleFieldChange('title', e.target.value)}
          placeholder="e.g., Pasta Carbonara"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          disabled={loading || isSaving}
        />
        {getSpanForField('title') && (
          <p className="text-xs text-gray-500 mt-1">
            OCR confidence: {Math.round(getSpanForField('title')!.ocr_confidence * 100)}%
          </p>
        )}
      </div>

      {/* Servings */}
      <div
        className={`cursor-pointer p-4 rounded-lg border-2 ${
          highlightedField === 'servings' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
        }`}
        onClick={() => onFieldClick?.('servings')}
      >
        <div className="flex justify-between items-center mb-2">
          <label className="block text-sm font-medium text-gray-700">Servings</label>
          <StatusBadge status={getStatusForField('servings')?.status} className="text-xs" />
        </div>
        <input
          type="number"
          value={editedRecipe.servings || ''}
          onChange={(e) => handleFieldChange('servings', e.target.value ? parseInt(e.target.value) : null)}
          placeholder="e.g., 4"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          disabled={loading || isSaving}
        />
      </div>

      {/* Ingredients */}
      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-900">Ingredients</h3>
          <StatusBadge status={getStatusForField('ingredients')?.status} className="text-xs" />
        </div>

        {editedRecipe.ingredients && editedRecipe.ingredients.length > 0 ? (
          editedRecipe.ingredients.map((ing, idx) => (
            <div
              key={idx}
              className={`cursor-pointer p-3 rounded-lg border-2 ${
                highlightedField === `ingredients[${idx}].original_text`
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200'
              }`}
              onClick={() => onFieldClick?.(`ingredients[${idx}].original_text`)}
            >
              <div className="grid grid-cols-3 gap-2 mb-2">
                <div>
                  <label className="block text-xs font-medium text-gray-700">Text</label>
                  <input
                    type="text"
                    value={ing.original_text || ''}
                    onChange={(e) => handleFieldChange(`ingredients[${idx}].original_text`, e.target.value)}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    disabled={loading || isSaving}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700">Qty</label>
                  <input
                    type="number"
                    step="0.01"
                    value={ing.quantity || ''}
                    onChange={(e) => handleFieldChange(`ingredients[${idx}].quantity`, e.target.value ? parseFloat(e.target.value) : null)}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    disabled={loading || isSaving}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700">Unit</label>
                  <input
                    type="text"
                    value={ing.unit || ''}
                    onChange={(e) => handleFieldChange(`ingredients[${idx}].unit`, e.target.value)}
                    placeholder="g, cup, tbsp"
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    disabled={loading || isSaving}
                  />
                </div>
              </div>
              {ing.name_norm && <p className="text-xs text-gray-500">Normalized: {ing.name_norm}</p>}
            </div>
          ))
        ) : (
          <p className="text-gray-500 italic">No ingredients yet</p>
        )}
      </div>

      {/* Steps */}
      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-900">Steps</h3>
          <StatusBadge status={getStatusForField('steps')?.status} className="text-xs" />
        </div>

        {editedRecipe.steps && editedRecipe.steps.length > 0 ? (
          editedRecipe.steps.map((step, idx) => (
            <div
              key={idx}
              className={`cursor-pointer p-3 rounded-lg border-2 ${
                highlightedField === `steps[${idx}].text`
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200'
              }`}
              onClick={() => onFieldClick?.(`steps[${idx}].text`)}
            >
              <label className="block text-xs font-medium text-gray-700 mb-1">Step {idx + 1}</label>
              <textarea
                value={step.text || ''}
                onChange={(e) => handleFieldChange(`steps[${idx}].text`, e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                rows={2}
                disabled={loading || isSaving}
              />
            </div>
          ))
        ) : (
          <p className="text-gray-500 italic">No steps yet</p>
        )}
      </div>

      {/* Tags */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Tags</label>
        <input
          type="text"
          value={(editedRecipe.tags || []).join(', ')}
          onChange={(e) => handleFieldChange('tags', e.target.value.split(',').map((t) => t.trim()))}
          placeholder="e.g., italian, pasta, vegetarian"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          disabled={loading || isSaving}
        />
      </div>

      {/* Actions - sticky on mobile */}
      <div className="sticky bottom-0 bg-white pt-4 pb-2 border-t flex gap-3 z-20 lg:relative lg:pt-4 lg:pb-0">
        <button
          onClick={handleSave}
          disabled={!hasChanges || loading || isSaving}
          className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors font-medium min-h-touch flex items-center justify-center"
        >
          {isSaving ? '💾 Saving...' : '💾 Save Changes'}
        </button>

        <button
          onClick={onVerify}
          disabled={isVerifyDisabled || loading || isSaving}
          title={
            isVerifyDisabled ? 'Recipe must have: title, at least 1 ingredient, at least 1 step' : ''
          }
          className="flex-1 px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 transition-colors font-medium min-h-touch flex items-center justify-center"
        >
          ✓ Verify Recipe
        </button>
      </div>

      {/* Status indicator */}
      <div className="pt-4 border-t">
        <p className="text-sm text-gray-600">
          <strong>Status:</strong> <RecipeStatusBadge status={recipe.status} />
        </p>
      </div>
    </div>
  )
}
