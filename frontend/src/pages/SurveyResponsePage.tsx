/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  getSurveyByToken,
  submitSurveyByToken,
  type Survey,
} from '@/api/domains/engagement'
import { SurveyRenderer } from '@/components/engagement/SurveyRenderer'

export default function SurveyResponsePage() {
  const { token = '' } = useParams<{ token: string }>()
  const [survey, setSurvey] = useState<Survey | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [errorStatus, setErrorStatus] = useState<number | null>(null)

  useEffect(() => {
    if (!token) {
      setError('Missing link')
      return
    }
    getSurveyByToken(token)
      .then((s) => setSurvey(s))
      .catch((e: Error & { status?: number }) => {
        setError(e.message || 'Failed to load survey')
        setErrorStatus(e.status ?? null)
      })
  }, [token])

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900 px-4 py-10">
      <div className="max-w-2xl mx-auto">
        {error ? (
          <ErrorPanel status={errorStatus} message={error} />
        ) : !survey ? (
          <LoadingPanel />
        ) : (
          <SurveyRenderer
            survey={survey}
            onSubmit={(answers) => submitSurveyByToken(token, answers)}
          />
        )}
      </div>
    </div>
  )
}

function ErrorPanel({
  status,
  message,
}: {
  status: number | null
  message: string
}) {
  const headline =
    status === 410
      ? 'This survey link has expired'
      : status === 409
      ? 'This survey was already submitted'
      : status === 404
      ? 'This link is no longer valid'
      : 'Something went wrong'
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg border border-lsc-border dark:border-earth-700 p-8 text-center">
      <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
        {headline}
      </h1>
      <p className="mt-2 text-lsc-dark/70 dark:text-lsc-cream/70">{message}</p>
      <p className="mt-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        If you'd like to share feedback another way, please contact your
        library.
      </p>
    </div>
  )
}

function LoadingPanel() {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg border border-lsc-border dark:border-earth-700 p-12 flex items-center justify-center">
      <span className="motion-safe:animate-spin h-6 w-6 border-2 border-lsc-rose/40 border-t-lsc-rose rounded-full" />
    </div>
  )
}
