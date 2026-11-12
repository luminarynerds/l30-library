/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import {
  listApplications,
  listEnrollments,
  listVolunteers,
  listDeliveries,
  listRoutes,
  getHomeDeliverySummary,
  reviewApplication,
  createEnrollment,
  updateVolunteerStatus,
  createDelivery,
  createRoute,
  updateDeliveryStatus,
  updateEnrollment,
  getReadingPreferences,
  HomeDeliveryApplication,
  HomeDeliveryEnrollment,
  DeliveryVolunteer,
  Delivery,
  DeliveryRoute,
  HomeDeliveryReportSummary,
  HomeDeliveryApplicationStatus,
  DeliveryStatus,
  ReadingPreferenceProfile,
} from '../api/homeDeliveryApi';
import {
  Home,
  Users,
  Truck,
  ClipboardList,
  MapPin,
  BarChart3,
  Loader2,
  BookOpen,
  Heart,
  ExternalLink,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation} from '@/i18n'
import { clean } from '@/lib/utils'
import { AdminShell } from '../components/shells/AdminShell'
import { Link } from 'react-router-dom';
import { DashboardTab } from '../components/delivery/DashboardTab';
import { ApplicationsTab } from '../components/delivery/ApplicationsTab';
import { EnrollmentsTab } from '../components/delivery/EnrollmentsTab';
import { VolunteersTab } from '../components/delivery/VolunteersTab';
import { DeliveriesTab } from '../components/delivery/DeliveriesTab';
import { RoutesTab } from '../components/delivery/RoutesTab';
import { PreferencesTab } from '../components/delivery/PreferencesTab';
import { ReviewApplicationModal } from '../components/delivery/ReviewApplicationModal';
import { CreateDeliveryModal } from '../components/delivery/CreateDeliveryModal';
import { CreateRouteModal } from '../components/delivery/CreateRouteModal';
import PageContainer from '@/components/layout/PageContainer'

type Tab = 'dashboard' | 'applications' | 'enrollments' | 'volunteers' | 'deliveries' | 'routes' | 'preferences' | 'reports';

