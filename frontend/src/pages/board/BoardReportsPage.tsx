/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useState } from "react"
import { API_BASE } from '@/api/types';
import {
  Download,
  Plus,
  RefreshCw,
  Loader2,
  Mail,
  BarChart3,
  Eye,
  Archive,
} from "lucide-react";
import api from "../../api/api";
import { getAccessToken } from "../../utils/tokenStore";
import toast from "react-hot-toast";
import { useTranslation, getCurrentLocale } from '@/i18n'
import type { BoardReport, ReportStats } from '../../components/board/BoardReportTypes'
import { KeyMetricsCards } from '../../components/board/KeyMetricsCards'
import { CirculationChart } from '../../components/board/CirculationChart'
import { CollectionPieChart } from '../../components/board/CollectionPieChart'
import { FinancialSummary } from '../../components/board/FinancialSummary'
import { PeriodComparison } from '../../components/board/PeriodComparison'
import { NarrativePromptsPanel } from '../../components/board/NarrativePromptsPanel'
import { WebsiteTrafficCard } from '../../components/board/WebsiteTrafficCard'
import { EmailReportModal } from '../../components/board/EmailReportModal'
import { BoardReportGeneratorForm } from '../../components/board/BoardReportGeneratorForm'
import PageContainer from '@/components/layout/PageContainer'
import { openDownloadInNewTab } from '@/utils/openDownload'

