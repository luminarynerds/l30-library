/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useAuth } from '../contexts/AuthContext';
import { AdminShell } from '../components/shells/AdminShell';
import {
  BarChart3,
  Users,
  Truck,
  Heart,
  Star,
  Download,
  RefreshCw,
  Loader2,
  Clock,
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
  getHomeDeliverySummary,
  getDeliveryAnalytics,
  getServiceAnalytics,
  getDeliveryReports,
  getPatronReports,
  getVolunteerReports,
  getSatisfactionMetrics,
  getVolunteerRecognition,
  getApplicationPipeline,
  requestExport,
} from '../api/homeDeliveryApi';
import { useTranslation} from '@/i18n'
import { clean } from '@/lib/utils'
import { StatCard } from '../components/delivery/reports/StatCard'
import { OverviewTab } from '../components/delivery/reports/OverviewTab'
import { DeliveriesTab } from '../components/delivery/reports/DeliveriesTab'
import { PatronsTab } from '../components/delivery/reports/PatronsTab'
import { VolunteersTab } from '../components/delivery/reports/VolunteersTab'
import { SatisfactionTab } from '../components/delivery/reports/SatisfactionTab'
import { ExportTab } from '../components/delivery/reports/ExportTab'

type Tab = 'overview' | 'deliveries' | 'patrons' | 'volunteers' | 'satisfaction' | 'export';

