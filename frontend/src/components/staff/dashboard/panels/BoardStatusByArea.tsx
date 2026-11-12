/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useTone } from '@/contexts/ToneContext'
import { getBoardStatus, StatusArea } from '@/api/staff-api/board-dashboard'
import { Users, Briefcase, FileText } from 'lucide-react'

const AREA_ICONS: Record<string, React.ReactNode> = {
  'users-group': <Users className="w-4 h-4" aria-hidden="true" />,
  'briefcase': <Briefcase className="w-4 h-4" aria-hidden="true" />,
  'file-text': <FileText className="w-4 h-4" aria-hidden="true" />,
}

export default function BoardStatusByArea() {
  const { token } = useAuth()
  const { showUrgencyColors } = useTone()
  const [areas, setAreas] = useState<StatusArea[]>([])

  useEffect(() => {
    if (!token) return
    getBoardStatus(token).then(r => setAreas(r.areas)).catch(() => {})
  }, [token])

  if (areas.length === 0) return null

  return (
    <div>
      <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 mb-2">Status by area</p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {areas.map(area => (
          <div key={area.title} className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4">
            <div className="flex items-center gap-2 mb-3">
              {AREA_ICONS[area.icon] ?? <FileText className="w-4 h-4" aria-hidden="true" />}
              <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{area.title}</p>
            </div>
            <div className="space-y-1.5">
              {area.entries.map(entry => (
                <div key={entry.label} className="flex justify-between text-xs">
                  <span className="text-lsc-dark/60 dark:text-lsc-cream/60">{entry.label}</span>
                  <span className={showUrgencyColors && entry.warning ? 'text-status-warning-600 dark:text-status-warning-400 font-medium' : 'text-lsc-dark dark:text-lsc-cream'}>
                    {entry.value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
