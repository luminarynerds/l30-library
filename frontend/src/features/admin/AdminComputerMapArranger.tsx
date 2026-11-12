/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getAdminComputers,
  updateAdminComputer,
  type AdminComputer,
} from '@/api/domains/admin/admin-computers-api'
import { useTranslation } from '@/i18n/I18nContext'

function clamp(v: number): number {
  return Math.min(1, Math.max(0, v))
}

export default function AdminComputerMapArranger(): React.ReactElement {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['admin-computers'], queryFn: getAdminComputers })
  const [draggingId, setDraggingId] = useState<number | null>(null)

  const items: AdminComputer[] = data?.items ?? []
  const placed = items.filter(c => c.map_x != null && c.map_y != null)
  const tray = items.filter(c => c.map_x == null || c.map_y == null)

  const onDragStart = (e: React.DragEvent<HTMLButtonElement>, id: number) => {
    e.dataTransfer.setData('text/plain', String(id))
    setDraggingId(id)
  }

  const onDropCanvas = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    const id = Number(e.dataTransfer.getData('text/plain') || draggingId)
    if (!id) return
    const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect()
    const x = clamp((e.clientX - rect.left) / rect.width)
    const y = clamp((e.clientY - rect.top) / rect.height)
    void updateAdminComputer(id, { map_x: x, map_y: y }).then(() => {
      qc.invalidateQueries({ queryKey: ['admin-computers'] })
    })
    setDraggingId(null)
  }

  return (
    <div className="space-y-4">
      <h3 className="font-serif text-xl">{t('admin.computerMap.title')}</h3>
      <p className="text-sm text-earth-600">{t('admin.computerMap.help')}</p>
      <div
        data-testid="arranger-canvas"
        onDragOver={e => { e.preventDefault(); e.dataTransfer.dropEffect = 'move' }}
        onDrop={onDropCanvas}
        className="relative w-full aspect-[2/1] rounded border-2 border-dashed border-earth-300 bg-earth-50"
      >
        {placed.map(c => (
          <button
            key={c.id}
            type="button"
            draggable
            onDragStart={e => onDragStart(e, c.id)}
            style={{ left: `${(c.map_x ?? 0) * 100}%`, top: `${(c.map_y ?? 0) * 100}%` }}
            className="absolute -translate-x-1/2 -translate-y-1/2 px-2 py-1 text-xs rounded bg-sage-200 hover:bg-sage-300"
          >
            {c.computer_number}
          </button>
        ))}
      </div>
      <div data-testid="tray" className="flex flex-wrap gap-2 p-3 rounded border border-earth-200">
        {tray.length === 0 && <span className="text-xs text-earth-600">{t('admin.computerMap.trayEmpty')}</span>}
        {tray.map(c => (
          <button
            key={c.id}
            type="button"
            draggable
            onDragStart={e => onDragStart(e, c.id)}
            className="px-2 py-1 text-xs rounded bg-earth-100 hover:bg-earth-200"
          >
            {c.computer_number}
          </button>
        ))}
      </div>
    </div>
  )
}
