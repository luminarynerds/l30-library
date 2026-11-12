/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../contexts/AuthContext';
import { AdminShell } from '../components/shells/AdminShell';
import {
  Users,
  Heart,
  Calendar,
  Clock,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
  Loader2,
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
  listVolunteers,
  getVolunteer,
  updateVolunteerStatus,
  getVolunteerHours,
  logVolunteerHours,
  verifyVolunteerHours,
  getVolunteerSchedule,
  createScheduleEntry,
  deleteScheduleEntry,
  DeliveryVolunteer,
  VolunteerStatus,
} from '../api/homeDeliveryApi';
import { useTranslation} from '@/i18n';
import { clean } from '@/lib/utils';
import { RosterTab } from '../components/delivery/volunteers/RosterTab';
import { AvailabilityTab } from '../components/delivery/volunteers/AvailabilityTab';
import { HoursTab } from '../components/delivery/volunteers/HoursTab';
import { VolunteerDetailModal } from '../components/delivery/volunteers/VolunteerDetailModal';
import { StatusUpdateModal } from '../components/delivery/volunteers/StatusUpdateModal';
import { ScheduleModal } from '../components/delivery/volunteers/ScheduleModal';
import { HoursModal } from '../components/delivery/volunteers/HoursModal';

type Tab = 'roster' | 'availability' | 'hours';

