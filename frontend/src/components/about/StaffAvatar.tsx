import { useState } from 'react'

interface StaffAvatarProps {
  name: string
  photoUrl: string | null
  colorClass: string
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/)
  if (parts.length === 1) return (parts[0]?.[0] || '').toUpperCase()
  return ((parts[0]?.[0] || '') + (parts[parts.length - 1]?.[0] || '')).toUpperCase()
}

export function StaffAvatar({ name, photoUrl, colorClass }: StaffAvatarProps) {
  const [imgFailed, setImgFailed] = useState(false)

  if (photoUrl && !imgFailed) {
    return (
      <img
        src={photoUrl}
        alt={`Photo of ${name}`}
        loading="lazy"
        onError={() => setImgFailed(true)}
        className="w-14 h-14 rounded-full object-cover mx-auto mb-3"
      />
    )
  }

  return (
    <div
      aria-hidden="true"
      className={`w-14 h-14 ${colorClass} rounded-full flex items-center justify-center mx-auto mb-3`}
    >
      <span className="text-lg font-bold text-white">{getInitials(name)}</span>
    </div>
  )
}

export default StaffAvatar
