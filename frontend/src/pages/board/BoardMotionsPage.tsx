/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useState, useMemo, useSyncExternalStore } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { API_BASE } from '@/api/types';
import {
  Gavel,
  FileText,
  Search,
  Filter,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Clock,
  MessageSquare,
  Pause,
  ArrowRight,
  Ban,
  AlertCircle,
} from "lucide-react";
import api from "../../api/api";
import { useTranslation, getCurrentLocale } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

interface BoardMotion {
  id: number;
  meeting_id: number;
  motion_type: string;
  motion_number: string;
  title: string;
  motion_text: string;
  plain_language_summary?: string;
  rationale?: string;
  moved_by_id: number;
  moved_by_name?: string;
  seconded_by_id?: number;
  seconded_by_name?: string;
  status: string;
  moved_at?: string;
  seconded_at?: string;
  tabled_reason?: string;
  referred_to_committee_name?: string;
  withdrawn_reason?: string;
  vote_id?: number;
  votes_for?: number;
  votes_against?: number;
  abstentions?: number;
  created_at: string;
  updated_at: string;
}

interface BoardMeeting {
  id: number;
  title: string;
  scheduled_date: string;
  meeting_type: string;
}

const statusLabels: Record<string, string> = {
  draft: "Draft",
  pending: "Pending Second",
  seconded: "Seconded",
  under_discussion: "Under Discussion",
  called_to_vote: "Called to Vote",
  passed: "Passed",
  failed: "Failed",
  tabled: "Tabled",
  referred: "Referred to Committee",
  withdrawn: "Withdrawn",
};

const statusColors: Record<string, string> = {
  draft: "bg-earth-100 text-earth-700 dark:bg-earth-700 dark:text-earth-300",
  pending: "bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-400",
  seconded: "bg-earth-100 text-lsc-rose dark:bg-earth-800/30 dark:text-lsc-rose-light",
  under_discussion: "bg-category-100 text-category-700 dark:bg-category-900/30 dark:text-category-400",
  called_to_vote: "bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-400",
  passed: "bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-400",
  failed: "bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-400",
  tabled: "bg-earth-100 text-earth-700 dark:bg-earth-700 dark:text-earth-300",
  referred: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400",
  withdrawn: "bg-earth-200 text-earth-600 dark:bg-earth-600 dark:text-earth-300",
};

const motionTypeLabels: Record<string, string> = {
  main: "Main Motion",
  amendment: "Amendment",
  subsidiary: "Subsidiary Motion",
  privileged: "Privileged Motion",
  incidental: "Incidental Motion",
};

function useDensity(): "compact" | "comfortable" | "spacious" {
  return useSyncExternalStore(
    (cb) => {
      const observer = new MutationObserver(cb);
      observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-density"] });
      return () => observer.disconnect();
    },
    () => (document.documentElement.dataset.density as "compact" | "comfortable" | "spacious") || "comfortable"
  );
}

const StatusIcon = ({ status }: { status: string }) => {
  switch (status) {
    case "passed":
      return <CheckCircle2 className="h-4 w-4" />;
    case "failed":
      return <XCircle className="h-4 w-4" />;
    case "pending":
    case "seconded":
      return <Clock className="h-4 w-4" />;
    case "under_discussion":
      return <MessageSquare className="h-4 w-4" />;
    case "tabled":
      return <Pause className="h-4 w-4" />;
    case "referred":
      return <ArrowRight className="h-4 w-4" />;
    case "withdrawn":
      return <Ban className="h-4 w-4" />;
    case "called_to_vote":
      return <Gavel className="h-4 w-4" />;
    default:
      return <FileText className="h-4 w-4" />;
  }
};

const outcomeStatuses = new Set(["passed", "failed", "tabled", "referred", "withdrawn"]);

