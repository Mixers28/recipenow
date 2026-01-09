/**
 * Recipe status badge component showing recipe completion status
 */

interface RecipeStatusBadgeProps {
  status: 'draft' | 'needs_review' | 'verified'
  className?: string
}

export function RecipeStatusBadge({ status, className = '' }: RecipeStatusBadgeProps) {
  const getStyle = (status: 'draft' | 'needs_review' | 'verified') => {
    switch (status) {
      case 'draft':
        return {
          bg: 'bg-yellow-100',
          text: 'text-yellow-800',
          label: '✏️ Draft',
        }
      case 'needs_review':
        return {
          bg: 'bg-orange-100',
          text: 'text-orange-800',
          label: '👀 Needs Review',
        }
      case 'verified':
        return {
          bg: 'bg-green-100',
          text: 'text-green-800',
          label: '✓ Verified',
        }
      default:
        return {
          bg: 'bg-gray-100',
          text: 'text-gray-800',
          label: 'Unknown',
        }
    }
  }

  const style = getStyle(status)

  return (
    <span
      className={`inline-block px-2 py-1 text-xs font-semibold rounded-full ${style.bg} ${style.text} ${className}`}
    >
      {style.label}
    </span>
  )
}
