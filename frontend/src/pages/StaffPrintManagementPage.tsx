/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { AdminShell } from '../components/shells/AdminShell'
import {
  Printer,
  Loader2,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  ListOrdered,
  Clock,
  FileText,
  Plus,
  X,
} from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../api/api'
import { useTranslation, getCurrentLocale } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface PrinterData {
  id: number
  name: string
  location: string
  status: string
  black_toner_level?: number
  paper_level?: number
}

interface PrinterAlert {
  id: number
  printer_name: string
  printer_location: string
  alert_type: string
  severity: string
  message: string
}

interface PrintJob {
  id: number
  job_name: string
  pages: number
  status: string
  submitted_at: string
}

type TabId = 'printers' | 'queue'

export default function StaffPrintManagementPage() {
  const { t } = useTranslation()
  const { user, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()
  const [printers, setPrinters] = useState<PrinterData[]>([])
  const [alerts, setAlerts] = useState<PrinterAlert[]>([])
  const [queue, setQueue] = useState<PrintJob[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<TabId>('printers')
  const [showAddPrinter, setShowAddPrinter] = useState(false)
  const [addingPrinter, setAddingPrinter] = useState(false)
  const [printerForm, setPrinterForm] = useState({
    name: '', printer_type: 'laser', location: '', model: '', ipp_endpoint: '',
  })

  const handleAddPrinter = async (e: React.FormEvent) => {
    e.preventDefault()
    setAddingPrinter(true)
    try {
      const fd = new FormData()
      fd.append('name', printerForm.name)
      fd.append('printer_type', printerForm.printer_type)
      fd.append('location', printerForm.location)
      if (printerForm.model) fd.append('model', printerForm.model)
      if (printerForm.ipp_endpoint) fd.append('ipp_endpoint', printerForm.ipp_endpoint)
      await api.post('/print/printers', fd)
      toast.success('Printer added')
      setShowAddPrinter(false)
      setPrinterForm({ name: '', printer_type: 'laser', location: '', model: '', ipp_endpoint: '' })
      fetchData()
    } catch {
      toast.error('Failed to add printer')
    } finally {
      setAddingPrinter(false)
    }
  }

  useEffect(() => {
    if (!authLoading && (!user || user.role === 'patron')) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
      navigate('/account')
    }
  }, [authLoading, user, navigate, t])

  const fetchData = async () => {
    try {
      const [printersRes, alertsRes, queueRes] = await Promise.all([
        api.get('/print/printers'),
        api.get('/print/alerts'),
        api.get('/print/queue'),
      ])

      setPrinters(printersRes.data)
      setAlerts(alertsRes.data)
      setQueue(queueRes.data.jobs || [])
    } catch {
      // Data may not be available
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (user && user.role !== 'patron') {
      fetchData()
      const interval = setInterval(fetchData, 30000)
      return () => clearInterval(interval)
    }
  }, [user])

  const handleResolveAlert = async (alertId: number) => {
    try {
      await api.post(`/print/alerts/${alertId}/resolve`)
      setAlerts((prev) => prev.filter((a) => a.id !== alertId))
      toast.success(t('toast.adminLinkHealth.alertResolved'))
    } catch {
      toast.error(t('staffPrintManagement.failedToResolveAlert'))
    }
  }

  const tabs: { id: TabId; label: string; icon: React.ReactNode; count: number }[] = [
    { id: 'printers', label: 'Printers', icon: <Printer className="w-4 h-4" />, count: printers.length },
    { id: 'queue', label: 'Print Queue', icon: <ListOrdered className="w-4 h-4" />, count: queue.length },
  ]

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
      </div>
    )
  }

  if (!user || user.role === 'patron') return <></>

  const onlinePrinters = printers.filter((p) => p.status === 'online').length

  return (
    <AdminShell title="Print Management">
      <div>
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-lsc-cream dark:bg-earth-800/30 rounded-xl">
                <Printer className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
              </div>
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                Print Management
              </h1>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowAddPrinter(true)}
                className="flex items-center gap-2 px-4 py-2 text-sm bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg transition-colors"
              >
                <Plus className="w-4 h-4" /> Add Printer
              </button>
              <button
                onClick={() => { setLoading(true); fetchData() }}
                className="flex items-center gap-2 px-4 py-2 text-sm bg-lsc-cream dark:bg-earth-800 hover:bg-lsc-border dark:hover:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg transition-colors"
              >
                <RefreshCw className="w-4 h-4" /> Refresh
              </button>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">Total Printers</p>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{printers.length}</p>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">Online</p>
              <p className="text-2xl font-bold text-status-success-700 dark:text-status-success-400">{onlinePrinters}</p>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">Queue</p>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{queue.length}</p>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">Active Alerts</p>
              <p className={`text-2xl font-bold ${alerts.length > 0 ? 'text-status-danger-600 dark:text-status-danger-400' : 'text-lsc-dark dark:text-lsc-cream'}`}>
                {alerts.length}
              </p>
            </div>
          </div>

          {/* Alerts */}
          {alerts.length > 0 && (
            <div className="bg-status-danger-50 dark:bg-status-danger-900/10 rounded-xl p-4 border border-status-danger-200 dark:border-status-danger-900/30">
              <h2 className="text-sm font-semibold text-status-danger-800 dark:text-status-danger-300 mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                Active Alerts ({alerts.length})
              </h2>
              <div className="space-y-2">
                {alerts.map((alert) => (
                  <div
                    key={alert.id}
                    className="flex items-center justify-between bg-lsc-white dark:bg-earth-800 p-3 rounded-lg border border-lsc-border dark:border-earth-700"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-lsc-dark dark:text-lsc-cream text-sm">{alert.printer_name}</p>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{alert.message}</p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50 mt-0.5">{alert.printer_location}</p>
                    </div>
                    <button
                      onClick={() => handleResolveAlert(alert.id)}
                      className="shrink-0 ml-3 flex items-center gap-1 px-3 py-1.5 bg-status-success-600 hover:bg-status-success-700 text-white rounded-lg text-sm transition-colors"
                    >
                      <CheckCircle className="w-3.5 h-3.5" />
                      Resolve
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tabs */}
          <div className="border-b border-lsc-border dark:border-earth-700">
            <nav className="flex gap-4 overflow-x-auto">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 pb-3 px-1 border-b-2 transition-colors whitespace-nowrap ${
                    activeTab === tab.id
                      ? 'border-lsc-rose text-lsc-rose dark:text-lsc-rose-light'
                      : 'border-transparent text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream'
                  }`}
                >
                  {tab.icon}
                  <span className="font-medium">{tab.label}</span>
                  <span className="text-xs bg-lsc-cream dark:bg-earth-700 px-1.5 py-0.5 rounded-full">
                    {tab.count}
                  </span>
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content */}
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
            </div>
          ) : (
            <>
              {/* Printers Tab */}
              {activeTab === 'printers' && (
                <div>
                  {printers.length === 0 ? (
                    <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
                      <Printer className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p>No printers configured</p>
                    </div>
                  ) : (
                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {printers.map((printer) => (
                        <div
                          key={printer.id}
                          className={`bg-lsc-white dark:bg-earth-800 rounded-xl p-5 border ${
                            printer.status === 'online'
                              ? 'border-lsc-border dark:border-earth-700'
                              : 'border-status-danger-200 dark:border-status-danger-900/50'
                          }`}
                        >
                          <div className="flex justify-between items-start mb-4">
                            <div>
                              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{printer.name}</h3>
                              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">{printer.location}</p>
                            </div>
                            <span
                              className={`px-2 py-0.5 rounded text-xs font-medium ${
                                printer.status === 'online'
                                  ? 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400'
                                  : 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400'
                              }`}
                            >
                              {printer.status.toUpperCase()}
                            </span>
                          </div>

                          <div className="space-y-3">
                            {printer.black_toner_level !== undefined && (
                              <div>
                                <div className="flex justify-between text-xs mb-1 text-lsc-dark/70 dark:text-lsc-cream/70">
                                  <span>Black Toner</span>
                                  <span className="font-medium">{printer.black_toner_level}%</span>
                                </div>
                                <div className="w-full bg-lsc-cream dark:bg-earth-600 rounded-full h-2">
                                  <div
                                    className={`h-2 rounded-full transition-all ${
                                      printer.black_toner_level > 20 ? 'bg-lsc-dark dark:bg-lsc-cream' : 'bg-status-danger-500'
                                    }`}
                                    style={{ width: `${printer.black_toner_level}%` }}
                                  />
                                </div>
                              </div>
                            )}

                            {printer.paper_level !== undefined && (
                              <div>
                                <div className="flex justify-between text-xs mb-1 text-lsc-dark/70 dark:text-lsc-cream/70">
                                  <span>Paper Level</span>
                                  <span className="font-medium">{printer.paper_level}%</span>
                                </div>
                                <div className="w-full bg-lsc-cream dark:bg-earth-600 rounded-full h-2">
                                  <div
                                    className={`h-2 rounded-full transition-all ${
                                      printer.paper_level > 15 ? 'bg-lsc-rose' : 'bg-status-warning-500'
                                    }`}
                                    style={{ width: `${printer.paper_level}%` }}
                                  />
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Queue Tab */}
              {activeTab === 'queue' && (
                <div>
                  {queue.length === 0 ? (
                    <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
                      <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p>{t('staffPrintManagement.noJobsInQueue')}</p>
                    </div>
                  ) : (
                    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
                      <table className="w-full">
                        <thead className="bg-lsc-cream/50 dark:bg-earth-700/50 border-b border-lsc-border dark:border-earth-700">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">Job Name</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">Pages</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">Status</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">Submitted</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                          {queue.map((job) => (
                            <tr key={job.id} className="hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30 transition-colors">
                              <td className="px-4 py-3 text-sm text-lsc-dark dark:text-lsc-cream font-medium">{job.job_name}</td>
                              <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{job.pages}</td>
                              <td className="px-4 py-3 text-sm">
                                <span className="px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded text-xs font-medium capitalize">
                                  {job.status}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/60 flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {new Date(job.submitted_at).toLocaleTimeString(getCurrentLocale(), {
                                  hour: 'numeric',
                                  minute: '2-digit',
                                })}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
      </div>
                  )}
      </div>
              )}
            </>
          )}
        {/* Add Printer Modal */}
        {showAddPrinter && (
          <ModalBackdrop onClose={() => setShowAddPrinter(false)} title="Add Printer">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-md w-full">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Add Printer</h3>
                <button onClick={() => setShowAddPrinter(false)} className="text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <form onSubmit={handleAddPrinter} className="p-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Name *</label>
                  <input type="text" required value={printerForm.name} onChange={(e) => setPrinterForm({ ...printerForm, name: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" placeholder="Main Floor Laser" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Type *</label>
                  <select required value={printerForm.printer_type} onChange={(e) => setPrinterForm({ ...printerForm, printer_type: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream">
                    <option value="laser">Laser</option>
                    <option value="inkjet">Inkjet</option>
                    <option value="multifunction">Multifunction</option>
                    <option value="copier">Copier</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Location *</label>
                  <input type="text" required value={printerForm.location} onChange={(e) => setPrinterForm({ ...printerForm, location: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" placeholder="Main Floor - Near Circulation" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Model</label>
                  <input type="text" value={printerForm.model} onChange={(e) => setPrinterForm({ ...printerForm, model: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" placeholder="HP LaserJet Pro M404dn" />
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <button type="button" onClick={() => setShowAddPrinter(false)} className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70">Cancel</button>
                  <button type="submit" disabled={addingPrinter} className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50">
                    {addingPrinter ? <Loader2 className="w-5 h-5 motion-safe:animate-spin" /> : 'Add Printer'}
                  </button>
                </div>
              </form>
            </div>
          </ModalBackdrop>
        )}
      </div>
    </AdminShell>
  )
}
