/**
 * Upload page - for uploading recipe images
 */
'use client'

import { useState } from 'react'

export default function UploadPage() {
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const handleUpload = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setUploading(true)
    setMessage(null)

    try {
      const formData = new FormData(e.currentTarget)
      // TODO: Implement actual upload to /assets/upload endpoint
      setMessage({ type: 'success', text: 'Upload feature coming soon!' })
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Upload failed',
      })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl md:text-3xl font-bold text-gray-900">⬆️ Upload Recipe</h1>

      <div className="bg-white rounded-lg shadow p-8">
        <form onSubmit={handleUpload} className="space-y-6">
          {/* File upload area */}
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-blue-500 transition-colors">
            <div className="space-y-2">
              <p className="text-2xl">📸</p>
              <p className="text-lg font-medium text-gray-900">Drag and drop your recipe image here</p>
              <p className="text-gray-600">or click to select a file</p>
              <p className="text-sm text-gray-500 mt-4">
                Supports: JPEG, PNG, PDF (max 10MB)
              </p>
            </div>
            <input
              type="file"
              name="file"
              accept=".jpg,.jpeg,.png,.pdf"
              className="hidden"
              disabled={uploading}
            />
          </div>

          {/* Source label */}
          <div>
            <label htmlFor="source_label" className="block text-sm font-medium text-gray-700 mb-2">
              Source label (optional)
            </label>
            <input
              type="text"
              id="source_label"
              name="source_label"
              placeholder="e.g., Family cookbook, Instagram, website"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={uploading}
            />
          </div>

          {/* Message */}
          {message && (
            <div
              className={`p-4 rounded-lg ${
                message.type === 'success'
                  ? 'bg-green-50 text-green-800 border border-green-200'
                  : 'bg-red-50 text-red-800 border border-red-200'
              }`}
            >
              {message.text}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={uploading}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors font-medium"
            >
              {uploading ? '⏳ Uploading...' : '⬆️ Upload Recipe'}
            </button>
            <a
              href="/library"
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium text-center"
            >
              ← Back to Library
            </a>
          </div>
        </form>
      </div>

      {/* Info section */}
      <div className="bg-blue-50 border border-blue-200 p-6 rounded-lg space-y-3">
        <h3 className="font-semibold text-blue-900">📝 What happens after upload:</h3>
        <ol className="list-decimal list-inside space-y-2 text-blue-800">
          <li>Image is stored securely</li>
          <li>OCR extracts text and creates OCRLines</li>
          <li>Structure job parses recipe sections</li>
          <li>You review and verify the extracted data</li>
          <li>Recipe is ready to match against your pantry</li>
        </ol>
      </div>
    </div>
  )
}
