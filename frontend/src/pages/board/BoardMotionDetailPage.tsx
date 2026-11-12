/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { API_BASE } from '@/api/types';
import {
  Gavel,
  ChevronLeft,
  User,
  Calendar,
  Clock,
  CheckCircle2,
  XCircle,
  MessageSquare,
  Pause,
  ArrowRight,
  Ban,
  FileText,
  AlertCircle,
  Building2,
  History,
} from "lucide-react";
import api from "../../api/api";
import { clean } from '@/lib/utils';
import PageContainer from '@/components/layout/PageContainer'
import { getCurrentLocale } from '@/i18n'

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
  parent_motion_id?: number;
  amended_text?: string;
  status: string;
  moved_at?: string;
  seconded_at?: string;
  discussion_opened_at?: string;
  discussion_closed_at?: string;
  discussion_notes?: string;
  vote_called_at?: string;
  vote_id?: number;
  outcome_recorded_at?: string;
  outcome_notes?: string;
  tabled_at?: string;
  tabled_until?: string;
  tabled_reason?: string;
  referred_to_committee_id?: number;
  referred_to_committee_name?: string;
  referred_at?: string;
  referred_notes?: string;
  withdrawn_at?: string;
  withdrawn_reason?: string;
  created_by_id: number;
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
  referred: "bg-lsc-rose/10 text-lsc-rose dark:bg-lsc-rose/20 dark:text-lsc-rose-light",
  withdrawn: "bg-earth-200 text-earth-600 dark:bg-earth-600 dark:text-earth-300",
};

const motionTypeLabels: Record<string, string> = {
  main: "Main Motion",
  amendment: "Amendment",
  subsidiary: "Subsidiary Motion",
  privileged: "Privileged Motion",
  incidental: "Incidental Motion",
};

const StatusIcon = ({ status, className = "h-5 w-5" }: { status: string; className?: string }) => {
  switch (status) {
    case "passed":
      return <CheckCircle2 className={className} />;
    case "failed":
      return <XCircle className={className} />;
    case "pending":
    case "seconded":
      return <Clock className={className} />;
    case "under_discussion":
      return <MessageSquare className={className} />;
    case "tabled":
      return <Pause className={className} />;
    case "referred":
      return <ArrowRight className={className} />;
    case "withdrawn":
      return <Ban className={className} />;
    case "called_to_vote":
      return <Gavel className={className} />;
    default:
      return <FileText className={className} />;
  }
};

// Timeline step type
interface TimelineStep {
  label: string;
  timestamp?: string;
  icon: React.ReactNode;
  completed: boolean;
  active: boolean;
  details?: string;
}

