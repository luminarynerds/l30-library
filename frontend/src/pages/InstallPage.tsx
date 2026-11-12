import PageContainer from '@/components/layout/PageContainer'

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export default function InstallPage() {
  return (
    <div className="min-h-screen bg-lsc-white dark:bg-earth-900">
      <PageContainer className="py-12">
        <h1 className="text-3xl font-bold text-earth-900 dark:text-earth-50">Install L30</h1>
        <p className="mt-2 text-earth-600 dark:text-earth-400">
          L30 runs anywhere Docker runs. One command to start.
        </p>

        <section className="mt-8 space-y-4">
          <h2 className="text-xl font-semibold text-earth-900 dark:text-earth-50">Requirements</h2>
          <ul className="list-disc pl-5 space-y-1 text-earth-700 dark:text-earth-300">
            <li>Docker Engine 24+ and Docker Compose v2</li>
            <li>2 GB RAM minimum (4 GB recommended)</li>
            <li>10 GB disk space</li>
            <li>Linux, macOS, or Windows with WSL2</li>
          </ul>
        </section>

        <section className="mt-8 space-y-4">
          <h2 className="text-xl font-semibold text-earth-900 dark:text-earth-50">Quick Start</h2>
          <div className="rounded-lg bg-earth-900 dark:bg-earth-950 p-4 text-sm font-mono text-status-success-400 overflow-x-auto">
            <p className="text-earth-600">{'# Download and start'}</p>
            <p>git clone https://github.com/luminarynerds/l30-dist.git my-library</p>
            <p>cd my-library</p>
            <p>cp .env.example .env</p>
            <p>docker compose up -d</p>
            <p className="mt-2 text-earth-600">{'# Open http://localhost in your browser'}</p>
          </div>
        </section>

        <section className="mt-8 space-y-4">
          <h2 className="text-xl font-semibold text-earth-900 dark:text-earth-50">Production Deploy</h2>
          <p className="text-earth-700 dark:text-earth-300">Edit .env with your domain for automatic SSL:</p>
          <div className="rounded-lg bg-earth-900 dark:bg-earth-950 p-4 text-sm font-mono text-status-success-400 overflow-x-auto">
            <p>DOMAIN=library.yourtown.org</p>
            <p>ADMIN_EMAIL=admin@yourtown.org</p>
            <p className="mt-2 text-earth-600">{'# Make sure DNS points to your server, then:'}</p>
            <p>docker compose up -d</p>
          </div>
        </section>

        <section className="mt-8 space-y-4">
          <h2 className="text-xl font-semibold text-earth-900 dark:text-earth-50">Updates</h2>
          <div className="rounded-lg bg-earth-900 dark:bg-earth-950 p-4 text-sm font-mono text-status-success-400 overflow-x-auto">
            <p>docker compose pull</p>
            <p>docker compose up -d</p>
          </div>
        </section>

        <section className="mt-8 space-y-4">
          <h2 className="text-xl font-semibold text-earth-900 dark:text-earth-50">Backup</h2>
          <div className="rounded-lg bg-earth-900 dark:bg-earth-950 p-4 text-sm font-mono text-status-success-400 overflow-x-auto">
            <p className="text-earth-600">{'# Database backup'}</p>
            <p>{'docker compose exec database pg_dump -U l30 l30 > backup.sql'}</p>
            <p className="mt-2 text-earth-600">{'# Restore'}</p>
            <p>{'docker compose exec -T database psql -U l30 l30 < backup.sql'}</p>
          </div>
        </section>
      </PageContainer>
    </div>
  )
}