export default function HomeDeliveryVolunteersPage(): React.ReactElement {
  const { t } = useTranslation();
  const { user, token, isLoading: authLoading } = useAuth();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<Tab>('roster');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<VolunteerStatus | ''>('');
  const [availableOnDate, setAvailableOnDate] = useState('');

  // Detail / modal states
  const [selectedVolunteer, setSelectedVolunteer] = useState<DeliveryVolunteer | null>(null);
  const [showVolunteerDetail, setShowVolunteerDetail] = useState(false);
  const [showHoursModal, setShowHoursModal] = useState(false);
  const [showStatusModal, setShowStatusModal] = useState(false);
  const [showScheduleModal, setShowScheduleModal] = useState(false);

  // Hours log form
  const [hoursVolunteerId, setHoursVolunteerId] = useState<number | null>(null);
  const [hoursDate, setHoursDate] = useState('');
  const [hoursCount, setHoursCount] = useState('');
  const [hoursActivityType, setHoursActivityType] = useState('delivery');
  const [hoursNotes, setHoursNotes] = useState('');

  // Status update form
  const [statusVolunteerId, setStatusVolunteerId] = useState<number | null>(null);
  const [newStatus, setNewStatus] = useState<VolunteerStatus>('active');
  const [bgCheckCompleted, setBgCheckCompleted] = useState(false);
  const [bgCheckDate, setBgCheckDate] = useState('');
  const [bgCheckExpiry, setBgCheckExpiry] = useState('');
  const [trainingCompleted, setTrainingCompleted] = useState(false);
  const [trainingDate, setTrainingDate] = useState('');

  // Schedule entry form
  const [scheduleVolunteerId, setScheduleVolunteerId] = useState<number | null>(null);
  const [scheduleDate, setScheduleDate] = useState('');
  const [scheduleIsAvailable, setScheduleIsAvailable] = useState(true);
  const [scheduleStartTime, setScheduleStartTime] = useState('');
  const [scheduleEndTime, setScheduleEndTime] = useState('');

  // Queries
  const { data: volunteersData, isLoading: volunteersLoading, refetch } = useQuery({
    queryKey: ['home-delivery-volunteers', statusFilter, searchQuery, availableOnDate],
    queryFn: () => listVolunteers({
      ...(statusFilter ? { status: statusFilter } : {}),
      ...(searchQuery ? { search: searchQuery } : {}),
      ...(availableOnDate ? { available_on: availableOnDate } : {}),
      limit: 100,
    }),
    enabled: !!token,
  });

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { data: _volunteerDetail } = useQuery({
    queryKey: ['home-delivery-volunteer-detail', selectedVolunteer?.id],
    queryFn: () => getVolunteer(selectedVolunteer!.id),
    enabled: !!selectedVolunteer?.id && showVolunteerDetail,
  });

  const { data: hoursData } = useQuery({
    queryKey: ['home-delivery-volunteer-hours', hoursVolunteerId],
    queryFn: () => getVolunteerHours(hoursVolunteerId!),
    enabled: !!hoursVolunteerId,
  });

  const { data: scheduleData } = useQuery({
    queryKey: ['home-delivery-volunteer-schedule', scheduleVolunteerId],
    queryFn: () => getVolunteerSchedule(scheduleVolunteerId!, clean({
      start_date: new Date().toISOString().split('T')[0],
      end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    })),
    enabled: !!scheduleVolunteerId,
  });

  // Mutations
  const updateStatusMutation = useMutation({
    mutationFn: () => updateVolunteerStatus(statusVolunteerId!, {
      status: newStatus,
      ...(bgCheckCompleted ? { background_check_completed: true } : {}),
      ...(bgCheckDate ? { background_check_date: bgCheckDate } : {}),
      ...(bgCheckExpiry ? { background_check_expiry: bgCheckExpiry } : {}),
      ...(trainingCompleted ? { training_completed: true } : {}),
      ...(trainingDate ? { training_date: trainingDate } : {}),
    }),
    onSuccess: () => {
      toast.success(t('toast.homeDeliveryVolunteers.volunteerStatusUpdated'));
      queryClient.invalidateQueries({ queryKey: ['home-delivery-volunteers'] });
      setShowStatusModal(false);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const logHoursMutation = useMutation({
    mutationFn: () => logVolunteerHours(hoursVolunteerId!, {
      date: hoursDate,
      hours: parseFloat(hoursCount),
      activity_type: hoursActivityType,
      ...(hoursNotes ? { notes: hoursNotes } : {}),
    }),
    onSuccess: () => {
      toast.success(t('toast.homeDeliveryVolunteers.hoursLoggedSuccessfully'));
      queryClient.invalidateQueries({ queryKey: ['home-delivery-volunteer-hours', hoursVolunteerId] });
      setHoursDate('');
      setHoursCount('');
      setHoursNotes('');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const verifyHoursMutation = useMutation({
    mutationFn: (logId: number) => verifyVolunteerHours(logId),
    onSuccess: () => {
      toast.success(t('toast.homeDeliveryVolunteers.hoursVerified'));
      queryClient.invalidateQueries({ queryKey: ['home-delivery-volunteer-hours'] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const createScheduleMutation = useMutation({
    mutationFn: () => createScheduleEntry(scheduleVolunteerId!, {
      date: scheduleDate,
      is_available: scheduleIsAvailable,
      ...(scheduleStartTime ? { time_start: scheduleStartTime } : {}),
      ...(scheduleEndTime ? { time_end: scheduleEndTime } : {}),
    }),
    onSuccess: () => {
      toast.success(t('toast.homeDeliveryVolunteers.scheduleEntryCreated'));
      queryClient.invalidateQueries({ queryKey: ['home-delivery-volunteer-schedule'] });
      setScheduleDate('');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteScheduleMutation = useMutation({
    mutationFn: ({ volunteerId, date }: { volunteerId: number; date: string }) =>
      deleteScheduleEntry(volunteerId, date),
    onSuccess: () => {
      toast.success(t('toast.homeDeliveryVolunteers.scheduleEntryRemoved'));
      queryClient.invalidateQueries({ queryKey: ['home-delivery-volunteer-schedule'] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const openHoursModal = (volunteer: DeliveryVolunteer) => {
    setHoursVolunteerId(volunteer.id);
    setShowHoursModal(true);
  };

  const openStatusModal = (volunteer: DeliveryVolunteer) => {
    setStatusVolunteerId(volunteer.id);
    setNewStatus(volunteer.status);
    setBgCheckCompleted(volunteer.background_check_completed);
    setBgCheckDate(volunteer.background_check_date ?? '');
    setBgCheckExpiry(volunteer.background_check_expiry ?? '');
    setTrainingCompleted(volunteer.training_completed);
    setTrainingDate(volunteer.training_date ?? '');
    setShowStatusModal(true);
  };

  const openScheduleModal = (volunteer: DeliveryVolunteer) => {
    setScheduleVolunteerId(volunteer.id);
    setShowScheduleModal(true);
  };

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    );
  }

  if (!user || user.role === 'patron') return <></>;

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: 'roster', label: 'Volunteer Roster', icon: <Users className="w-4 h-4" /> },
    { id: 'availability', label: 'Availability', icon: <Calendar className="w-4 h-4" /> },
    { id: 'hours', label: 'Hours Log', icon: <Clock className="w-4 h-4" /> },
  ];

  const volunteers = volunteersData?.volunteers ?? [];

  return (
    <AdminShell title="Home Delivery Volunteers">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-lsc-cream dark:bg-earth-800/30 rounded-xl">
            <Heart className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Volunteer Coordination
            </h1>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Manage volunteers, schedules, and hours
            </p>
          </div>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 px-3 py-2 text-sm bg-lsc-cream dark:bg-earth-800 hover:bg-lsc-border dark:hover:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          {
            label: 'Total Volunteers',
            count: volunteersData?.total ?? 0,
            color: 'text-lsc-dark dark:text-lsc-cream',
            icon: <Users className="w-6 h-6 text-lsc-rose" />,
          },
          {
            label: 'Active',
            count: volunteers.filter((v) => v.status === 'active').length,
            color: 'text-status-success-700 dark:text-status-success-400',
            icon: <CheckCircle className="w-6 h-6 text-status-success-500" />,
          },
          {
            label: 'Pending Approval',
            count: volunteers.filter((v) => v.status === 'pending_approval').length,
            color: 'text-lsc-rose dark:text-lsc-rose-light',
            icon: <AlertTriangle className="w-6 h-6 text-earth-600" />,
          },
          {
            label: 'On Leave',
            count: volunteers.filter((v) => v.status === 'on_leave').length,
            color: 'text-status-warning-700 dark:text-status-warning-400',
            icon: <Clock className="w-6 h-6 text-status-warning-500" />,
          },
        ].map((stat) => (
          <div key={stat.label} className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
            <div className="flex items-center gap-3">
              {stat.icon}
              <div>
                <p className={`text-2xl font-bold ${stat.color}`}>{stat.count}</p>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{stat.label}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

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
            </button>
          ))}
        </nav>
      </div>

      {activeTab === 'roster' && (
        <RosterTab
          volunteers={volunteers}
          volunteersLoading={volunteersLoading}
          searchQuery={searchQuery}
          statusFilter={statusFilter}
          onSearchChange={setSearchQuery}
          onStatusFilterChange={setStatusFilter}
          onViewVolunteer={(v) => { setSelectedVolunteer(v); setShowVolunteerDetail(true); }}
          onOpenStatusModal={openStatusModal}
          onOpenScheduleModal={openScheduleModal}
          onOpenHoursModal={openHoursModal}
        />
      )}

      {activeTab === 'availability' && (
        <AvailabilityTab
          volunteers={volunteers}
          availableOnDate={availableOnDate}
          onAvailableDateChange={setAvailableOnDate}
        />
      )}

      {activeTab === 'hours' && (
        <HoursTab
          volunteers={volunteers}
          hoursVolunteerId={hoursVolunteerId}
          hoursDate={hoursDate}
          hoursCount={hoursCount}
          hoursActivityType={hoursActivityType}
          hoursNotes={hoursNotes}
          hoursData={hoursData}
          logHoursMutation={logHoursMutation}
          verifyHoursMutation={verifyHoursMutation}
          onHoursVolunteerIdChange={setHoursVolunteerId}
          onHoursDateChange={setHoursDate}
          onHoursCountChange={setHoursCount}
          onHoursActivityTypeChange={setHoursActivityType}
          onHoursNotesChange={setHoursNotes}
        />
      )}

      {showVolunteerDetail && selectedVolunteer && (
        <VolunteerDetailModal
          volunteer={selectedVolunteer}
          onClose={() => setShowVolunteerDetail(false)}
        />
      )}

      {showStatusModal && (
        <StatusUpdateModal
          newStatus={newStatus}
          bgCheckCompleted={bgCheckCompleted}
          bgCheckDate={bgCheckDate}
          bgCheckExpiry={bgCheckExpiry}
          trainingCompleted={trainingCompleted}
          trainingDate={trainingDate}
          updateStatusMutation={updateStatusMutation}
          onClose={() => setShowStatusModal(false)}
          onNewStatusChange={setNewStatus}
          onBgCheckCompletedChange={setBgCheckCompleted}
          onBgCheckDateChange={setBgCheckDate}
          onBgCheckExpiryChange={setBgCheckExpiry}
          onTrainingCompletedChange={setTrainingCompleted}
          onTrainingDateChange={setTrainingDate}
        />
      )}

      {showScheduleModal && scheduleVolunteerId && (
        <ScheduleModal
          scheduleVolunteerId={scheduleVolunteerId}
          scheduleDate={scheduleDate}
          scheduleIsAvailable={scheduleIsAvailable}
          scheduleStartTime={scheduleStartTime}
          scheduleEndTime={scheduleEndTime}
          scheduleData={scheduleData}
          createScheduleMutation={createScheduleMutation}
          deleteScheduleMutation={deleteScheduleMutation}
          onClose={() => setShowScheduleModal(false)}
          onScheduleDateChange={setScheduleDate}
          onScheduleIsAvailableChange={setScheduleIsAvailable}
          onScheduleStartTimeChange={setScheduleStartTime}
          onScheduleEndTimeChange={setScheduleEndTime}
        />
      )}

      {showHoursModal && hoursVolunteerId && (
        <HoursModal
          hoursVolunteerId={hoursVolunteerId}
          volunteers={volunteers}
          hoursData={hoursData}
          verifyHoursMutation={verifyHoursMutation}
          onClose={() => setShowHoursModal(false)}
        />
      )}
    </AdminShell>
  );
}
