/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useNudges } from '@/contexts/NudgeContext'
import { NudgeToast } from './NudgeToast'
import { NudgePanel } from './NudgePanel'
import { NudgeModalLite } from './NudgeModalLite'

export function NudgeRenderer() {
  const { activeNudges } = useNudges()

  const globalNudges = activeNudges.filter(
    n => n.delivery_placement === 'global' || ['toast', 'panel', 'modal_lite'].includes(n.delivery_type)
  )

  const modalNudge = globalNudges.find(n => n.delivery_type === 'modal_lite')
  const panelNudge = globalNudges.find(n => n.delivery_type === 'panel')
  const toastNudge = globalNudges.find(n => n.delivery_type === 'toast')

  if (modalNudge) return <NudgeModalLite nudge={modalNudge} />

  return (
    <>
      {panelNudge && <NudgePanel nudge={panelNudge} />}
      {toastNudge && <NudgeToast nudge={toastNudge} />}
    </>
  )
}