export default function BoardReportsPage() {
  const { t } = useTranslation()
  const [reports, setReports] = useState<BoardReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [showGenerator, setShowGenerator] = useState(false);
  const [previewData, setPreviewData] = useState<ReportStats | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [emailReportId, setEmailReportId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<"dashboard" | "archive">("dashboard");
  const [skip, setSkip] = useState(0);
  const limit = 10;

  const fetchReports = async () => {
    try {
      setLoading(true);
      const response = await api.get(`${API_BASE}/board/reports?skip=${skip}&limit=${limit}`);
      setReports(response);
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      toast.error(t('boardReports.failedToLoadReports'));
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    fetchReports();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [skip]);

  const loadDashboardPreview = async () => {
    try {
      setPreviewLoading(true);
      const response = await api.get(`${API_BASE}/board/reports/quick/monthly-report`);
      setPreviewData(response);
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      toast.error(t("boardReports.failedToLoadDashboard") || "Failed to load report data");
    } finally {
      setPreviewLoading(false);
    }
  };


  useEffect(() => {
    loadDashboardPreview();
  }, []);

  const generateMonthlyReport = async () => {
    try {
      setGenerating(true);
      await api.post(`${API_BASE}/board/reports/generate`, {
        start_date: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString(),
        end_date: new Date().toISOString(),
        include_comparison: true,
        export_format: "both",
      });
      toast.success(t('boardReports.monthlyReportGeneratedWithPowerpoint'));
      fetchReports();
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      toast.error(t('boardReports.failedToGenerateMonthlyReport'));
    } finally {
      setGenerating(false);
    }
  };

  const viewReportStats = async (reportId: number) => {
    if (selectedReportId === reportId) {
      setSelectedReportId(null);
      return;
    }
    try {
      const response = await api.get(`${API_BASE}/board/reports/${reportId}/stats`);
      if (response.stats_snapshot) {
        setPreviewData(response.stats_snapshot);
        setSelectedReportId(reportId);
        setActiveTab("dashboard");
      }
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      toast.error(t('boardReports.failedToLoadReportDetails'));
    }
  };

  const downloadFile = async (reportId: number, format: "powerpoint" | "pdf") => {
    try {
      const endpoint = format === "powerpoint"
        ? `${API_BASE}/board/reports/${reportId}/powerpoint`
        : `${API_BASE}/board/reports/${reportId}/pdf`;

      const token = getAccessToken();
      // eslint-disable-next-line no-restricted-syntax -- PDF/PowerPoint report download, blob response
      const res = await fetch(endpoint, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error(`Download failed: ${res.status}`);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      openDownloadInNewTab(
        url,
        `board_report_${reportId}.${format === "powerpoint" ? "pptx" : "pdf"}`,
      );
      window.URL.revokeObjectURL(url);
      toast.success(t('toast.boardReports.reportDownloaded'));
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      toast.error(t('toast.boardReports.failedToDownloadFormat', { format: format }));
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(getCurrentLocale(), {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const formatPeriod = (start: string, end: string) => {
    return `${formatDate(start)} - ${formatDate(end)}`;
  };

  if (loading && reports.length === 0 && !previewData) {
    return (
      <>
        <PageContainer className="py-8">
          <div className="motion-safe:animate-pulse space-y-4">
            <div className="h-8 bg-earth-200 dark:bg-earth-600 rounded w-1/3"></div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-28 bg-earth-200 dark:bg-earth-600 rounded-lg"></div>
              ))}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[1, 2].map((i) => (
                <div key={i} className="h-64 bg-earth-200 dark:bg-earth-600 rounded-lg"></div>
              ))}
            </div>
          </div>
        </PageContainer>
      </>
    );
  }

  return (
    <>
      <PageContainer className="py-8">
        {/* Header */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Board Reports
            </h1>
            <p className="text-earth-600 dark:text-earth-200 mt-2">
              Generate and manage reports for board meetings.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={generateMonthlyReport}
              disabled={generating}
              className="flex items-center gap-2 px-4 py-2 bg-lsc-primary text-white rounded-lg hover:bg-lsc-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {generating ? (
                <>
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <RefreshCw className="w-4 h-4" />
                  Generate Monthly Report
                </>
              )}
            </button>
            <button
              onClick={() => setShowGenerator(true)}
              className="flex items-center gap-2 px-4 py-2 bg-earth-200 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-earth-300 dark:hover:bg-earth-600 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Custom Range
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="mb-6 flex gap-1 bg-earth-100 dark:bg-earth-800 p-1 rounded-lg w-fit">
          <button
            onClick={() => setActiveTab("dashboard")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === "dashboard"
                ? "bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream shadow-sm"
                : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-900 dark:hover:text-white"
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            Dashboard
          </button>
          <button
            onClick={() => setActiveTab("archive")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === "archive"
                ? "bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream shadow-sm"
                : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-900 dark:hover:text-white"
            }`}
          >
            <Archive className="w-4 h-4" />
            Report Archive
          </button>
        </div>

        {/* Dashboard Tab */}
        {activeTab === "dashboard" && (
          <>
            {previewLoading ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-primary" />
                <span className="ml-3 text-lsc-dark/70 dark:text-lsc-cream/70">Loading dashboard data...</span>
              </div>
            ) : previewData ? (
              <>
                <KeyMetricsCards data={previewData} />
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
                  <CirculationChart data={previewData} />
                  <CollectionPieChart data={previewData} />
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
                  <FinancialSummary data={previewData} />
                  <PeriodComparison data={previewData} />
                </div>
                <div className="mt-6">
                  <WebsiteTrafficCard data={previewData} />
                </div>
                <NarrativePromptsPanel data={previewData} />
              </>
            ) : (
              <div className="text-center py-12 bg-earth-50 dark:bg-earth-900 rounded-lg">
                <BarChart3 className="w-12 h-12 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-4" />
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                  Generate your first report to see the dashboard
                </p>
                <button
                  onClick={generateMonthlyReport}
                  disabled={generating}
                  className="px-4 py-2 bg-lsc-primary text-white rounded-lg hover:bg-lsc-primary/90 disabled:opacity-50"
                >
                  Generate First Report
                </button>
              </div>
            )}
          </>
        )}

        {/* Archive Tab */}
        {activeTab === "archive" && (
          <>
            {reports.length === 0 ? (
              <div className="text-center py-12 bg-earth-50 dark:bg-earth-900 rounded-lg">
                <Archive className="w-12 h-12 text-earth-600 mx-auto mb-4" />
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{t('boardReports.noReportsArchivedYet')}</p>
                <button
                  onClick={generateMonthlyReport}
                  disabled={generating}
                  className="px-4 py-2 bg-lsc-primary text-white rounded-lg hover:bg-lsc-primary/90 disabled:opacity-50"
                >
                  Generate First Report
                </button>
              </div>
            ) : (
              <>
                <div className="overflow-x-auto rounded-lg border border-lsc-border dark:border-earth-700">
                  <table className="w-full">
                    <thead className="bg-earth-100 dark:bg-earth-800">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">Period</th>
                        <th className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">Status</th>
                        <th className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">Format</th>
                        <th className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">Email</th>
                        <th className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">Generated</th>
                        <th className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reports.map((report, idx) => (
                        <tr
                          key={report.id}
                          className={`border-t border-lsc-border dark:border-earth-700 ${
                            idx % 2 === 0 ? "bg-lsc-white dark:bg-earth-900" : "bg-earth-50 dark:bg-earth-800"
                          } ${selectedReportId === report.id ? "ring-2 ring-lsc-primary ring-inset" : ""}`}
                        >
                          <td className="px-4 py-3 text-sm text-lsc-dark dark:text-lsc-cream">
                            {formatPeriod(report.report_period_start, report.report_period_end)}
                          </td>
                          <td className="px-4 py-3 text-sm">
                            <span
                              className={`px-3 py-1 rounded-full text-xs font-medium ${
                                report.status === "generated"
                                  ? "bg-status-success-100 text-status-success-800 dark:bg-status-success-900 dark:text-status-success-200"
                                  : report.status === "sent"
                                    ? "bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-lsc-rose-light/80"
                                    : "bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900 dark:text-status-warning-200"
                              }`}
                            >
                              {report.status}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm text-lsc-dark dark:text-lsc-cream">
                            <div className="flex gap-1">
                              {report.file_powerpoint && (
                                <span className="px-2 py-1 bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-lsc-rose-light/80 rounded text-xs">
                                  PPTX
                                </span>
                              )}
                              {report.file_pdf && (
                                <span className="px-2 py-1 bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900 dark:text-status-danger-200 rounded text-xs">
                                  PDF
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm">
                            {report.email_sent ? (
                              <span className="px-2 py-1 bg-status-success-100 text-status-success-800 dark:bg-status-success-900 dark:text-status-success-200 rounded text-xs">
                                Sent
                              </span>
                            ) : (
                              <span className="text-earth-600 text-xs">Not sent</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            {report.generated_at ? formatDate(report.generated_at) : "-"}
                          </td>
                          <td className="px-4 py-3 text-sm">
                            <div className="flex gap-1 flex-wrap">
                              <button
                                onClick={() => viewReportStats(report.id)}
                                className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-earth-500 text-white rounded hover:bg-earth-600 transition-colors"
                                title="View report data"
                              >
                                <Eye className="w-3 h-3" />
                                View
                              </button>
                              {report.file_powerpoint && (
                                <button
                                  onClick={() => downloadFile(report.id, "powerpoint")}
                                  className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-earth-500 text-white rounded hover:bg-lsc-rose transition-colors"
                                  title="Download PowerPoint"
                                >
                                  <Download className="w-3 h-3" />
                                  PPTX
                                </button>
                              )}
                              {report.file_pdf && (
                                <button
                                  onClick={() => downloadFile(report.id, "pdf")}
                                  className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-status-danger-500 text-white rounded hover:bg-status-danger-600 transition-colors"
                                  title="Download PDF"
                                >
                                  <Download className="w-3 h-3" />
                                  PDF
                                </button>
                              )}
                              {(report.file_powerpoint || report.file_pdf) && (
                                <button
                                  onClick={() => {
                                    setEmailReportId(report.id);
                                    setShowEmailModal(true);
                                  }}
                                  className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-status-success-600 text-white rounded hover:bg-status-success-700 transition-colors"
                                  title="Email to board"
                                >
                                  <Mail className="w-3 h-3" />
                                  Email
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                <div className="mt-6 flex justify-between items-center">
                  <button
                    onClick={() => setSkip(Math.max(0, skip - limit))}
                    disabled={skip === 0}
                    className="px-4 py-2 bg-earth-200 dark:bg-earth-700 rounded disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                  >
                    Previous
                  </button>
                  {reports.length > 0 && (
                    <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      Showing {skip + 1}-{Math.min(skip + limit, skip + reports.length)} reports
                    </span>
                  )}
                  <button
                    onClick={() => setSkip(skip + limit)}
                    disabled={reports.length < limit}
                    className="px-4 py-2 bg-earth-200 dark:bg-earth-700 rounded disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                  >
                    Next
                  </button>
                </div>
              </>
            )}
          </>
        )}

        {showGenerator && (
          <BoardReportGeneratorForm
            onClose={() => setShowGenerator(false)}
            onSuccess={() => {
              setShowGenerator(false);
              setSkip(0);
              fetchReports();
              loadDashboardPreview();
            }}
          />
        )}

        {showEmailModal && emailReportId && (
          <EmailReportModal
            reportId={emailReportId}
            onClose={() => {
              setShowEmailModal(false);
              setEmailReportId(null);
            }}
            onSuccess={() => {
              setShowEmailModal(false);
              setEmailReportId(null);
              fetchReports();
            }}
          />
        )}
      </PageContainer>
    </>
  );
}
