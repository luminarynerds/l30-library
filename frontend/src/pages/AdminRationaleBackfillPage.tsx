/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from '@/i18n'
import { listMissingRationale } from '@/api/acquisitionRationale'

export default function AdminRationaleBackfillPage(): React.ReactElement {
  const { t } = useTranslation()
  const [ids, setIds] = useState<number[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listMissingRationale(200)
      .then(setIds)
      .catch((e: unknown) => {
        const message = e instanceof Error ? e.message : String(e)
        setError(message)
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <main>
      <h1>{t('acquisitionRationale.backfillTitle')}</h1>
      <p>{t('acquisitionRationale.itemsMissing', { count: ids.length })}</p>
      {loading && <p>{t('acquisitionRationale.saving')}</p>}
      {error && <p role="alert">{error}</p>}
      <ul>
        {ids.map((id) => (
          <li key={id}>
            <Link to={`/staff/cataloging?edit=${id}&openRationale=1`}>
              {t('acquisitionRationale.itemLink', { id })}
            </Link>
          </li>
        ))}
      </ul>
    </main>
  )
}
