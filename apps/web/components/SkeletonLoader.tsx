/**
 * Skeleton loaders for improved loading UX
 */

export function SkeletonRect({
  height = 'h-4',
  width = 'w-full',
  className = '',
}: {
  height?: string
  width?: string
  className?: string
}) {
  return (
    <div
      className={`bg-gradient-to-r from-gray-200 via-gray-300 to-gray-200 rounded animate-pulse ${height} ${width} ${className}`}
      style={{
        backgroundSize: '200% 100%',
        animation: 'shimmer 1.5s infinite',
      }}
    />
  )
}

export function SkeletonImageViewer() {
  return (
    <div className="w-full h-full bg-gray-100 rounded-lg flex items-center justify-center">
      <div className="text-center space-y-3 w-3/4">
        <SkeletonRect height="h-64" />
        <SkeletonRect height="h-8" width="w-1/2" className="mx-auto" />
        <div className="flex gap-2">
          <SkeletonRect height="h-10" width="w-12" />
          <SkeletonRect height="h-10" width="w-12" />
          <SkeletonRect height="h-10" width="w-12" />
        </div>
      </div>
    </div>
  )
}

export function SkeletonRecipeForm() {
  return (
    <div className="w-full h-full space-y-6 p-6 bg-gray-50 rounded-lg overflow-y-auto">
      {/* Title section */}
      <div className="space-y-2">
        <SkeletonRect height="h-6" width="w-1/3" />
        <SkeletonRect height="h-10" />
      </div>

      {/* Sections */}
      {[1, 2, 3].map((i) => (
        <div key={i} className="space-y-3">
          <SkeletonRect height="h-5" width="w-1/4" />
          <SkeletonRect height="h-20" />
        </div>
      ))}

      {/* Action buttons */}
      <div className="flex gap-3 pt-4">
        <SkeletonRect height="h-12" width="w-1/2" />
        <SkeletonRect height="h-12" width="w-1/2" />
      </div>
    </div>
  )
}

export function SkeletonRecipeCard() {
  return (
    <div className="bg-white rounded-lg shadow p-6 space-y-4">
      <div className="flex justify-between items-start gap-2">
        <SkeletonRect height="h-6" width="w-3/4" />
        <SkeletonRect height="h-6" width="w-1/4" />
      </div>

      <div className="space-y-2">
        <SkeletonRect height="h-4" />
        <SkeletonRect height="h-4" width="w-3/4" />
      </div>

      <div className="flex gap-2">
        <SkeletonRect height="h-6" width="w-16" />
        <SkeletonRect height="h-6" width="w-16" />
      </div>

      <SkeletonRect height="h-4" width="w-1/2" />
    </div>
  )
}

export function SkeletonLibraryGrid() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {[1, 2, 3, 4, 5, 6].map((i) => (
        <SkeletonRecipeCard key={i} />
      ))}
    </div>
  )
}