export default function HomeDeliveryReportsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token, isLoading: authLoading } = useAuth();
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [analyticsStart, setAnalyticsStart] = useState<string>(
    () => new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0] ?? ''
  );
  const [analyticsEnd, setAnalyticsEnd] = useState<string>(() => new Date().toISOString().split('T')[0] ?? '');

  const [exportType, setExportType] = useState<'deliveries' | 'patrons' | 'volunteers' | 'hours' | 'feedback'>('deliveries');
  const [exportFormat, setExportFormat] = useState<'csv' | 'json' | 'xlsx'>('csv');
  const [exportStart, setExportStart] = useState('');
  const [exportEnd, setExportEnd] = useState('');

  const { data: summary, isLoading: summaryLoading, refetch: refetchAll } = useQuery({
    queryKey: ['home-delivery-summary'],
    queryFn: getHomeDeliverySummary,
    enabled: !!token,
  });

  const { data: serviceAnalytics, isLoading: serviceLoading } = useQuery({
    queryKey: ['home-delivery-service-analytics', analyticsStart, analyticsEnd],
    queryFn: () => getServiceAnalytics(clean({ start_date: analyticsStart, end_date: analyticsEnd })),
    enabled: !!token && activeTab === 'overview',
  });

  const { data: deliveryReports, isLoading: deliveryReportsLoading } = useQuery({
    queryKey: ['home-delivery-delivery-reports'],
    queryFn: () => getDeliveryReports({ period_type: 'month', periods: 6 }),
    enabled: !!token && activeTab === 'deliveries',
  });

  const { data: patronReports, isLoading: patronReportsLoading } = useQuery({
    queryKey: ['home-delivery-patron-reports'],
    queryFn: () => getPatronReports({ limit: 50 }),
    enabled: !!token && activeTab === 'patrons',
  });

  const { data: volunteerReports, isLoading: volunteerReportsLoading } = useQuery({
    queryKey: ['home-delivery-volunteer-reports'],
    queryFn: () => getVolunteerReports({ limit: 50 }),
    enabled: !!token && activeTab === 'volunteers',
  });

  const { data: satisfactionData, isLoading: satisfactionLoading } = useQuery({
    queryKey: ['home-delivery-satisfaction-metrics'],
    queryFn: getSatisfactionMetrics,
    enabled: !!token && activeTab === 'satisfaction',
  });

  const { data: volunteerRecognition } = useQuery({
    queryKey: ['home-delivery-volunteer-recognition'],
    queryFn: getVolunteerRecognition,
    enabled: !!token && activeTab === 'volunteers',
  });

  const { data: applicationPipeline } = useQuery({
    queryKey: ['home-delivery-application-pipeline'],
    queryFn: getApplicationPipeline,
    enabled: !!token && activeTab === 'overview',
  });

  const { data: deliveryAnalytics } = useQuery({
    queryKey: ['home-delivery-delivery-analytics', analyticsStart, analyticsEnd],
    queryFn: () => getDeliveryAnalytics(clean({ start_date: analyticsStart, end_date: analyticsEnd })),
    enabled: !!token && activeTab === 'deliveries',
  });

  const exportMutation = useMutation({
    mutationFn: () => requestExport({
      report_type: exportType,
      format: exportFormat,
      ...(exportStart ? { start_date: exportStart } : {}),
      ...(exportEnd ? { end_date: exportEnd } : {}),
    }),
    onSuccess: (data) => {
      if (data.download_url) {
        window.open(data.download_url, '_blank', 'noopener,noreferrer');
        toast.success(t('homeDeliveryReports.exportStartedDownloadLinkOpened'));
      } else {
        toast.success(t('toast.homeDeliveryReports.exportRequestedIdExportidCheck', { exportid: data.export_id }));
      }
    },
    onError: (err: Error) => toast.error(err.message),
  });

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    );
  }

  if (!user || user.role === 'patron') return <></>;

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: 'overview', label: 'Overview', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'deliveries', label: 'Deliveries', icon: <Truck className="w-4 h-4" /> },
    { id: 'patrons', label: 'Patron Stats', icon: <Users className="w-4 h-4" /> },
    { id: 'volunteers', label: 'Volunteers', icon: <Heart className="w-4 h-4" /> },
    { id: 'satisfaction', label: 'Satisfaction', icon: <Star className="w-4 h-4" /> },
    { id: 'export', label: 'Export Data', icon: <Download className="w-4 h-4" /> },
  ];

  return (
    <AdminShell title="Service Reports">
      <div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-lsc-cream dark:bg-earth-800/30 rounded-xl">
              <BarChart3 className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <div>
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                Service Reports
              </h1>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Analytics, statistics, and data exports for home delivery services
              </p>
            </div>
          </div>
          <button
            onClick={() => refetchAll()}
            className="flex items-center gap-2 px-3 py-2 text-sm bg-lsc-cream dark:bg-earth-800 hover:bg-lsc-border dark:hover:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {!summaryLoading && summary && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Active Patrons" value={summary.active_enrolled_patrons} icon={<Users className="w-5 h-5 text-lsc-rose" />} />
            <StatCard label="Deliveries This Month" value={summary.total_deliveries_this_month} icon={<Truck className="w-5 h-5 text-status-success-500" />} />
            <StatCard label="Volunteer Hours (MTD)" value={`${summary.total_volunteer_hours_this_month}h`} icon={<Clock className="w-5 h-5 text-earth-600" />} />
            <StatCard
              label="Avg Rating"
              value={summary.average_delivery_rating?.toFixed(1) ?? 'N/A'}
              {...(summary.average_delivery_rating ? { sub: '/ 5.0' } : {})}
              icon={<Star className="w-5 h-5 text-status-warning-500" />}
            />
          </div>
        )}

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
              </button>
            ))}
          </nav>
        </div>

        {activeTab === 'overview' && (
          <OverviewTab
            analyticsStart={analyticsStart}
            analyticsEnd={analyticsEnd}
            setAnalyticsStart={setAnalyticsStart}
            setAnalyticsEnd={setAnalyticsEnd}
            serviceLoading={serviceLoading}
            serviceAnalytics={serviceAnalytics}
            applicationPipeline={applicationPipeline}
          />
        )}

        {activeTab === 'deliveries' && (
          <DeliveriesTab
            analyticsStart={analyticsStart}
            analyticsEnd={analyticsEnd}
            setAnalyticsStart={setAnalyticsStart}
            setAnalyticsEnd={setAnalyticsEnd}
            deliveryAnalytics={deliveryAnalytics}
            deliveryReports={deliveryReports}
            deliveryReportsLoading={deliveryReportsLoading}
          />
        )}

        {activeTab === 'patrons' && (
          <PatronsTab
            patronReports={patronReports}
            patronReportsLoading={patronReportsLoading}
          />
        )}

        {activeTab === 'volunteers' && (
          <VolunteersTab
            volunteerReports={volunteerReports}
            volunteerReportsLoading={volunteerReportsLoading}
            volunteerRecognition={volunteerRecognition}
          />
        )}

        {activeTab === 'satisfaction' && (
          <SatisfactionTab
            satisfactionData={satisfactionData}
            satisfactionLoading={satisfactionLoading}
          />
        )}

        {activeTab === 'export' && (
          <ExportTab
            exportType={exportType}
            setExportType={setExportType}
            exportFormat={exportFormat}
            setExportFormat={setExportFormat}
            exportStart={exportStart}
            setExportStart={setExportStart}
            exportEnd={exportEnd}
            setExportEnd={setExportEnd}
            onExport={() => exportMutation.mutate()}
            isPending={exportMutation.isPending}
          />
        )}
      </div>
    </AdminShell>
  );
}