const OutcomeBadge = ({ motion }: { motion: BoardMotion }) => {
  const status = motion.status;
  if (!outcomeStatuses.has(status)) return null;

  const badgeConfig: Record<string, { bg: string; icon: React.ReactNode; label: string }> = {
    passed: {
      bg: "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300 ring-1 ring-status-success-300 dark:ring-status-success-700",
      icon: <CheckCircle2 className="h-4 w-4" />,
      label: "Passed",
    },
    failed: {
      bg: "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300 ring-1 ring-status-danger-300 dark:ring-status-danger-700",
      icon: <XCircle className="h-4 w-4" />,
      label: "Failed",
    },
    tabled: {
      bg: "bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300 ring-1 ring-status-warning-300 dark:ring-status-warning-700",
      icon: <Pause className="h-4 w-4" />,
      label: "Tabled",
    },
    referred: {
      bg: "bg-indigo-100 dark:bg-indigo-900/30 text-indigo-800 dark:text-indigo-300 ring-1 ring-indigo-300 dark:ring-indigo-700",
      icon: <ArrowRight className="h-4 w-4" />,
      label: "Referred",
    },
    withdrawn: {
      bg: "bg-earth-200 dark:bg-earth-600 text-earth-700 dark:text-earth-200 ring-1 ring-earth-300 dark:ring-earth-500",
      icon: <Ban className="h-4 w-4" />,
      label: "Withdrawn",
    },
  };

  const config = badgeConfig[status];
  if (!config) return null;

  const voteText = formatVoteCounts(motion);

  return (
    <div
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold ${config.bg}`}
      aria-label={`Outcome: ${config.label}${voteText ? `, ${voteText}` : ""}`}
    >
      {config.icon}
      <span>{config.label}</span>
      {voteText && (
        <span className="text-xs font-normal opacity-80 ml-1">({voteText})</span>
      )}
    </div>
  );
};

const formatVoteCounts = (motion: BoardMotion): string => {
  if (motion.votes_for == null && motion.votes_against == null) return "";
  const f = motion.votes_for ?? 0;
  const a = motion.votes_against ?? 0;
  const ab = motion.abstentions ?? 0;
  let text = `${f}-${a}`;
  if (ab > 0) text += `, ${ab} abstention${ab !== 1 ? "s" : ""}`;
  return text;
};

export default function BoardMotionsPage() {
  const { t } = useTranslation()
  const density = useDensity();
  const [expandedMotions, setExpandedMotions] = useState<Set<number>>(new Set());
  const [searchParams, setSearchParams] = useSearchParams();
  const [motions, setMotions] = useState<BoardMotion[]>([]);
  const [meetings, setMeetings] = useState<BoardMeeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [searchQuery, setSearchQuery] = useState(searchParams.get("q") || "");
  const [statusFilter, setStatusFilter] = useState(searchParams.get("status") || "all");
  const [meetingFilter, setMeetingFilter] = useState(searchParams.get("meeting") || "all");
  const [typeFilter, setTypeFilter] = useState(searchParams.get("type") || "all");
  const [sortBy, setSortBy] = useState<"date" | "status" | "meeting">(
    (searchParams.get("sort") as "date" | "status" | "meeting") || "date"
  );


  useEffect(() => {
    const fetchData = async () => {
      try {
        const [meetingsData, motionsData] = await Promise.all([
          api.get(`${API_BASE}/board/meetings?limit=100`),
          api.get(`${API_BASE}/board/motions?include_all=true`),
        ]);
        const meetingsList = Array.isArray(meetingsData) ? meetingsData : (meetingsData.meetings || []);
        setMeetings(meetingsList);
        setMotions(Array.isArray(motionsData) ? motionsData : []);
      } catch (err: unknown) {
        Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
        setError("Unable to load motions. Please ensure you have the required permissions.");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Update URL params when filters change
  useEffect(() => {
    const params = new URLSearchParams();
    if (searchQuery) params.set("q", searchQuery);
    if (statusFilter !== "all") params.set("status", statusFilter);
    if (meetingFilter !== "all") params.set("meeting", meetingFilter);
    if (typeFilter !== "all") params.set("type", typeFilter);
    if (sortBy !== "date") params.set("sort", sortBy);
    setSearchParams(params, { replace: true });
  }, [searchQuery, statusFilter, meetingFilter, typeFilter, sortBy, setSearchParams]);

  // Filter and sort motions
  const toggleMotionExpanded = (id: number, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setExpandedMotions(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const filteredMotions = useMemo(() => {
    let result = [...motions];

    // Text search
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (m) =>
          m.title.toLowerCase().includes(query) ||
          m.motion_text.toLowerCase().includes(query) ||
          m.motion_number.toLowerCase().includes(query) ||
          (m.plain_language_summary && m.plain_language_summary.toLowerCase().includes(query))
      );
    }

    // Status filter
    if (statusFilter !== "all") {
      result = result.filter((m) => m.status === statusFilter);
    }

    // Meeting filter
    if (meetingFilter !== "all") {
      result = result.filter((m) => m.meeting_id === parseInt(meetingFilter));
    }

    // Type filter
    if (typeFilter !== "all") {
      result = result.filter((m) => m.motion_type === typeFilter);
    }

    // Sort
    result.sort((a, b) => {
      switch (sortBy) {
        case "status":
          return a.status.localeCompare(b.status);
        case "meeting":
          return a.meeting_id - b.meeting_id;
        case "date":
        default:
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
    });

    return result;
  }, [motions, searchQuery, statusFilter, meetingFilter, typeFilter, sortBy]);

  const getMeetingTitle = (meetingId: number) => {
    const meeting = meetings.find((m) => m.id === meetingId);
    return meeting ? meeting.title : `Meeting #${meetingId}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(getCurrentLocale(), {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  // Count motions by status for summary
  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    motions.forEach((m) => {
      counts[m.status] = (counts[m.status] || 0) + 1;
    });
    return counts;
  }, [motions]);

  if (loading) {
    return (
      <PageContainer className="py-8">
        <div className="motion-safe:animate-pulse space-y-4">
          <div className="h-8 bg-lsc-cream dark:bg-lsc-brown rounded w-1/3"></div>
          <div className="h-12 bg-lsc-cream dark:bg-lsc-brown rounded"></div>
          <div className="space-y-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-32 bg-lsc-cream dark:bg-lsc-brown rounded"></div>
            ))}
          </div>
        </div>
      </PageContainer>
    );
  }

  return (
    <>
    <PageContainer className="py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Gavel className="h-8 w-8 text-lsc-rose" />
          <h1 className="text-2xl font-bold text-earth-900 dark:text-earth-100">Board Motions</h1>
        </div>
      </div>

      {error ? (
        <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl p-6 mb-6">
          <div className="flex items-center gap-2 text-status-warning-700 dark:text-status-warning-300">
            <AlertCircle className="h-5 w-5" />
            <span>{error}</span>
          </div>
          <p className="text-sm text-status-warning-600 dark:text-status-warning-400 mt-2">
            Board members and staff can view motion details by logging in.
          </p>
        </div>
      ) : (
        <>
          {/* Summary Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow">
              <div className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{motions.length}</div>
              <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/80">Total Motions</div>
            </div>
            <div className="bg-status-success-50 dark:bg-status-success-900/20 rounded-xl p-4 shadow">
              <div className="text-2xl font-bold text-status-success-700 dark:text-status-success-400">{statusCounts.passed || 0}</div>
              <div className="text-sm text-status-success-600 dark:text-status-success-400">Passed</div>
            </div>
            <div className="bg-status-danger-50 dark:bg-status-danger-900/20 rounded-xl p-4 shadow">
              <div className="text-2xl font-bold text-status-danger-700 dark:text-status-danger-400">{statusCounts.failed || 0}</div>
              <div className="text-sm text-status-danger-600 dark:text-status-danger-400">Failed</div>
            </div>
            <div className="bg-status-warning-50 dark:bg-status-warning-900/20 rounded-xl p-4 shadow">
              <div className="text-2xl font-bold text-status-warning-700 dark:text-status-warning-400">
                {(statusCounts.pending || 0) + (statusCounts.seconded || 0) + (statusCounts.under_discussion || 0) + (statusCounts.called_to_vote || 0)}
              </div>
              <div className="text-sm text-status-warning-600 dark:text-status-warning-400">In Progress</div>
            </div>
            <div className="bg-earth-50 dark:bg-earth-800 rounded-xl p-4 shadow">
              <div className="text-2xl font-bold text-earth-700 dark:text-earth-300">{statusCounts.tabled || 0}</div>
              <div className="text-sm text-earth-600 dark:text-earth-300">Tabled</div>
            </div>
            <div className="bg-indigo-50 dark:bg-indigo-900/20 rounded-xl p-4 shadow">
              <div className="text-2xl font-bold text-indigo-700 dark:text-indigo-400">{statusCounts.referred || 0}</div>
              <div className="text-sm text-indigo-600 dark:text-indigo-400">Referred</div>
            </div>
          </div>

          {/* Filters */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-4 mb-6">
            <div className="flex flex-wrap gap-4" role="group" aria-label="Motion filters">
              {/* Search */}
              <div className="flex-1 min-w-[200px]">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-lsc-dark/70 dark:text-lsc-cream/50" />
                  <input
                    type="text"
                    placeholder={t('placeholder.boardMotions.searchMotions')}
                    aria-label={t('aria.boardMotions.searchMotions')}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream placeholder:text-lsc-dark/70 dark:placeholder:text-lsc-cream/50 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                  />
                </div>
              </div>

              {/* Status Filter */}
              <div className="flex items-center gap-2">
                <Filter className="h-4 w-4 text-lsc-dark/70 dark:text-lsc-cream/50" aria-hidden="true" />
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  aria-label="Filter by status"
                  className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                >
                  <option value="all">All Statuses</option>
                  {Object.entries(statusLabels).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Meeting Filter */}
              <select
                value={meetingFilter}
                onChange={(e) => setMeetingFilter(e.target.value)}
                aria-label="Filter by meeting"
                className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                <option value="all">All Meetings</option>
                {meetings.map((meeting) => (
                  <option key={meeting.id} value={meeting.id}>
                    {meeting.title} ({formatDate(meeting.scheduled_date)})
                  </option>
                ))}
              </select>

              {/* Type Filter */}
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                aria-label="Filter by motion type"
                className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                <option value="all">All Types</option>
                {Object.entries(motionTypeLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>

              {/* Sort */}
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as "date" | "status" | "meeting")}
                aria-label="Sort motions"
                className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                <option value="date">Sort by Date</option>
                <option value="status">Sort by Status</option>
                <option value="meeting">Sort by Meeting</option>
              </select>
            </div>
          </div>

          {/* Motions List */}
          {/* Screen reader announcement for filter results */}
          <div aria-live="polite" aria-atomic="true" className="sr-only">
            {!loading && `${filteredMotions.length} motion${filteredMotions.length === 1 ? '' : 's'} shown`}
          </div>

          {filteredMotions.length === 0 ? (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-12 text-center">
              <Gavel className="h-12 w-12 text-lsc-border mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">No Motions Found</h3>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/80">
                {searchQuery || statusFilter !== "all" || meetingFilter !== "all" || typeFilter !== "all"
                  ? "Try adjusting your filters to see more results."
                  : "No motions have been recorded yet."}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredMotions.map((motion) => (
                <Link
                  key={motion.id}
                  to={`/board/motions/${motion.id}`}
                  className="block bg-lsc-white dark:bg-earth-800 rounded-xl shadow hover:shadow-md transition-shadow"
                >
                  <div className={density === "compact" ? "p-4" : density === "spacious" ? "p-8" : "p-6"}>
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        {outcomeStatuses.has(motion.status) && (
                          <div className="mb-3">
                            <OutcomeBadge motion={motion} />
                          </div>
                        )}
                        <div className="flex items-center gap-3 mb-2 flex-wrap">
                          <span className="text-sm font-mono text-lsc-dark/70 dark:text-lsc-cream/70">
                            {motion.motion_number}
                          </span>
                          {!outcomeStatuses.has(motion.status) && (
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              statusColors[motion.status] || statusColors.draft
                            }`}
                            aria-label={`Status: ${statusLabels[motion.status] || motion.status}`}
                          >
                            <StatusIcon status={motion.status} />
                            {statusLabels[motion.status] || motion.status}
                          </span>
                          )}
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
                            {motionTypeLabels[motion.motion_type] || motion.motion_type}
                          </span>
                        </div>
                        <h3 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2" title={motion.title}>
                          {motion.title}
                        </h3>
                        {motion.plain_language_summary && (
                          <div className="mb-2">
                            <span className="text-xs font-medium uppercase tracking-wide text-lsc-dark/70 dark:text-lsc-cream/50">Plain Language</span>
                            <p className="text-base text-lsc-dark/80 dark:text-lsc-cream/90">
                              {motion.plain_language_summary}
                            </p>
                          </div>
                        )}
                        <p className={`text-sm text-lsc-dark/70 dark:text-lsc-cream/80 ${expandedMotions.has(motion.id) || density === "spacious" ? "" : density === "compact" ? "line-clamp-1" : "line-clamp-2"}`}>
                          {motion.motion_text}
                        </p>
                        {motion.motion_text && motion.motion_text.length > 120 && density !== "spacious" && (
                          <button
                            onClick={(e) => toggleMotionExpanded(motion.id, e)}
                            aria-expanded={expandedMotions.has(motion.id)}
                            className="text-xs text-lsc-rose dark:text-lsc-rose-light hover:underline mt-1 mb-2"
                          >
                            {expandedMotions.has(motion.id) ? "Show less" : "Show more"}
                          </button>
                        )}
                        <div className={`text-sm text-lsc-dark/70 dark:text-lsc-cream/70 ${density === "spacious" ? "flex flex-col gap-1" : "flex items-center gap-4 flex-wrap"}`}>
                          <span>Meeting: {getMeetingTitle(motion.meeting_id)}</span>
                          {motion.moved_by_name && <span>Moved by: {motion.moved_by_name}</span>}
                          {motion.seconded_by_name && <span>Seconded by: {motion.seconded_by_name}</span>}
                          <span>{formatDate(motion.created_at)}</span>
                        </div>
                      </div>
                      <ChevronRight className="h-5 w-5 text-lsc-dark/30 dark:text-lsc-cream/60 shrink-0 mt-2" />
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </>
      )}

      {/* Info Section */}
      <div className="mt-12 bg-lsc-cream dark:bg-earth-800 rounded-xl p-6">
        <section aria-label="About board motions">
        <h2 className="text-xl font-semibold mb-4 text-lsc-dark dark:text-lsc-cream">About Board Motions</h2>
        <div className="grid md:grid-cols-2 gap-6 text-sm text-lsc-dark/70 dark:text-lsc-cream/80">
          <div>
            <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">Motion Process</h3>
            <ol className="list-decimal list-inside space-y-1">
              <li>{t('boardMotions.aBoardMemberMovesProposes')}</li>
              <li>{t('boardMotions.anotherMemberSecondsTheMotion')}</li>
              <li>{t('boardMotions.theMotionIsOpenedFor')}</li>
              <li>{t('boardMotions.discussionIsClosedAndA')}</li>
              <li>{t('boardMotions.theOutcomePassedFailedIs')}</li>
            </ol>
          </div>
          <div>
            <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">Other Outcomes</h3>
            <ul className="list-disc list-inside space-y-1">
              <li><strong>Tabled:</strong> {t('boardMotions.postponedForLaterConsideration')}</li>
              <li><strong>Referred:</strong> {t('boardMotions.sentToACommitteeFor')}</li>
              <li><strong>Withdrawn:</strong> {t('boardMotions.removedByTheMoverBefore')}</li>
              <li><strong>Amended:</strong> Modified during discussion</li>
            </ul>
          </div>
        </div>
        </section>
      </div>
    </PageContainer>
  </>
  );
}