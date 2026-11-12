/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, fetchApi } from '@/lib/api-client'

export default function FirstBootLanding() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [loadingDemo, setLoadingDemo] = useState(false)
  const [demoError, setDemoError] = useState<string | null>(null)

  useEffect(() => {
    fetchApi('/setup/status').then((data: any) => {
      if (!data.setup_required) navigate('/', { replace: true })
      else setLoading(false)
    }).catch(() => setLoading(false))
  }, [navigate])

  const handleLoadDemo = async () => {
    setLoadingDemo(true)
    setDemoError(null)
    try {
      await fetchApi("/setup/demo/load", { method: "POST" })
      await fetchApi("/setup/complete", { method: "POST" })
      window.location.href = '/'  // Full reload to pick up demo state
    } catch (err) {
      setLoadingDemo(false)
      const message =
        err instanceof ApiError
          ? err.userMessage || err.detail
          : "Could not load demo data."
      setDemoError(message || "Could not load demo data.")
    }
  }

  if (loading) return null

  return (
    <div className="flex min-h-screen items-center justify-center bg-earth-50 dark:bg-earth-900 p-4">
      <div className="w-full max-w-2xl space-y-6">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-earth-900 dark:text-earth-50">Welcome to L30</h1>
          <p className="mt-2 text-earth-600 dark:text-earth-400">
            Your library management system is ready to set up.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <button
            onClick={handleLoadDemo}
            disabled={loadingDemo}
            className="rounded-lg border-2 border-earth-200 dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-6 text-left shadow-sm transition hover:border-lsc-rose hover:shadow-md disabled:opacity-50"
          >
            <h2 className="text-lg font-semibold text-earth-900 dark:text-earth-50">Explore Demo</h2>
            <p className="mt-2 text-sm text-earth-600 dark:text-earth-400">
              Load sample data and explore L30 without commitment.
            </p>
            {loadingDemo && <p className="mt-2 text-sm text-lsc-rose">Loading demo data...</p>}
            {demoError && (
              <p role="alert" className="mt-2 text-sm text-red-600 dark:text-red-400">
                {demoError}
              </p>
            )}
          </button>
          <button
            onClick={() => navigate('/setup')}
            className="rounded-lg border-2 border-lsc-rose/30 bg-lsc-rose/5 dark:bg-lsc-rose/10 p-6 text-left shadow-sm transition hover:border-lsc-rose hover:shadow-md"
          >
            <h2 className="text-lg font-semibold text-earth-900 dark:text-earth-50">Set Up My Library</h2>
            <p className="mt-2 text-sm text-earth-600 dark:text-earth-400">
              Configure your library. Takes about 5 minutes.
            </p>
          </button>
        </div>
      </div>
    </div>
  )
}
