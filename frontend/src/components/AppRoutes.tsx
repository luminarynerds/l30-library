/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useTranslation} from '../i18n/I18nContext'
import ErrorBoundary from './ErrorBoundary'
import { lazyWithRetry } from '../utils/lazyWithRetry'
import Layout from './Layout'
import PlatformLayout from './PlatformLayout'
import ScrollToTop from './ScrollToTop'
import RouteAnnouncer from './RouteAnnouncer'
import { publicAuthRoutes, publicLayoutRoutes, publicPlatformShellRoutes, publicStaffShellRoutes } from '../routes/public'
import { catalogRoutes } from '../routes/catalog'
import { renderGenealogyRoutesFragment } from '../routes/genealogy'
import { legalRoutes } from '../routes/legal'
import RequireFeature from './RequireFeature'
import { NudgeProvider } from '@/contexts/NudgeContext'

// NudgeRenderer returns null until a server-pushed nudge is active, so its
// tree (NudgeToast/NudgePanel/NudgeModalLite) doesn't need to ship in the
// entry chunk. Suspense fallback is null -- same reasoning as the eager
// case rendering nothing on idle.
const NudgeRenderer = lazyWithRetry(
  () =>
    import('@/components/nudges/NudgeRenderer').then((m) => ({
      default: m.NudgeRenderer,
    })),
  'nudge-renderer',
)

const StaffRoutes = lazyWithRetry(() => import('../routes/StaffRoutes'), 'staff-routes')
const BoardRoutes = lazyWithRetry(() => import('../routes/BoardRoutes'), 'board-routes')
const IndieRoutes = lazyWithRetry(() => import('../routes/IndieRoutes'), 'indie-routes')
const LearnRoutes = lazyWithRetry(() => import('../routes/LearnRoutes'), 'learn-routes')
const SetupWizardPage = lazyWithRetry(() => import("../pages/SetupWizardPage"), 'setup-wizard-page')
const BlogListPage = lazyWithRetry(() => import("../pages/BlogListPage"), 'blog-list-page')
const PicksPage = lazyWithRetry(() => import("../pages/PicksPage"), 'picks-page')
const BlogDetailPage = lazyWithRetry(() => import("../pages/BlogDetailPage"), 'blog-detail-page')
const BlogFormPage = lazyWithRetry(() => import("../pages/BlogFormPage"), 'blog-form-page')
const StaffBlogPage = lazyWithRetry(() => import("../pages/StaffBlogPage"), 'staff-blog-page')
const FirstBootLanding = lazyWithRetry(() => import("../pages/FirstBootLanding"), 'first-boot-landing')
const InstallPage = lazyWithRetry(() => import("../pages/InstallPage"), 'install-page')
const SurveyResponsePage = lazyWithRetry(() => import("../pages/SurveyResponsePage"), 'survey-response-page')

function AdminRedirect() {
  const location = useLocation()
  const newPath = location.pathname.replace(/^\/admin/, '/staff/admin')
  return <Navigate to={newPath + location.search + location.hash} replace />
}

function RouteLoadingFallback() {
  const { t } = useTranslation()

  return (
    <div className="min-h-[50vh] px-4 py-8 max-w-5xl mx-auto" role="status" aria-label={t('aria.appRoutes.loadingPage')} aria-live="polite">
      <div className="h-8 w-64 bg-earth-200 dark:bg-earth-700 rounded-lg mb-6 motion-safe:animate-pulse" aria-hidden="true" />
      <div className="space-y-4" aria-hidden="true">
        <div className="h-4 w-full bg-earth-100 dark:bg-earth-800 rounded motion-safe:animate-pulse" />
        <div className="h-4 w-5/6 bg-earth-100 dark:bg-earth-800 rounded motion-safe:animate-pulse" />
        <div className="h-4 w-4/6 bg-earth-100 dark:bg-earth-800 rounded motion-safe:animate-pulse" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8" aria-hidden="true">
        <div className="h-40 bg-earth-100 dark:bg-earth-800 rounded-xl motion-safe:animate-pulse" />
        <div className="h-40 bg-earth-100 dark:bg-earth-800 rounded-xl motion-safe:animate-pulse" />
        <div className="h-40 bg-earth-100 dark:bg-earth-800 rounded-xl motion-safe:animate-pulse" />
      </div>
      <p className="sr-only">{t('common.loading')}</p>
    </div>
  )
}

export default function AppRoutes(): React.ReactElement {
  return (
    <ErrorBoundary>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <NudgeProvider>
        <ScrollToTop />
        <RouteAnnouncer />
        <Suspense fallback={<RouteLoadingFallback />}>
          <Routes>
            {publicAuthRoutes}

            {/* First-boot and install: run outside Layout, no auth required */}
            <Route path="/welcome" element={<FirstBootLanding />} />
            <Route path="/install" element={<InstallPage />} />

            {/* Magic-link survey response: no auth, no Layout chrome.
                Single-use token bound to a specific SurveyResponse row. */}
            <Route path="/survey/respond/:token" element={<SurveyResponsePage />} />

            {/* Setup wizard: runs outside Layout, no auth required */}
            <Route path="/setup" element={<SetupWizardPage />} />

            {/* Staff shell: full-bleed, sidebar-owned chrome (no site footer/breadcrumbs/mobile-nav). */}
            <Route element={<Layout staffShell />}>
              <Route path="staff/blog" element={<StaffBlogPage />} />
              <Route path="staff/blog/new" element={<BlogFormPage />} />
              <Route path="staff/blog/:id/edit" element={<BlogFormPage />} />
              <Route path="staff/*" element={<StaffRoutes />} />
              <Route path="admin/*" element={<AdminRedirect />} />
              <Route path="board/*" element={<RequireFeature feature="board_features_enabled"><BoardRoutes /></RequireFeature>} />
              {publicStaffShellRoutes}
            </Route>

            {/* Patron shell: site header, footer, breadcrumbs, mobile bottom nav. */}
            <Route element={<Layout />}>
              <Route path="indie/*" element={<RequireFeature feature="indie_platform_enabled"><IndieRoutes /></RequireFeature>} />
              <Route path="learn/*" element={<RequireFeature feature="learning_platform_enabled"><LearnRoutes /></RequireFeature>} />

              {catalogRoutes}

              {/* Curated picks (formerly the FanShelf on the home page) */}
              <Route path="picks" element={<PicksPage />} />

              {/* Blog */}
              <Route path="blog" element={<BlogListPage />} />
              <Route path="blog/:slug" element={<BlogDetailPage />} />
              {renderGenealogyRoutesFragment()}
              {legalRoutes}
              {publicLayoutRoutes}
            </Route>

            {/* Platform shell: minimal L30 frame for vendor/marketing pages (no patron chrome). */}
            <Route element={<PlatformLayout />}>
              {publicPlatformShellRoutes}
            </Route>
          </Routes>
        </Suspense>
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 5500,
            style: {
              background: '#2C2520',
              color: '#F9F7F4',
            },
            success: {
              duration: 4500,
            },
            error: {
              duration: 7000,
            },
            ariaProps: {
              role: 'status',
              'aria-live': 'polite',
            },
          }}
        />
        <Suspense fallback={null}>
          <NudgeRenderer />
        </Suspense>
        </NudgeProvider>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
