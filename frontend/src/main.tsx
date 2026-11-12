/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import ReactDOM from 'react-dom/client'
import * as Sentry from "@/lib/sentry-lazy"
import App from './App'
import './index.css'
import '@fontsource/cormorant-garamond/500.css'
import '@fontsource/cormorant-garamond/600.css'
import '@fontsource/cormorant-garamond/700.css'
import { getInitialLanguage, loadLanguage } from './i18n/translations'
import { shouldReloadAfterChunkError } from './utils/lazyWithRetry'

if (import.meta.env.VITE_SENTRY_DSN) {
  Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN,
    environment: import.meta.env.MODE || 'development',
    tracesSampleRate: import.meta.env.MODE === 'production' ? 0.1 : 1.0,
  })
}

// Auto-recover from stale dynamic-import chunks after a deploy. The user's
// open tab still references old content-hashed chunk URLs that now 404.
// Reload to pick up the fresh shell, but suppress the reload if we just did
// one (the chunk is genuinely missing, not merely stale) to avoid a loop.
// A later deploy in the same session falls outside that window and recovers.
// See: https://luminary-nerds.sentry.io/issues/L30-LIBRARY-2K
const VITE_PRELOAD_RELOAD_KEY = '__l30_vite_preload_reload_ts__'
window.addEventListener('vite:preloadError', (event) => {
  const e = event as Event & { payload?: unknown }
  if (!shouldReloadAfterChunkError(sessionStorage, VITE_PRELOAD_RELOAD_KEY)) {
    Sentry.captureException(e.payload ?? new Error('vite preloadError after reload'), {
      tags: { trap: 'vite_preload_after_reload' },
    })
    return
  }
  window.location.reload()
})

const root = document.getElementById('root')

if (!root) {
  throw new Error('Root element not found')
}

// Await the initial locale before mounting so the index.html skeleton
// stays visible during the brief fetch instead of a blank flicker.
// English is always loaded (used as fallback for missing keys in other locales).
const initialLang = getInitialLanguage()
const loaders = initialLang === 'en'
  ? [loadLanguage('en')]
  : [loadLanguage('en'), loadLanguage(initialLang)]

void Promise.all(loaders).finally(() => {
  ReactDOM.createRoot(root).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  )
})
