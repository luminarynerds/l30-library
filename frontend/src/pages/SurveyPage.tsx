/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  getSurvey,
  submitSurveyResponse,
  type Survey,
} from '@/api/domains/engagement'
import { SurveyRenderer } from '@/components/engagement/SurveyRenderer'
import PageContainer from '@/components/layout/PageContainer'

export default function SurveyPage() {
  const { id } = useParams<{ id: string }>()
  const surveyId = id ? Number(id) : NaN
  const [survey, setSurvey] = useState<Survey | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!Number.isFinite(surveyId)) {
      setError('Invalid survey id')
      return
    }
    getSurvey(surveyId)
      .then(setSurvey)
      .catch((e: Error) => setError(e.message || 'Failed to load survey'))
  }, [surveyId])

  return (
    <PageContainer width="form" className="py-8">
      {error ? (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow border border-lsc-border dark:border-earth-700 p-6">
          <h1 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            Survey unavailable
          </h1>
          <p className="mt-2 text-lsc-dark/70 dark:text-lsc-cream/70">
            {error}
          </p>
        </div>
      ) : !survey ? (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow border border-lsc-border dark:border-earth-700 p-12 flex items-center justify-center">
          <span className="motion-safe:animate-spin h-6 w-6 border-2 border-lsc-rose/40 border-t-lsc-rose rounded-full" />
        </div>
      ) : (
        <SurveyRenderer
          survey={survey}
          onSubmit={(answers) => submitSurveyResponse(surveyId, answers)}
        />
      )}
    </PageContainer>
  )
}