export default function HomeDeliveryManagementPage() {
  const { t } = useTranslation()
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { user: _user } = useAuth();
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');
  const [loading, setLoading] = useState(true);

  const [summary, setSummary] = useState<HomeDeliveryReportSummary | null>(null);
  const [applications, setApplications] = useState<HomeDeliveryApplication[]>([]);
  const [appFilter, setAppFilter] = useState<HomeDeliveryApplicationStatus | ''>('');
  const [enrollments, setEnrollments] = useState<HomeDeliveryEnrollment[]>([]);
  const [volunteers, setVolunteers] = useState<DeliveryVolunteer[]>([]);
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [deliveryFilter, setDeliveryFilter] = useState<DeliveryStatus | ''>('');
  const [routes, setRoutes] = useState<DeliveryRoute[]>([]);
  const [searchQuery, setSearchQuery] = useState('');

  const [selectedEnrollmentForPrefs, setSelectedEnrollmentForPrefs] = useState<HomeDeliveryEnrollment | null>(null);
  const [readingPrefs, setReadingPrefs] = useState<ReadingPreferenceProfile | null>(null);
  const [prefsLoading, setPrefsLoading] = useState(false);
  const [editingContactInfo, setEditingContactInfo] = useState(false);
  const [editPhone, setEditPhone] = useState('');
  const [editInstructions, setEditInstructions] = useState('');

  const [showReviewModal, setShowReviewModal] = useState(false);
  const [selectedApplication, setSelectedApplication] = useState<HomeDeliveryApplication | null>(null);
  const [reviewNotes, setReviewNotes] = useState('');
  const [denialReason, setDenialReason] = useState('');

  const [showCreateDeliveryModal, setShowCreateDeliveryModal] = useState(false);
  const [newDeliveryEnrollmentId, setNewDeliveryEnrollmentId] = useState<number | null>(null);
  const [newDeliveryDate, setNewDeliveryDate] = useState('');

  const [showCreateRouteModal, setShowCreateRouteModal] = useState(false);
  const [newRouteName, setNewRouteName] = useState('');
  const [newRouteDate, setNewRouteDate] = useState('');
  const [newRouteVolunteerId, setNewRouteVolunteerId] = useState<number | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [summaryRes, appsRes, enrollRes, volRes, delRes, routeRes] = await Promise.allSettled([
        getHomeDeliverySummary(),
        listApplications({ limit: 100 }),
        listEnrollments({ limit: 100 }),
        listVolunteers({ limit: 100 }),
        listDeliveries({ limit: 100 }),
        listRoutes({ limit: 100 }),
      ]);

      if (summaryRes.status === 'fulfilled') setSummary(summaryRes.value);
      else Sentry.captureException(summaryRes.reason instanceof Error ? summaryRes.reason : new Error(String(summaryRes.reason)));

      if (appsRes.status === 'fulfilled') setApplications(appsRes.value.applications);
      if (enrollRes.status === 'fulfilled') setEnrollments(enrollRes.value.enrollments);
      if (volRes.status === 'fulfilled') setVolunteers(volRes.value.volunteers);
      if (delRes.status === 'fulfilled') setDeliveries(delRes.value.deliveries);
      if (routeRes.status === 'fulfilled') setRoutes(routeRes.value.routes);

      const failures = [summaryRes, appsRes, enrollRes, volRes, delRes, routeRes].filter(r => r.status === 'rejected');
      if (failures.length > 0) {
        toast.error(t('homeDeliveryManagement.failedToLoadHomeDelivery'));
      }
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleReviewApplication = async (status: HomeDeliveryApplicationStatus) => {
    if (!selectedApplication) return;
    try {
      await reviewApplication(selectedApplication.id, clean({
        status,
        ...(reviewNotes ? { review_notes: reviewNotes } : {}),
        denial_reason: status === 'denied' ? denialReason : undefined,
      }));
      toast.success(t('toast.homeDeliveryManagement.applicationStatus', { status: status }));
      if (status === 'approved') {
        await createEnrollment({ application_id: selectedApplication.id });
        toast.success(t('toast.homeDeliveryManagement.enrollmentCreated'));
      }
      setShowReviewModal(false);
      setSelectedApplication(null);
      setReviewNotes('');
      setDenialReason('');
      loadData();
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      toast.error(t('homeDeliveryManagement.failedToReviewApplication'));
    }
  };

  const handleApproveVolunteer = async (volunteer: DeliveryVolunteer) => {
    try {
      await updateVolunteerStatus(volunteer.id, clean({
        status: 'active',
        background_check_completed: true,
        background_check_date: new Date().toISOString().split('T')[0],
        training_completed: true,
        training_date: new Date().toISOString().split('T')[0],
      }));
      toast.success(t('toast.homeDeliveryManagement.volunteerApproved'));
      loadData();
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      toast.error(t('homeDeliveryManagement.failedToApproveVolunteer'));
    }
  };

  const handleCreateDelivery = async () => {
    if (!newDeliveryEnrollmentId || !newDeliveryDate) {
      toast.error(t('homeDeliveryManagement.pleaseSelectAPatronAnd'));
      return;
    }
    try {
      await createDelivery({
        enrollment_id: newDeliveryEnrollmentId,
        scheduled_date: newDeliveryDate,
      });
      toast.success(t('toast.homeDeliveryManagement.deliveryScheduled'));
      setShowCreateDeliveryModal(false);
      setNewDeliveryEnrollmentId(null);
      setNewDeliveryDate('');
      loadData();
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      toast.error(t('homeDeliveryManagement.failedToCreateDelivery'));
    }
  };

  const handleCreateRoute = async () => {
    if (!newRouteName || !newRouteDate) {
      toast.error(t('homeDeliveryManagement.pleaseEnterRouteNameAnd'));
      return;
    }
    try {
      await createRoute({
        name: newRouteName,
        date: newRouteDate,
        ...(newRouteVolunteerId ? { volunteer_id: newRouteVolunteerId } : {}),
      });
      toast.success(t('toast.homeDeliveryManagement.routeCreated'));
      setShowCreateRouteModal(false);
      setNewRouteName('');
      setNewRouteDate('');
      setNewRouteVolunteerId(null);
      loadData();
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      toast.error(t('homeDeliveryManagement.failedToCreateRoute'));
    }
  };

  const handleLoadPreferences = async (enrollment: HomeDeliveryEnrollment) => {
    setSelectedEnrollmentForPrefs(enrollment);
    setEditPhone(enrollment.contact_phone || '');
    setEditInstructions(enrollment.delivery_instructions || '');
    setPrefsLoading(true);
    try {
      const prefs = await getReadingPreferences(enrollment.id);
      setReadingPrefs(prefs);
    } catch {
      setReadingPrefs(null);
    } finally {
      setPrefsLoading(false);
    }
  };

  const handleSaveContactInfo = async () => {
    if (!selectedEnrollmentForPrefs) return;
    try {
      await updateEnrollment(selectedEnrollmentForPrefs.id, {
        contact_phone: editPhone,
        delivery_instructions: editInstructions,
      });
      toast.success(t('toast.homeDeliveryManagement.contactInfoUpdated'));
      setEditingContactInfo(false);
      loadData();
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      toast.error(t('homeDeliveryManagement.failedToUpdateContactInfo'));
    }
  };

  const handleUpdateDeliveryStatus = async (delivery: Delivery, status: DeliveryStatus) => {
    try {
      await updateDeliveryStatus(delivery.id, { status });
      toast.success(t('toast.homeDeliveryManagement.deliveryMarkedAsReplace', { replace: status.replace('_', ' ') }));
      loadData();
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      toast.error(t('homeDeliveryManagement.failedToUpdateDeliveryStatus'));
    }
  };

  const filteredApplications = applications.filter((app) => {
    if (appFilter && app.status !== appFilter) return false;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        app.patron_name?.toLowerCase().includes(query) ||
        app.patron_library_card?.toLowerCase().includes(query)
      );
    }
    return true;
  });

  const filteredDeliveries = deliveries.filter((del) => {
    if (deliveryFilter && del.status !== deliveryFilter) return false;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        del.patron_name?.toLowerCase().includes(query) ||
        del.patron_library_card?.toLowerCase().includes(query)
      );
    }
    return true;
  });

  const tabs = [
    { id: 'dashboard' as Tab, label: 'Dashboard', icon: BarChart3 },
    { id: 'applications' as Tab, label: 'Applications', icon: ClipboardList, badge: summary?.pending_applications },
    { id: 'enrollments' as Tab, label: 'Enrollments', icon: Users },
    { id: 'volunteers' as Tab, label: 'Volunteers', icon: Heart },
    { id: 'deliveries' as Tab, label: 'Deliveries', icon: Truck },
    { id: 'routes' as Tab, label: 'Routes', icon: MapPin },
    { id: 'preferences' as Tab, label: 'Patron Prefs', icon: BookOpen },
    { id: 'reports' as Tab, label: 'Reports', icon: BarChart3 },
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
      case 'approved':
      case 'delivered':
      case 'completed':
        return 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300';
      case 'pending':
      case 'pending_approval':
      case 'scheduled':
      case 'draft':
        return 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300';
      case 'denied':
      case 'terminated':
      case 'cancelled':
      case 'delivery_failed':
        return 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300';
      case 'paused':
      case 'under_review':
      case 'items_selected':
      case 'packed':
      case 'in_progress':
        return 'bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light';
      case 'out_for_delivery':
        return 'bg-category-100 dark:bg-category-900/30 text-category-800 dark:text-category-300';
      default:
        return 'bg-earth-100 dark:bg-earth-700 text-earth-800 dark:text-earth-100';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin motion-reduce:animate-none text-status-warning-600" />
      </div>
    );
  }

  return (
    <AdminShell title="Home Delivery Service" subtitle={t('homeDeliveryManagement.managePatronApplicationsVolunteersAnd')}>
      <div className="min-h-screen bg-lsc-cream dark:bg-earth-900">
        <div className="bg-lsc-white dark:bg-earth-800 border-b">
          <PageContainer width="wide">
            <div className="py-6">
              <div className="flex items-center gap-3">
                <Home className="w-8 h-8 text-status-warning-600" />
                <div></div>
              </div>
            </div>
            <div className="flex gap-1 overflow-x-auto pb-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-t-lg transition-colors whitespace-nowrap ${
                    activeTab === tab.id
                      ? 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300 border-b-2 border-status-warning-600'
                      : 'text-earth-600 hover:text-lsc-dark dark:text-lsc-cream dark:hover:text-earth-100 hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700'
                  }`}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                  {tab.badge ? (
                    <span className="ml-1 px-2 py-0.5 text-xs bg-status-danger-500 text-white rounded-full">
                      {tab.badge}
                    </span>
                  ) : null}
                </button>
              ))}
            </div>
          </PageContainer>
        </div>

        <PageContainer width="wide" className="py-6">
          {activeTab === 'dashboard' && (summary ? (
            <DashboardTab
              summary={summary}
              onScheduleDelivery={() => setShowCreateDeliveryModal(true)}
              onCreateRoute={() => setShowCreateRouteModal(true)}
              onReviewApplications={() => setActiveTab('applications')}
            />
          ) : (
            <div className="space-y-6">
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-8 text-center">
                <BarChart3 className="w-12 h-12 text-earth-600 mx-auto mb-4" />
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">Dashboard Unavailable</h3>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">Summary data could not be loaded. Other tabs are still available.</p>
                <button onClick={loadData} className="px-4 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700">
                  Retry
                </button>
              </div>
            </div>
          ))}

          {activeTab === 'applications' && (
            <ApplicationsTab
              applications={filteredApplications}
              searchQuery={searchQuery}
              appFilter={appFilter}
              onSearchChange={setSearchQuery}
              onFilterChange={setAppFilter}
              onReview={(app) => { setSelectedApplication(app); setShowReviewModal(true); }}
              getStatusColor={getStatusColor}
            />
          )}

          {activeTab === 'enrollments' && (
            <EnrollmentsTab
              enrollments={enrollments}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              onScheduleDelivery={(id) => { setNewDeliveryEnrollmentId(id); setShowCreateDeliveryModal(true); }}
              getStatusColor={getStatusColor}
            />
          )}

          {activeTab === 'volunteers' && (
            <VolunteersTab
              volunteers={volunteers}
              onApprove={handleApproveVolunteer}
              getStatusColor={getStatusColor}
            />
          )}

          {activeTab === 'deliveries' && (
            <DeliveriesTab
              deliveries={filteredDeliveries}
              searchQuery={searchQuery}
              deliveryFilter={deliveryFilter}
              onSearchChange={setSearchQuery}
              onFilterChange={setDeliveryFilter}
              onScheduleDelivery={() => setShowCreateDeliveryModal(true)}
              onUpdateStatus={handleUpdateDeliveryStatus}
              getStatusColor={getStatusColor}
            />
          )}

          {activeTab === 'routes' && (
            <RoutesTab
              routes={routes}
              onCreateRoute={() => setShowCreateRouteModal(true)}
              getStatusColor={getStatusColor}
            />
          )}

          {activeTab === 'preferences' && (
            <PreferencesTab
              enrollments={enrollments}
              selectedEnrollment={selectedEnrollmentForPrefs}
              readingPrefs={readingPrefs}
              prefsLoading={prefsLoading}
              editingContactInfo={editingContactInfo}
              editPhone={editPhone}
              editInstructions={editInstructions}
              onSelectEnrollment={handleLoadPreferences}
              onEditContactInfo={() => setEditingContactInfo(true)}
              onCancelEdit={() => setEditingContactInfo(false)}
              onSaveContactInfo={handleSaveContactInfo}
              onEditPhoneChange={setEditPhone}
              onEditInstructionsChange={setEditInstructions}
            />
          )}

          {activeTab === 'reports' && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
              <h3 className="font-serif text-lg font-semibold mb-4">{t('homeDeliveryManagement.homeDeliveryServiceReports')}</h3>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                View detailed analytics, satisfaction metrics, and data exports on the dedicated reports page.
              </p>
              <Link
                to="/staff/home-delivery/reports"
                className="inline-flex items-center gap-2 px-4 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700"
              >
                <BarChart3 className="w-4 h-4" />
                Open Full Reports Dashboard
                <ExternalLink className="w-4 h-4" />
              </Link>
            </div>
          )}
        </PageContainer>

        {showReviewModal && selectedApplication && (
          <ReviewApplicationModal
            application={selectedApplication}
            reviewNotes={reviewNotes}
            denialReason={denialReason}
            onReviewNotesChange={setReviewNotes}
            onDenialReasonChange={setDenialReason}
            onReview={handleReviewApplication}
            onClose={() => { setShowReviewModal(false); setSelectedApplication(null); setReviewNotes(''); setDenialReason(''); }}
          />
        )}

        {showCreateDeliveryModal && (
          <CreateDeliveryModal
            enrollments={enrollments}
            enrollmentId={newDeliveryEnrollmentId}
            date={newDeliveryDate}
            onEnrollmentChange={setNewDeliveryEnrollmentId}
            onDateChange={setNewDeliveryDate}
            onSubmit={handleCreateDelivery}
            onClose={() => { setShowCreateDeliveryModal(false); setNewDeliveryEnrollmentId(null); setNewDeliveryDate(''); }}
          />
        )}

        {showCreateRouteModal && (
          <CreateRouteModal
            volunteers={volunteers}
            name={newRouteName}
            date={newRouteDate}
            volunteerId={newRouteVolunteerId}
            onNameChange={setNewRouteName}
            onDateChange={setNewRouteDate}
            onVolunteerChange={setNewRouteVolunteerId}
            onSubmit={handleCreateRoute}
            onClose={() => { setShowCreateRouteModal(false); setNewRouteName(''); setNewRouteDate(''); setNewRouteVolunteerId(null); }}
          />
        )}
      </div>
    </AdminShell>
  );
}
