/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../contexts/AuthContext';
import { AdminShell } from '../components/shells/AdminShell';
import { Truck, RefreshCw, Plus, Loader2, Route, Calendar } from 'lucide-react';
import toast from 'react-hot-toast';
import {
  listDeliveries,
  createDelivery,
  updateDeliveryStatus,
  listRoutes,
  createRoute,
  assignDeliveriesToRoute,
  optimizeRoute,
  updateRouteStatus,
  listEnrollments,
  listVolunteers,
  DeliveryStatus,
  RouteStatus,
  Delivery,
  DeliveryRoute,
} from '../api/homeDeliveryApi';
import { useTranslation } from '@/i18n';
import { ScheduleTab } from '../components/delivery/ScheduleTab';
import { AllDeliveriesTab } from '../components/delivery/AllDeliveriesTab';
import { RoutesTabFull } from '../components/delivery/RoutesTabFull';
import { CreateDeliveryModalFull } from '../components/delivery/CreateDeliveryModalFull';
import { CreateRouteModalFull } from '../components/delivery/CreateRouteModalFull';
import { DeliveryDetailModal } from '../components/delivery/DeliveryDetailModal';

type Tab = 'schedule' | 'deliveries' | 'routes';

export default function HomeDeliveryDeliveryPage(): React.ReactElement {
  const { t } = useTranslation();
  const { user, token, isLoading: authLoading } = useAuth();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<Tab>('schedule');
  const [searchQuery, setSearchQuery] = useState('');
  const [deliveryStatusFilter, setDeliveryStatusFilter] = useState<DeliveryStatus | ''>('');
  const [routeStatusFilter, setRouteStatusFilter] = useState<RouteStatus | ''>('');
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0] ?? '');

  const [showCreateDeliveryModal, setShowCreateDeliveryModal] = useState(false);
  const [showCreateRouteModal, setShowCreateRouteModal] = useState(false);
  const [showDeliveryDetailModal, setShowDeliveryDetailModal] = useState(false);
  const [_showRouteDetailModal, setShowRouteDetailModal] = useState(false);
  const [selectedDelivery, setSelectedDelivery] = useState<Delivery | null>(null);
  const [_selectedRoute, setSelectedRoute] = useState<DeliveryRoute | null>(null);

  const [newDeliveryEnrollmentId, setNewDeliveryEnrollmentId] = useState<number | null>(null);
  const [newDeliveryDate, setNewDeliveryDate] = useState('');
  const [newDeliveryTimeStart, setNewDeliveryTimeStart] = useState('');
  const [newDeliveryTimeEnd, setNewDeliveryTimeEnd] = useState('');
  const [newDeliveryRouteId, setNewDeliveryRouteId] = useState<number | null>(null);
  const [newDeliveryNotes, setNewDeliveryNotes] = useState('');

  const [newRouteName, setNewRouteName] = useState('');
  const [newRouteDate, setNewRouteDate] = useState('');
  const [newRouteVolunteerId, setNewRouteVolunteerId] = useState<number | null>(null);
  const [newRoutePlannedStart, setNewRoutePlannedStart] = useState('');
  const [newRoutePlannedEnd, setNewRoutePlannedEnd] = useState('');
  const [newRouteNotes, setNewRouteNotes] = useState('');

  const [selectedDeliveryIds, setSelectedDeliveryIds] = useState<number[]>([]);

  const { data: deliveriesData, isLoading: deliveriesLoading, refetch: refetchDeliveries } = useQuery({
    queryKey: ['home-delivery-deliveries', deliveryStatusFilter, searchQuery],
    queryFn: () => listDeliveries({
      ...(deliveryStatusFilter ? { status: deliveryStatusFilter } : {}),
      ...(searchQuery ? { search: searchQuery } : {}),
      limit: 200,
    }),
    enabled: !!token,
  });

  const { data: routesData, isLoading: routesLoading, refetch: refetchRoutes } = useQuery({
    queryKey: ['home-delivery-routes', routeStatusFilter],
    queryFn: () => listRoutes({
      ...(routeStatusFilter ? { status: routeStatusFilter } : {}),
      limit: 100,
    }),
    enabled: !!token,
  });

  const { data: enrollmentsData } = useQuery({
    queryKey: ['home-delivery-enrollments-active'],
    queryFn: () => listEnrollments({ status: 'active', limit: 200 }),
    enabled: !!token,
  });

  const { data: volunteersData } = useQuery({
    queryKey: ['home-delivery-volunteers-active'],
    queryFn: () => listVolunteers({ status: 'active', limit: 100 }),
    enabled: !!token,
  });

  const createDeliveryMutation = useMutation({
    mutationFn: () => createDelivery({
      enrollment_id: newDeliveryEnrollmentId!,
      scheduled_date: newDeliveryDate,
      ...(newDeliveryTimeStart ? { scheduled_time_start: newDeliveryTimeStart } : {}),
      ...(newDeliveryTimeEnd ? { scheduled_time_end: newDeliveryTimeEnd } : {}),
      ...(newDeliveryRouteId ? { route_id: newDeliveryRouteId } : {}),
      ...(newDeliveryNotes ? { staff_notes: newDeliveryNotes } : {}),
    }),
    onSuccess: () => {
      toast.success(t('toast.homeDelivery.deliveryScheduledSuccessfully'));
      queryClient.invalidateQueries({ queryKey: ['home-delivery-deliveries'] });
      setShowCreateDeliveryModal(false);
      setNewDeliveryEnrollmentId(null);
      setNewDeliveryDate('');
      setNewDeliveryTimeStart('');
      setNewDeliveryTimeEnd('');
      setNewDeliveryRouteId(null);
      setNewDeliveryNotes('');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const updateDeliveryStatusMutation = useMutation({
    mutationFn: ({ id, status, failureReason }: { id: number; status: DeliveryStatus; failureReason?: string }) =>
      updateDeliveryStatus(id, { status, ...(failureReason ? { failure_reason: failureReason } : {}) }),
    onSuccess: () => {
      toast.success(t('toast.homeDelivery.deliveryStatusUpdated'));
      queryClient.invalidateQueries({ queryKey: ['home-delivery-deliveries'] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const createRouteMutation = useMutation({
    mutationFn: () => createRoute({
      name: newRouteName,
      date: newRouteDate,
      ...(newRouteVolunteerId ? { volunteer_id: newRouteVolunteerId } : {}),
      ...(newRoutePlannedStart ? { planned_start_time: newRoutePlannedStart } : {}),
      ...(newRoutePlannedEnd ? { planned_end_time: newRoutePlannedEnd } : {}),
      ...(newRouteNotes ? { notes: newRouteNotes } : {}),
    }),
    onSuccess: () => {
      toast.success(t('toast.homeDeliveryManagement.routeCreated'));
      queryClient.invalidateQueries({ queryKey: ['home-delivery-routes'] });
      setShowCreateRouteModal(false);
      setNewRouteName('');
      setNewRouteDate('');
      setNewRouteVolunteerId(null);
      setNewRoutePlannedStart('');
      setNewRoutePlannedEnd('');
      setNewRouteNotes('');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const optimizeRouteMutation = useMutation({
    mutationFn: (routeId: number) => optimizeRoute(routeId),
    onSuccess: () => {
      toast.success(t('toast.homeDelivery.routeOptimized'));
      queryClient.invalidateQueries({ queryKey: ['home-delivery-routes'] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const updateRouteStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: RouteStatus }) =>
      updateRouteStatus(id, { status }),
    onSuccess: () => {
      toast.success(t('toast.homeDelivery.routeStatusUpdated'));
      queryClient.invalidateQueries({ queryKey: ['home-delivery-routes'] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const assignDeliveriesMutation = useMutation({
    mutationFn: ({ routeId, deliveryIds }: { routeId: number; deliveryIds: number[] }) =>
      assignDeliveriesToRoute(routeId, deliveryIds),
    onSuccess: () => {
      toast.success(t('homeDelivery.deliveriesAssignedToRoute'));
      queryClient.invalidateQueries({ queryKey: ['home-delivery-deliveries'] });
      queryClient.invalidateQueries({ queryKey: ['home-delivery-routes'] });
      setSelectedDeliveryIds([]);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const handleAdvanceStatus = (delivery: Delivery) => {
    const nextStatusMap: Partial<Record<DeliveryStatus, DeliveryStatus>> = {
      scheduled: 'items_selected',
      items_selected: 'packed',
      packed: 'out_for_delivery',
      out_for_delivery: 'delivered',
    };
    const nextStatus = nextStatusMap[delivery.status];
    if (nextStatus) {
      updateDeliveryStatusMutation.mutate({ id: delivery.id, status: nextStatus });
    }
  };

  const toggleDeliverySelection = (id: number) => {
    setSelectedDeliveryIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
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
    { id: 'schedule', label: 'Day Schedule', icon: <Calendar className="w-4 h-4" /> },
    { id: 'deliveries', label: 'All Deliveries', icon: <Truck className="w-4 h-4" /> },
    { id: 'routes', label: 'Routes', icon: <Route className="w-4 h-4" /> },
  ];

  return (
    <AdminShell title="Home Delivery">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-lsc-cream dark:bg-earth-800/30 rounded-xl">
            <Truck className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Delivery Management
            </h1>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Schedule, track, and manage home deliveries
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => { refetchDeliveries(); refetchRoutes(); }}
            className="flex items-center gap-2 px-3 py-2 text-sm bg-lsc-cream dark:bg-earth-800 hover:bg-lsc-border dark:hover:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowCreateDeliveryModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg text-sm font-medium"
          >
            <Plus className="w-4 h-4" /> Schedule Delivery
          </button>
        </div>
      </div>

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

      {activeTab === 'schedule' && (
        <ScheduleTab
          selectedDate={selectedDate}
          onDateChange={setSelectedDate}
          deliveries={deliveriesData?.deliveries ?? []}
          loading={deliveriesLoading}
          onViewDelivery={(d) => { setSelectedDelivery(d); setShowDeliveryDetailModal(true); }}
          onAdvanceStatus={handleAdvanceStatus}
          onScheduleForDate={(date) => { setNewDeliveryDate(date); setShowCreateDeliveryModal(true); }}
          isAdvancing={updateDeliveryStatusMutation.isPending}
        />
      )}

      {activeTab === 'deliveries' && (
        <AllDeliveriesTab
          deliveries={deliveriesData?.deliveries ?? []}
          loading={deliveriesLoading}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          statusFilter={deliveryStatusFilter}
          onStatusFilterChange={setDeliveryStatusFilter}
          selectedDeliveryIds={selectedDeliveryIds}
          onToggleSelection={toggleDeliverySelection}
          routes={routesData?.routes ?? []}
          onAssignToRoute={(routeId) => assignDeliveriesMutation.mutate({ routeId, deliveryIds: selectedDeliveryIds })}
          onViewDelivery={(d) => { setSelectedDelivery(d); setShowDeliveryDetailModal(true); }}
          onUpdateStatus={(id, status) => updateDeliveryStatusMutation.mutate({ id, status })}
          onUpdateStatusWithReason={(id, status) => {
            const reason = prompt('Enter failure reason:');
            if (reason !== null) {
              updateDeliveryStatusMutation.mutate({ id, status, failureReason: reason });
            }
          }}
        />
      )}

      {activeTab === 'routes' && (
        <RoutesTabFull
          routes={routesData?.routes ?? []}
          loading={routesLoading}
          statusFilter={routeStatusFilter}
          onStatusFilterChange={setRouteStatusFilter}
          onCreateRoute={() => setShowCreateRouteModal(true)}
          onViewRoute={(r) => { setSelectedRoute(r); setShowRouteDetailModal(true); }}
          onOptimizeRoute={(id) => optimizeRouteMutation.mutate(id)}
          onUpdateRouteStatus={(id, status) => updateRouteStatusMutation.mutate({ id, status })}
          isOptimizing={optimizeRouteMutation.isPending}
          isUpdating={updateRouteStatusMutation.isPending}
        />
      )}

      {showCreateDeliveryModal && (
        <CreateDeliveryModalFull
          enrollmentId={newDeliveryEnrollmentId}
          onEnrollmentChange={setNewDeliveryEnrollmentId}
          date={newDeliveryDate}
          onDateChange={setNewDeliveryDate}
          timeStart={newDeliveryTimeStart}
          onTimeStartChange={setNewDeliveryTimeStart}
          timeEnd={newDeliveryTimeEnd}
          onTimeEndChange={setNewDeliveryTimeEnd}
          routeId={newDeliveryRouteId}
          onRouteChange={setNewDeliveryRouteId}
          notes={newDeliveryNotes}
          onNotesChange={setNewDeliveryNotes}
          enrollments={enrollmentsData?.enrollments ?? []}
          routes={routesData?.routes ?? []}
          onSubmit={() => {
            if (!newDeliveryEnrollmentId || !newDeliveryDate) {
              toast.error(t('homeDelivery.pleaseSelectAPatronAnd'));
              return;
            }
            createDeliveryMutation.mutate();
          }}
          onClose={() => setShowCreateDeliveryModal(false)}
          isPending={createDeliveryMutation.isPending}
        />
      )}

      {showCreateRouteModal && (
        <CreateRouteModalFull
          name={newRouteName}
          onNameChange={setNewRouteName}
          date={newRouteDate}
          onDateChange={setNewRouteDate}
          volunteerId={newRouteVolunteerId}
          onVolunteerChange={setNewRouteVolunteerId}
          plannedStart={newRoutePlannedStart}
          onPlannedStartChange={setNewRoutePlannedStart}
          plannedEnd={newRoutePlannedEnd}
          onPlannedEndChange={setNewRoutePlannedEnd}
          notes={newRouteNotes}
          onNotesChange={setNewRouteNotes}
          volunteers={volunteersData?.volunteers ?? []}
          onSubmit={() => {
            if (!newRouteName || !newRouteDate) {
              toast.error(t('homeDelivery.pleaseEnterARouteName'));
              return;
            }
            createRouteMutation.mutate();
          }}
          onClose={() => setShowCreateRouteModal(false)}
          isPending={createRouteMutation.isPending}
        />
      )}

      {showDeliveryDetailModal && selectedDelivery && (
        <DeliveryDetailModal
          delivery={selectedDelivery}
          onClose={() => setShowDeliveryDetailModal(false)}
        />
      )}
    </AdminShell>
  );
}
