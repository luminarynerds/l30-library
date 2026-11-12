/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom';
import {
  Users,
  Truck,
  ClipboardList,
  MapPin,
  BarChart3,
  Clock,
  Plus,
  Package,
  Star,
  Heart,
  ExternalLink,
} from 'lucide-react';
import { useTranslation } from '@/i18n';
import type { HomeDeliveryReportSummary } from '../../api/homeDeliveryApi';

interface DashboardTabProps {
  summary: HomeDeliveryReportSummary;
  onScheduleDelivery: () => void;
  onCreateRoute: () => void;
  onReviewApplications: () => void;
}

export function DashboardTab({ summary, onScheduleDelivery, onCreateRoute, onReviewApplications }: DashboardTabProps) {
  const { t } = useTranslation();
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Active Patrons</p>
              <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">{summary.active_enrolled_patrons}</p>
            </div>
            <Users className="w-10 h-10 text-status-warning-500" />
          </div>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Pending Applications</p>
              <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">{summary.pending_applications}</p>
            </div>
            <ClipboardList className="w-10 h-10 text-status-warning-500" />
          </div>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Active Volunteers</p>
              <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">{summary.active_volunteers}</p>
            </div>
            <Heart className="w-10 h-10 text-status-danger-500" />
          </div>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Deliveries This Month</p>
              <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">{summary.total_deliveries_this_month}</p>
            </div>
            <Truck className="w-10 h-10 text-status-success-500" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
          <div className="flex items-center gap-3">
            <Package className="w-8 h-8 text-earth-600" />
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('homeDeliveryManagement.itemsDeliveredThisMonth')}</p>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{summary.total_items_delivered_this_month}</p>
            </div>
          </div>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
          <div className="flex items-center gap-3">
            <Star className="w-8 h-8 text-status-warning-500" />
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Average Rating</p>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                {summary.average_delivery_rating?.toFixed(1) || 'N/A'}
              </p>
            </div>
          </div>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
          <div className="flex items-center gap-3">
            <Clock className="w-8 h-8 text-category-500" />
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('homeDeliveryManagement.volunteerHoursThisMonth')}</p>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{summary.total_volunteer_hours_this_month.toFixed(1)}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
        <h3 className="font-serif text-lg font-semibold mb-4">Quick Actions</h3>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={onReviewApplications}
            className="flex items-center gap-2 px-4 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700"
          >
            <ClipboardList className="w-4 h-4" />
            Review Applications
          </button>
          <button
            onClick={onScheduleDelivery}
            className="flex items-center gap-2 px-4 py-2 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700"
          >
            <Plus className="w-4 h-4" />
            Schedule Delivery
          </button>
          <button
            onClick={onCreateRoute}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90"
          >
            <MapPin className="w-4 h-4" />
            Create Route
          </button>
        </div>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
        <h3 className="font-serif text-lg font-semibold mb-4">Dedicated Management Pages</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            to="/staff/home-delivery/deliveries"
            className="flex items-center justify-between p-4 border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 transition-colors"
          >
            <div className="flex items-center gap-3">
              <Truck className="w-5 h-5 text-status-warning-600" />
              <div>
                <p className="font-medium text-lsc-dark dark:text-lsc-cream">Delivery Management</p>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('homeDeliveryManagement.dayScheduleRoutesTracking')}</p>
              </div>
            </div>
            <ExternalLink className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
          </Link>
          <Link
            to="/staff/home-delivery/volunteers"
            className="flex items-center justify-between p-4 border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 transition-colors"
          >
            <div className="flex items-center gap-3">
              <Heart className="w-5 h-5 text-status-warning-600" />
              <div>
                <p className="font-medium text-lsc-dark dark:text-lsc-cream">Volunteer Coordination</p>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Roster, schedules, hours</p>
              </div>
            </div>
            <ExternalLink className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
          </Link>
          <Link
            to="/staff/home-delivery/reports"
            className="flex items-center justify-between p-4 border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 transition-colors"
          >
            <div className="flex items-center gap-3">
              <BarChart3 className="w-5 h-5 text-status-warning-600" />
              <div>
                <p className="font-medium text-lsc-dark dark:text-lsc-cream">Reports & Analytics</p>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Stats, satisfaction, exports</p>
              </div>
            </div>
            <ExternalLink className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
          </Link>
        </div>
      </div>
    </div>
  );
}
