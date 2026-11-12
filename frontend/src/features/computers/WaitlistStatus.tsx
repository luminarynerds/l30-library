/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/card'
import api from '@/lib/api-client'
import { logger } from '@/utils/logger'
import { API_BASE } from '@/api/types'

export function WaitlistStatus() {
  const [position, setPosition] = useState<{ queue_position: number; computer_id: number; status: string } | null>(null)

  useEffect(() => {
    api.get(`${API_BASE}/computers/waitlist/position`)
      .then(setPosition)
      .catch((error) => {
        logger.error('Failed to fetch waitlist position:', error)
        setPosition(null)
      })
  }, [])

  if (!position) return null

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Waitlist Status</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-center">
          <div className="text-4xl font-bold text-lsc-rose dark:text-lsc-rose-light mb-2">#{position.queue_position}</div>
          <div className="text-lsc-dark/70 dark:text-lsc-cream/70">Your position in the queue</div>
          <div className="text-sm text-earth-600 dark:text-earth-400 mt-1">Computer #{position.computer_id}</div>
        </div>
      </CardContent>
    </Card>
  )
}