import { getCurrentLocale } from '@/i18n'
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  Loader2,
  History,
  Filter,
  ChevronLeft,
  ChevronRight,
  Clock,
  BookOpen,
  Undo2,
  RefreshCcw,
  DollarSign,
  CheckCircle,
  XCircle,
  Bookmark,
  Ban,
  Activity,
  User,
  UserPlus,
  Edit3,
} from "lucide-react"
import {
  PatronActivityListResponse,
  PatronActivityType,
} from "../../../api/staff-api"

interface PatronHistoryTabProps {
  activityData: PatronActivityListResponse | null
  isLoading: boolean
  currentPage: number
  perPage: number
  activityTypeFilter: PatronActivityType | ""
  onPageChange: (page: number) => void
  onActivityTypeFilterChange: (type: PatronActivityType | "") => void
}

export function PatronHistoryTab({
  activityData,
  isLoading,
  currentPage,
  perPage,
  activityTypeFilter,
  onPageChange,
  onActivityTypeFilterChange,
}: PatronHistoryTabProps) {
  const getActivityIcon = (activityType: PatronActivityType) => {
    switch (activityType) {
      case "checkout":
        return <BookOpen aria-hidden="true" className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
      case "return":
        return <Undo2 aria-hidden="true" className="w-4 h-4 text-status-success-600 dark:text-status-success-400" />
      case "renewal":
        return <RefreshCcw aria-hidden="true" className="w-4 h-4 text-category-600 dark:text-category-400" />
      case "fine_created":
        return <DollarSign aria-hidden="true" className="w-4 h-4 text-status-danger-600 dark:text-status-danger-400" />
      case "fine_paid":
        return <CheckCircle aria-hidden="true" className="w-4 h-4 text-status-success-600 dark:text-status-success-400" />
      case "fine_waived":
        return <XCircle aria-hidden="true" className="w-4 h-4 text-status-warning-600 dark:text-status-warning-400" />
      case "hold_placed":
        return <Bookmark aria-hidden="true" className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
      case "hold_fulfilled":
        return <CheckCircle aria-hidden="true" className="w-4 h-4 text-status-success-600 dark:text-status-success-400" />
      case "hold_cancelled":
        return <XCircle aria-hidden="true" className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
      case "hold_expired":
        return <Clock aria-hidden="true" className="w-4 h-4 text-status-warning-600 dark:text-status-warning-400" />
      case "account_blocked":
        return <Ban aria-hidden="true" className="w-4 h-4 text-status-danger-600 dark:text-status-danger-400" />
      case "account_unblocked":
        return <CheckCircle aria-hidden="true" className="w-4 h-4 text-status-success-600 dark:text-status-success-400" />
      case "account_created":
        return <UserPlus aria-hidden="true" className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
      case "profile_updated":
        return <Edit3 aria-hidden="true" className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
      default:
        return <Activity aria-hidden="true" className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
    }
  }

  const getBgColor = (activityType: PatronActivityType) => {
    switch (activityType) {
      case "checkout":
      case "hold_placed":
      case "account_created":
        return "bg-earth-100 dark:bg-earth-800/30"
      case "return":
      case "fine_paid":
      case "hold_fulfilled":
      case "account_unblocked":
        return "bg-status-success-100 dark:bg-status-success-900/30"
      case "fine_created":
      case "account_blocked":
        return "bg-status-danger-100 dark:bg-status-danger-900/30"
      case "fine_waived":
        return "bg-status-warning-100 dark:bg-status-warning-900/30"
      case "renewal":
        return "bg-category-100 dark:bg-category-900/30"
      case "hold_expired":
        return "bg-status-warning-100 dark:bg-status-warning-900/30"
      default:
        return "bg-earth-100 dark:bg-earth-800"
    }
  }

  return (
    <div>
      {/* Header with filter */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          Activity History
          {activityData && (
            <span className="ml-2 text-sm font-normal text-lsc-dark/70 dark:text-lsc-cream/70">
              ({activityData.total} total)
            </span>
          )}
        </h3>
        <div className="flex items-center gap-2">
          <Filter aria-hidden="true" className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <select
            value={activityTypeFilter}
            onChange={(e) => onActivityTypeFilterChange(e.target.value as PatronActivityType | "")}
            className="text-sm border border-lsc-border dark:border-earth-700 rounded-lg px-2 py-1 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose"
          >
            <option value="">All Activities</option>
            <option value="checkout">Checkouts</option>
            <option value="return">Returns</option>
            <option value="renewal">Renewals</option>
            <option value="fine_created">Fines Created</option>
            <option value="fine_paid">Fines Paid</option>
            <option value="fine_waived">Fines Waived</option>
            <option value="hold_placed">Holds Placed</option>
            <option value="hold_fulfilled">Holds Fulfilled</option>
            <option value="hold_cancelled">Holds Cancelled</option>
            <option value="hold_expired">Holds Expired</option>
            <option value="account_blocked">Account Blocked</option>
            <option value="account_unblocked">Account Unblocked</option>
            <option value="account_created">Account Created</option>
            <option value="profile_updated">Profile Updated</option>
          </select>
        </div>
      </div>

      {/* Loading state */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
        </div>
      ) : !activityData || activityData.activities.length === 0 ? (
        /* Empty state */
        <div className="text-center py-8">
          <History aria-hidden="true" className="w-12 h-12 text-lsc-border dark:text-lsc-cream/70 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No activity found</p>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            {activityTypeFilter ? "Try changing the filter" : "This patron has no recorded activity"}
          </p>
        </div>
      ) : (
        <>
          {/* Activity timeline */}
          <div className="space-y-3">
            {activityData.activities.map((activity) => (
              <div
                key={activity.id}
                className="flex items-start gap-3 p-3 rounded-lg border border-lsc-border/50 dark:border-earth-700/50 hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 transition-colors"
              >
                {/* Icon */}
                <div className={`p-2 rounded-full ${getBgColor(activity.activity_type)}`}>
                  {getActivityIcon(activity.activity_type)}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-lsc-dark dark:text-lsc-cream">
                    {activity.description}
                  </p>
                  {(activity.item_title || activity.item_author) && (
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
                      {activity.item_title}
                      {activity.item_author && (
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                          {" "}by {activity.item_author}
                        </span>
                      )}
                    </p>
                  )}
                  {activity.fine_amount && (
                    <p className="text-sm font-medium text-lsc-rose dark:text-lsc-rose-light mt-0.5">
                      ${activity.fine_amount}
                    </p>
                  )}
                  <div className="flex items-center gap-2 mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    <Clock aria-hidden="true" className="w-3 h-3" />
                    <span>
                      {new Date(activity.created_at).toLocaleDateString(getCurrentLocale(), {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                    {activity.staff_name && (
                      <>
                        <span className="text-lsc-dark/30 dark:text-lsc-cream/60">|</span>
                        <User aria-hidden="true" className="w-3 h-3" />
                        <span>{activity.staff_name}</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {activityData.total > perPage && (
            <div className="mt-4 pt-4 border-t border-lsc-border dark:border-earth-700 flex items-center justify-between">
              <button
                onClick={() => onPageChange(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="flex items-center gap-1 px-3 py-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft aria-hidden="true" className="w-4 h-4" />
                Prev
              </button>
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Page {currentPage} of {Math.ceil(activityData.total / perPage)}
              </span>
              <button
                onClick={() => onPageChange(currentPage + 1)}
                disabled={!activityData.has_more}
                className="flex items-center gap-1 px-3 py-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
                <ChevronRight aria-hidden="true" className="w-4 h-4" />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