export default function BoardMotionDetailPage() {
  const { motionId } = useParams();
  const [motion, setMotion] = useState<BoardMotion | null>(null);
  const [meeting, setMeeting] = useState<BoardMeeting | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const targetId = parseInt(motionId || "0");
        const foundMotion = await api.get(`${API_BASE}/board/motions/${targetId}`) as BoardMotion;

        setMotion(foundMotion);

        const meetingData = await api.get(`${API_BASE}/board/meetings/${foundMotion.meeting_id}`);
        setMeeting(meetingData as BoardMeeting);
      } catch (err: unknown) {
        Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
        setError("Unable to load motion details. Please ensure you have the required permissions.");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [motionId]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(getCurrentLocale(), {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  const formatDateTime = (dateString?: string) => {
    if (!dateString) return null;
    return new Date(dateString).toLocaleString(getCurrentLocale(), {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  };

  // Build timeline steps based on motion status
  const buildTimeline = (m: BoardMotion): TimelineStep[] => {
    const steps: TimelineStep[] = [];
    const statusOrder = ["pending", "seconded", "under_discussion", "called_to_vote"];
    const currentIndex = statusOrder.indexOf(m.status);

    // Moved
    steps.push(clean({
      label: "Motion Moved",
      timestamp: m.moved_at || m.created_at,
      icon: <Gavel className="h-4 w-4" />,
      completed: true,
      active: m.status === "pending",
      details: m.moved_by_name ? `By ${m.moved_by_name}` : undefined,
    }));

    // Seconded
    steps.push(clean({
      label: "Motion Seconded",
      timestamp: m.seconded_at,
      icon: <User className="h-4 w-4" />,
      completed: currentIndex >= 1 || ["passed", "failed"].includes(m.status),
      active: m.status === "seconded",
      details: m.seconded_by_name ? `By ${m.seconded_by_name}` : undefined,
    }));

    // Discussion
    steps.push(clean({
      label: "Under Discussion",
      timestamp: m.discussion_opened_at,
      icon: <MessageSquare className="h-4 w-4" />,
      completed: currentIndex >= 3 || ["passed", "failed"].includes(m.status),
      active: m.status === "under_discussion",
      details: m.discussion_closed_at ? `Closed ${formatDateTime(m.discussion_closed_at)}` : undefined,
    }));

    // Vote Called
    steps.push(clean({
      label: "Vote Called",
      timestamp: m.vote_called_at,
      icon: <Gavel className="h-4 w-4" />,
      completed: ["passed", "failed"].includes(m.status),
      active: m.status === "called_to_vote",
    }));

    // Outcome
    if (m.status === "passed" || m.status === "failed") {
      steps.push(clean({
        label: m.status === "passed" ? "Motion Passed" : "Motion Failed",
        timestamp: m.outcome_recorded_at,
        icon: m.status === "passed" ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />,
        completed: true,
        active: true,
        details: m.outcome_notes,
      }));
    }

    // Special outcomes
    if (m.status === "tabled") {
      steps.push(clean({
        label: "Motion Tabled",
        timestamp: m.tabled_at,
        icon: <Pause className="h-4 w-4" />,
        completed: true,
        active: true,
        details: m.tabled_reason || (m.tabled_until ? `Until ${formatDate(m.tabled_until)}` : undefined),
      }));
    }

    if (m.status === "referred") {
      steps.push(clean({
        label: "Referred to Committee",
        timestamp: m.referred_at,
        icon: <Building2 className="h-4 w-4" />,
        completed: true,
        active: true,
        details: m.referred_to_committee_name || m.referred_notes,
      }));
    }

    if (m.status === "withdrawn") {
      steps.push(clean({
        label: "Motion Withdrawn",
        timestamp: m.withdrawn_at,
        icon: <Ban className="h-4 w-4" />,
        completed: true,
        active: true,
        details: m.withdrawn_reason,
      }));
    }

    return steps;
  };

  if (loading) {
    return (
      <PageContainer className="py-8">
        <div className="motion-safe:animate-pulse space-y-4">
          <div className="h-6 bg-lsc-cream dark:bg-lsc-brown rounded w-32"></div>
          <div className="h-10 bg-lsc-cream dark:bg-lsc-brown rounded w-2/3"></div>
          <div className="h-64 bg-lsc-cream dark:bg-lsc-brown rounded"></div>
        </div>
      </PageContainer>
    );
  }

  if (error || !motion) {
    return (
      <PageContainer className="py-8">
        <Link to="/board/motions" className="flex items-center gap-2 text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream hover:underline mb-4">
          <ChevronLeft className="h-4 w-4" /> Back to Motions
        </Link>
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-6">
          <div className="flex items-center gap-2 text-status-danger-700 dark:text-status-danger-300">
            <AlertCircle className="h-5 w-5" />
            <span>{error || "Motion not found"}</span>
          </div>
        </div>
      </PageContainer>
    );
  }

  const timeline = buildTimeline(motion);

  return (
    <>
    <PageContainer className="py-8">
      <Link to="/board/motions" className="flex items-center gap-2 text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream hover:underline mb-4">
        <ChevronLeft className="h-4 w-4" /> Back to Motions
      </Link>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Motion Header */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
            <div className="flex items-start justify-between gap-4 mb-4 flex-wrap">
              <div>
                <div className="flex items-center gap-3 mb-2 flex-wrap">
                  <span className="text-sm font-mono text-lsc-dark/70 dark:text-lsc-cream/70">
                    {motion.motion_number}
                  </span>
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
                    {motionTypeLabels[motion.motion_type] || motion.motion_type}
                  </span>
                </div>
                <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">{motion.title}</h1>
              </div>
              <span
                className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${
                  statusColors[motion.status] || statusColors.draft
                }`}
              >
                <StatusIcon status={motion.status} className="h-4 w-4" />
                {statusLabels[motion.status] || motion.status}
              </span>
            </div>

            {meeting && (
              <Link
                to={`/board/meetings/${meeting.id}`}
                className="inline-flex items-center gap-2 text-sm text-lsc-rose hover:underline mb-4"
              >
                <Calendar className="h-4 w-4" />
                {meeting.title} - {formatDate(meeting.scheduled_date)}
              </Link>
            )}
          </div>

          {/* Plain Language Summary */}
          {motion.plain_language_summary && (
            <div className="bg-lsc-cream dark:bg-earth-700 rounded-xl p-4 border-l-4 border-lsc-rose">
              <h2 className="text-sm font-medium uppercase tracking-wide text-lsc-dark/70 dark:text-lsc-cream/60 mb-2">What This Means</h2>
              <p className="text-base text-lsc-dark/90 dark:text-lsc-cream/90">
                {motion.plain_language_summary}
              </p>
            </div>
          )}

          {/* Motion Text */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Motion Text</h2>
            <div className="prose dark:prose-invert max-w-none">
              <p className="text-lsc-dark/80 dark:text-lsc-cream/80 whitespace-pre-wrap">
                {motion.motion_text}
              </p>
            </div>

            {motion.amended_text && (
              <div className="mt-6 pt-6 border-t border-lsc-border dark:border-earth-700">
                <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">Amended Text</h3>
                <p className="text-lsc-dark/80 dark:text-lsc-cream/80 whitespace-pre-wrap bg-status-warning-50 dark:bg-status-warning-900/20 p-4 rounded-lg">
                  {motion.amended_text}
                </p>
              </div>
            )}

            {motion.rationale && (
              <div className="mt-6 pt-6 border-t border-lsc-border dark:border-earth-700">
                <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">Rationale</h3>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-pre-wrap">
                  {motion.rationale}
                </p>
              </div>
            )}
          </div>

          {/* Discussion Notes */}
          {motion.discussion_notes && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                Discussion Notes
              </h2>
              <p className="text-lsc-dark/80 dark:text-lsc-cream/80 whitespace-pre-wrap">
                {motion.discussion_notes}
              </p>
            </div>
          )}

          {/* Outcome Notes */}
          {motion.outcome_notes && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Outcome Notes
              </h2>
              <p className="text-lsc-dark/80 dark:text-lsc-cream/80 whitespace-pre-wrap">
                {motion.outcome_notes}
              </p>
            </div>
          )}

          {/* Special Status Details */}
          {motion.status === "tabled" && (
            <div className="bg-earth-50 dark:bg-earth-800/50 rounded-xl p-6">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-4 flex items-center gap-2">
                <Pause className="h-5 w-5" />
                Motion Tabled
              </h2>
              {motion.tabled_until && (
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                  <strong>Tabled Until:</strong> {formatDate(motion.tabled_until)}
                </p>
              )}
              {motion.tabled_reason && (
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                  <strong>Reason:</strong> {motion.tabled_reason}
                </p>
              )}
            </div>
          )}

          {motion.status === "referred" && (
            <div className="bg-lsc-rose/10 dark:bg-lsc-rose/20 rounded-xl p-6">
              <h2 className="font-serif text-lg font-semibold text-lsc-rose dark:text-lsc-rose-light mb-4 flex items-center gap-2">
                <Building2 className="h-5 w-5" />
                Referred to Committee
              </h2>
              {motion.referred_to_committee_name && (
                <p className="text-lsc-rose dark:text-lsc-rose-light mb-2">
                  <strong>Committee:</strong> {motion.referred_to_committee_name}
                </p>
              )}
              {motion.referred_notes && (
                <p className="text-lsc-rose dark:text-lsc-rose-light">
                  <strong>Notes:</strong> {motion.referred_notes}
                </p>
              )}
            </div>
          )}

          {motion.status === "withdrawn" && (
            <div className="bg-earth-100 dark:bg-earth-800 rounded-xl p-6">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-4 flex items-center gap-2">
                <Ban className="h-5 w-5" />
                Motion Withdrawn
              </h2>
              {motion.withdrawn_reason && (
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                  <strong>Reason:</strong> {motion.withdrawn_reason}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Participants */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
            <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Participants</h2>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-lsc-rose/20 flex items-center justify-center">
                  <User className="h-5 w-5 text-lsc-rose" />
                </div>
                <div>
                  <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                    {motion.moved_by_name || `Member #${motion.moved_by_id}`}
                  </div>
                  <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Moved the motion</div>
                </div>
              </div>
              {motion.seconded_by_id && (
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-earth-100 dark:bg-earth-800/30 flex items-center justify-center">
                    <User className="h-5 w-5 text-lsc-rose dark:text-lsc-rose-light" />
                  </div>
                  <div>
                    <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                      {motion.seconded_by_name || `Member #${motion.seconded_by_id}`}
                    </div>
                    <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Seconded the motion</div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Timeline */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
            <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
              <History className="h-5 w-5" />
              Timeline
            </h2>
            <div className="space-y-4">
              {timeline.map((step, index) => (
                <div key={index} className="flex gap-3">
                  <div className="relative">
                    <div
                      className={`h-8 w-8 rounded-full flex items-center justify-center ${
                        step.completed
                          ? step.active
                            ? "bg-lsc-rose text-white"
                            : "bg-status-success-100 text-status-success-600 dark:bg-status-success-900/30 dark:text-status-success-400"
                          : "bg-earth-100 text-earth-600 dark:bg-earth-700 dark:text-earth-300"
                      }`}
                    >
                      {step.icon}
                    </div>
                    {index < timeline.length - 1 && (
                      <div
                        className={`absolute left-1/2 top-8 w-0.5 h-8 -translate-x-1/2 ${
                          step.completed ? "bg-status-success-200 dark:bg-status-success-800" : "bg-earth-200 dark:bg-earth-700"
                        }`}
                      />
                    )}
                  </div>
                  <div className="flex-1 pb-4">
                    <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{step.label}</div>
                    {step.timestamp && (
                      <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        {formatDateTime(step.timestamp)}
                      </div>
                    )}
                    {step.details && (
                      <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{step.details}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Links */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
            <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Related</h2>
            <div className="space-y-2">
              {meeting && (
                <Link
                  to={`/board/meetings/${meeting.id}`}
                  className="block text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline"
                >
                  View Meeting Details
                </Link>
              )}
              <Link to="/board/motions" className="block text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline">
                All Board Motions
              </Link>
              <Link to="/board/minutes" className="block text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline">
                Meeting Minutes
              </Link>
              <Link to="/board/documents" className="block text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline">
                Board Documents
              </Link>
            </div>
          </div>
        </div>
      </div>
    </PageContainer>
  </>
  );
}