/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { useTranslation } from '@/i18n'
import { parseLexileClient } from '../utils/lexile'

interface Props { raw: string | null | undefined }

export function LexileParsePreview({ raw }: Props): JSX.Element | null {
  const { t } = useTranslation()
  const [state, setState] = useState<{ ok: boolean; numeric: number | null }>({ ok: true, numeric: null })
  useEffect(() => {
    if (!raw || raw.trim() === '') { setState({ ok: true, numeric: null }); return }
    try {
      const { numeric } = parseLexileClient(raw)
      setState({ ok: true, numeric })
    } catch {
      setState({ ok: false, numeric: null })
    }
  }, [raw])
  if (!raw || raw.trim() === '') return null
  if (!state.ok) {
    return <p id="lexile-hint" className="mt-1 text-sm text-red-600">{t('staff_form_lexile_invalid')}</p>
  }
  return <p id="lexile-hint" className="mt-1 text-sm text-earth-600">{t('staff_form_lexile_hint', { numeric: state.numeric ?? '—' })}</p>
}
