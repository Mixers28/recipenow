/**
 * Upload page - for uploading recipe images
 */
'use client'

import { useRouter } from 'next/navigation'
import { useRef, useState } from 'react'
import { useUser } from '@auth0/nextjs-auth0/client'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface UploadResponse {
  asset_id: string
  storage_path: string
  sha256: string
  job_id?: string
}

export default function UploadPage() {
  const router = useRouter()
  const { user } = useUser()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [dragActive, setDragActive] = useState(false)

  const handleDrag = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    const files = e.dataTransfer.files
    if (files && files[0]) {
      setSelectedFile(files[0])
    }
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0])
    }
  }

  const handleUpload = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()

    if (!selectedFile) {
      setMessage({ type: 'error', text: 'Please select a file to upload' })
      return
    }

    if (!user?.sub) {
      setMessage({ type: 'error', text: 'User not authenticated' })
      return
    }

    setUploading(true)
    setMessage(null)

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      formData.append('user_id', user.sub)

      const sourceLabel = (e.currentTarget.elements.namedItem('source_label') as HTMLInputElement)?.value
      if (sourceLabel) {
        formData.append('source_label', sourceLabel)
      }

      const response = await fetch(`${API_BASE}/assets/upload`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || `Upload failed: ${response.status}`)
      }

      const data: UploadResponse = await response.json()
      setMessage({ type: 'success', text: 'Upload successful! Redirecting to review...' })

      // Redirect to review page after 1 second
      setTimeout(() => {
        router.push(`/review/${data.asset_id}`)
      }, 1000)
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
          <div
            className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors cursor-pointer ${
              dragActive
                ? 'border-blue-500 bg-blue-50'
                : selectedFile
                  ? 'border-green-500 bg-green-50'
                  : 'border-gray-300 hover:border-blue-500'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <div className="space-y-2">
              <p className="text-2xl">{selectedFile ? '✅' : '📸'}</p>
              {selectedFile ? (
                <>
                  <p className="text-lg font-medium text-gray-900">File selected</p>
                  <p className="text-gray-700 font-semibold">{selectedFile.name}</p>
                  <p className="text-sm text-gray-500">
                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                  <p className="text-sm text-gray-600 mt-2">Click to change file</p>
                </>
              ) : (
                <>
                  <p className="text-lg font-medium text-gray-900">Drag and drop your recipe image here</p>
                  <p className="text-gray-600">or click to select a file</p>
                  <p className="text-sm text-gray-500 mt-4">
                    Supports: JPEG, PNG, PDF (max 10MB)
                  </p>
                </>
              )}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              name="file"
              accept=".jpg,.jpeg,.png,.pdf"
              className="hidden"
              disabled={uploading}
              onChange={handleFileInput}
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
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              type="submit"
              disabled={uploading || !selectedFile}
              className="flex-1 px-4 py-3 sm:py-2 min-h-touch bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {uploading ? '⏳ Uploading...' : '⬆️ Upload Recipe'}
            </button>
            <a
              href="/library"
              className="flex-1 px-4 py-3 sm:py-2 min-h-touch border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium text-center"
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
