/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Admin dashboard for library data migration management.
 *
 * Shows past migration jobs and allows starting new migrations.
 */
import { useEffect, useState } from 'react'
import { Download, Plus, RefreshCw } from 'lucide-react'
import { AdminShell } from '../components/shells/AdminShell';
import { migrationApi, type MigrationHistoryResponse } from '../api/migration-api'
import { t } from '@/i18n'

export default function AdminMigrationWizardPage() {
  const [history, setHistory] = useState<MigrationHistoryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadHistory = async () => {
    try {
      setLoading(true)
      const data = await migrationApi.getHistory(50, 0)
      setHistory(data)
      setError(null)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load migration history')
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    loadHistory()
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-status-success-100 dark:bg-status-success-900 text-status-success-800 dark:text-status-success-200'
      case 'failed':
        return 'bg-status-danger-100 dark:bg-status-danger-900 text-status-danger-800 dark:text-status-danger-200'
      case 'rolled_back':
        return 'bg-status-warning-100 dark:bg-status-warning-900 text-status-warning-800 dark:text-status-warning-200'
      case 'running':
      case 'executing':
        return 'bg-earth-100 dark:bg-earth-800 text-earth-800 dark:text-lsc-rose-light/80'
      default:
        return 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream'
    }
  }

  return (
    <AdminShell title="Data Migration" subtitle="Import data from Sirsi, Koha, or CSV sources">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div></div>
          <button
            onClick={() => (window.location.href = '/onboarding/migration')}
            className="bg-lsc-rose text-white px-6 py-2 rounded-lg hover:bg-status-warning-600 flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            Start New Migration
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="bg-status-danger-50 dark:bg-status-danger-900 border border-status-danger-200 dark:border-status-danger-700 p-4 rounded-lg">
            <p className="text-status-danger-800 dark:text-status-danger-200">Error: {error}</p>
          </div>
        )}

        {/* Migration History */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow">
          <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex justify-between items-center">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Migration History</h3>
            <button
              onClick={loadHistory}
              disabled={loading}
              aria-label={t('aria.adminMigrationWizard.refreshHistory', 'Refresh migration history')}
              className="text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-white disabled:opacity-50"
            >
              <RefreshCw className={`w-5 h-5 ${loading ? 'motion-safe:animate-spin' : ''}`} />
            </button>
          </div>

          {loading ? (
            <div className="p-6 text-center">
              <RefreshCw className="w-8 h-8 motion-safe:animate-spin text-lsc-rose mx-auto" />
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">Loading migration history...</p>
            </div>
          ) : !history || history.items.length === 0 ? (
            <div className="p-6 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
              No migrations yet. Start your first migration to get started!
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-lsc-cream dark:bg-earth-700 border-b border-lsc-border dark:border-earth-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      Filename
                    </th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      Source System
                    </th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      Rows
                    </th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      Date
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                  {history.items.map((item) => (
                    <tr key={item.id} className="hover:bg-lsc-cream dark:hover:bg-earth-700">
                      <td className="px-6 py-4">
                        <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate" title={item.original_filename}>
                          {item.original_filename}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">
                          {item.source_system}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(item.status)}`}>
                          {item.status}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          <span className="text-status-success-600 dark:text-status-success-400 font-medium">{item.processed_rows}</span>
                          {item.failed_rows > 0 && (
                            <>
                              {' '}
                              / <span className="text-status-danger-600 dark:text-status-danger-400">{item.failed_rows} failed</span>
                            </>
                          )}
                          <br />
                          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">of {item.total_rows} total</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {new Date(item.created_at).toLocaleDateString()}
                        <br />
                        <span className="text-xs">
                          {new Date(item.created_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* CSV Templates */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow">
          <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">CSV Templates</h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              Download a template to format your data before importing. Fill in the columns, save as CSV, then upload using the migration wizard.
            </p>
          </div>
          <div className="p-6 grid gap-4 sm:grid-cols-2">
            <TemplateCard
              title="Catalog Items"
              description="Books, DVDs, audiobooks, and other collection items"
              requiredFields={['title']}
              optionalFields={['author', 'isbn', 'publisher', 'publication_year', 'item_type', 'call_number', 'dewey_decimal', 'lc_classification', 'edition', 'series_name', 'series_number', 'subjects', 'description']}
              sampleRow={{
                title: 'The Great Gatsby',
                author: 'F. Scott Fitzgerald',
                isbn: '9780743273565',
                publisher: 'Scribner',
                publication_year: '1925',
                item_type: 'book',
                call_number: '813.52 FIT',
                subjects: 'American fiction; Jazz Age',
              }}
              fieldNotes={{
                item_type: 'book, audiobook, ebook, dvd, bluray, cd, vinyl, magazine, game, equipment, kit, other',
                publication_year: 'Four-digit year, e.g. 2024',
                subjects: 'Semicolon-separated list',
              }}
            />
            <TemplateCard
              title="Patrons"
              description="Library cardholders and their contact information"
              requiredFields={['name', 'email']}
              optionalFields={['barcode', 'phone', 'address', 'patron_type', 'home_branch', 'first_name', 'last_name', 'library_card']}
              sampleRow={{
                name: 'Jane Smith',
                email: 'jane.smith@example.com',
                barcode: 'P00012345',
                phone: '555-0100',
                patron_type: 'adult',
              }}
              fieldNotes={{
                patron_type: 'patron, child, staff, admin, bookmobile, homebond',
                name: 'Full name; or use first_name + last_name instead',
              }}
            />
            <TemplateCard
              title="Holdings / Item Copies"
              description="Physical copies tied to catalog records"
              requiredFields={['item_barcode', 'catalog_id']}
              optionalFields={['branch', 'call_number', 'condition', 'status', 'copy_number', 'location', 'replacement_cost', 'acquisition_source']}
              sampleRow={{
                item_barcode: 'I000098765',
                catalog_id: '1',
                branch: 'Main',
                call_number: '813.52 FIT',
                condition: 'good',
                status: 'available',
                copy_number: '1',
              }}
              fieldNotes={{
                status: 'available, checked_out, on_hold, in_transit, on_order, in_processing, missing, lost, damaged, withdrawn',
                catalog_id: 'Numeric ID of the catalog record this copy belongs to',
              }}
            />
            <TemplateCard
              title="Circulation History"
              description="Past checkouts for reporting and analytics"
              requiredFields={['patron_barcode', 'item_barcode', 'checkout_date']}
              optionalFields={['return_date']}
              sampleRow={{
                patron_barcode: 'P00012345',
                item_barcode: 'I000098765',
                checkout_date: '2025-01-15',
                return_date: '2025-02-01',
              }}
              fieldNotes={{
                checkout_date: 'YYYY-MM-DD format',
                return_date: 'YYYY-MM-DD format; leave blank for active checkouts',
              }}
            />
          </div>
        </div>

        {/* Info Section */}
        <div className="bg-earth-50 dark:bg-earth-900 border border-lsc-border dark:border-earth-600 rounded-lg p-6">
          <h3 className="font-serif font-semibold text-earth-900 dark:text-earth-200 mb-3">About Data Migrations</h3>
          <ul className="text-sm text-earth-800 dark:text-lsc-rose-light/80 space-y-2">
            <li>✓ Supported sources: Sirsi/Symphony, Koha, and generic CSV files</li>
            <li>✓ All migrations are validated before execution with a dry-run preview</li>
            <li>✓ Migrations can be rolled back within 24 hours of completion</li>
            <li>✓ Field mapping is automatically detected and can be customized</li>
          </ul>
        </div>
      </div>
    </AdminShell>
  )
}


// ── Template Card Component ────────────────────────────────────────────

interface TemplateCardProps {
  title: string
  description: string
  requiredFields: string[]
  optionalFields: string[]
  sampleRow: Record<string, string>
  fieldNotes?: Record<string, string>
}

function TemplateCard({ title, description, requiredFields, optionalFields, sampleRow, fieldNotes }: TemplateCardProps) {
  const allFields = [...requiredFields, ...optionalFields]

  const downloadTemplate = () => {
    const header = allFields.join(',')
    const sample = allFields.map((f) => sampleRow[f] || '').join(',')
    const csv = header + '\n' + sample + '\n'
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${title.toLowerCase().replace(/[\s/]+/g, '_')}_template.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="border border-lsc-border dark:border-earth-700 rounded-lg p-4 flex flex-col">
      <h4 className="font-semibold text-lsc-dark dark:text-lsc-cream">{title}</h4>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{description}</p>
      <div className="mt-3 space-y-2 flex-1">
        <div>
          <span className="text-xs font-medium text-lsc-dark/70 dark:text-earth-400 uppercase tracking-wide">Required</span>
          <div className="flex flex-wrap gap-1 mt-1">
            {requiredFields.map((f) => (
              <span key={f} className="px-2 py-0.5 text-xs rounded bg-status-warning-100 dark:bg-status-warning-900 text-status-warning-800 dark:text-status-warning-300 font-mono">
                {f}
              </span>
            ))}
          </div>
        </div>
        <div>
          <span className="text-xs font-medium text-lsc-dark/70 dark:text-earth-400 uppercase tracking-wide">Optional</span>
          <div className="flex flex-wrap gap-1 mt-1">
            {optionalFields.map((f) => (
              <span key={f} className="px-2 py-0.5 text-xs rounded bg-earth-100 dark:bg-earth-700 text-earth-700 dark:text-earth-300 font-mono">
                {f}
              </span>
            ))}
          </div>
        </div>
      </div>
      {fieldNotes && Object.keys(fieldNotes).length > 0 && (
        <div className="mt-3 border-t border-lsc-border dark:border-earth-700 pt-3">
          <span className="text-xs font-medium text-lsc-dark/70 dark:text-earth-400 uppercase tracking-wide">Accepted Values</span>
          <dl className="mt-1 space-y-1">
            {Object.entries(fieldNotes).map(([field, note]) => (
              <div key={field} className="text-xs">
                <dt className="inline font-mono font-medium text-lsc-dark dark:text-lsc-cream">{field}: </dt>
                <dd className="inline text-lsc-dark/70 dark:text-earth-400">{note}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}
      <button
        onClick={downloadTemplate}
        className="mt-4 flex items-center justify-center gap-2 w-full px-4 py-2 text-sm border border-lsc-border dark:border-earth-600 rounded-lg text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 transition"
      >
        <Download className="w-4 h-4" />
        Download Template
      </button>
    </div>
  )
}
