/**
 * Status badge component showing field extraction status
 */
import { FieldStatus } from '@/lib/api'

interface StatusBadgeProps {
  status?: FieldStatus['status']
  className?: string
}

export function StatusBadge({ status = 'missing', className = '' }: StatusBadgeProps) {
  const getStyle = (status: FieldStatus['status']) => {
    switch (status) {
      case 'extracted':
        return {
          bg: 'bg-green-100',
          text: 'text-green-800',
          label: '✓ Extracted',
        }
      case 'user_entered':
        return {
          bg: 'bg-blue-100',
          text: 'text-blue-800',
          label: '✎ User Entered',
        }
      case 'missing':
        return {
          bg: 'bg-red-100',
          text: 'text-red-800',
          label: '⚠ Missing',
        }
      case 'verified':
        return {
          bg: 'bg-green-100',
          text: 'text-green-800',
          label: '✓✓ Verified',
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
