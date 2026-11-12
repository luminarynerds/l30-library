/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useMemo, useRef, useState, useCallback, useSyncExternalStore } from "react";
import { useSearchParams } from "react-router-dom";
import { Calendar, ListChecks, MapPin, Video, Clock, Search, X, XCircle, Filter, Rss, FileText, MessageSquare, Megaphone, AlertCircle, CalendarPlus, Mic } from "lucide-react";
import api from "../../api/api";
import { searchMeetings } from "../../api/board-api";
import type { MeetingSearchParams } from "../../api/board-api";
import { API_BASE } from '@/api/types'
import { useTranslation, getCurrentLocale } from '@/i18n'
import ActiveCommentPeriodBanner from '../../components/board/ActiveCommentPeriodBanner'
import { useBranding } from '@/contexts/BrandingContext'
import PageContainer from '@/components/layout/PageContainer'

interface AgendaPreviewItem {
  title: string;
  item_number: string;
}

interface NoticePostingLocation {
  location: string;
  url?: string | null;
  posted_at?: string | null;
  notes?: string | null;
}

interface BoardMeeting {
  id: number;
  meeting_type: string;
  title: string;
  description?: string;
  scheduled_date: string;
  start_time?: string;
  end_time?: string;
  location?: string;
  is_virtual: boolean;
  virtual_meeting_url?: string;
  is_cancelled: boolean;
  agenda_preview?: AgendaPreviewItem[];
  minutes_approved?: boolean | null;
  public_comment_instructions?: string | null;
  public_comment_enabled?: boolean;
  agenda_published_at?: string | null;
  notice_posted_at?: string | null;
  notice_posting_locations?: NoticePostingLocation[] | null;
  notice_status?: string | null;
  notice_lead_days_required?: number | null;
  accessibility_info?: string | null;
  quorum_met?: boolean | null;
}

const DEFAULT_PUBLIC_COMMENT_INSTRUCTIONS =
  "Three minutes per speaker. Sign in at the door, or submit written comment to the board clerk before the meeting.";

type MeetingListResponse =
  | BoardMeeting[]
  | {
      meetings?: BoardMeeting[];
      results?: BoardMeeting[];
      items?: BoardMeeting[];
    };

const meetingTypeLabels: Record<string, string> = {
  regular: "Regular Meeting",
  special: "Special Meeting",
  emergency: "Emergency Meeting",
  committee: "Committee Meeting",
  workshop: "Workshop",
  public_hearing: "Public Hearing",
};

const meetingTypeKeys: Record<string, string> = {
  regular: "boardMeetings.meetingType.regular",
  special: "boardMeetings.meetingType.special",
  emergency: "boardMeetings.meetingType.emergency",
  committee: "boardMeetings.meetingType.committee",
  workshop: "boardMeetings.meetingType.workshop",
  public_hearing: "boardMeetings.meetingType.publicHearing",
};

const MEETING_TYPES = [
  { value: "", labelKey: "boardMeetings.filterAllTypes", label: "All Types" },
  { value: "regular", labelKey: "boardMeetings.meetingType.regular", label: "Regular Meeting" },
  { value: "special", labelKey: "boardMeetings.meetingType.special", label: "Special Meeting" },
  { value: "emergency", labelKey: "boardMeetings.meetingType.emergency", label: "Emergency Meeting" },
  { value: "committee", labelKey: "boardMeetings.meetingType.committee", label: "Committee Meeting" },
  { value: "workshop", labelKey: "boardMeetings.meetingType.workshop", label: "Workshop" },
  { value: "public_hearing", labelKey: "boardMeetings.meetingType.publicHearing", label: "Public Hearing" },
];

const MEETING_STATUSES = [
  { value: "", labelKey: "boardMeetings.filterAllStatuses", label: "All Statuses" },
  { value: "scheduled", labelKey: "boardMeetings.status.scheduled", label: "Scheduled" },
  { value: "completed", labelKey: "boardMeetings.status.completed", label: "Completed" },
  { value: "cancelled", labelKey: "boardMeetings.status.cancelled", label: "Cancelled" },
];

const DEBOUNCE_MS = 300;
const MS_PER_DAY = 86_400_000;
const MEETINGS_PAGE_SIZE = 50;

export default function BoardMeetingsPage() {
  const branding = useBranding()
  const { t } = useTranslation()
  const [searchParams] = useSearchParams();
  const yearParam = searchParams.get("year");
  const [upcomingMeetings, setUpcomingMeetings] = useState<BoardMeeting[]>([]);
  const [pastMeetings, setPastMeetings] = useState<BoardMeeting[]>([]);
  const [searchResults, setSearchResults] = useState<BoardMeeting[]>([]);
  const [searchTotal, setSearchTotal] = useState(0);
  const [searchParamsSnapshot, setSearchParamsSnapshot] = useState<MeetingSearchParams>({});

  const [loading, setLoading] = useState(true);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchLoadingMore, setSearchLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryKey, _setRetryKey] = useState(0);

  // Search / filter state
  const [query, setQuery] = useState("");
  const [meetingType, setMeetingType] = useState("");
  const [meetingStatus, setMeetingStatus] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [hasRecording, setHasRecording] = useState(false);

  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isSearchActive =
    query.trim() !== "" ||
    meetingType !== "" ||
    meetingStatus !== "" ||
    dateFrom !== "" ||
    dateTo !== "" ||
    hasRecording;

  // Initial load of all meetings (no filters)
  useEffect(() => {
    const getMeetingDate = (meeting: BoardMeeting): Date | null => {
      const dateValue = meeting.scheduled_date;
      if (!dateValue) return null;
      const parsed = new Date(dateValue);
      return Number.isNaN(parsed.getTime()) ? null : parsed;
    };

    const extractMeetings = (response: MeetingListResponse): BoardMeeting[] => {
      if (Array.isArray(response)) return response;
      if (Array.isArray(response.meetings)) return response.meetings;
      if (Array.isArray(response.results)) return response.results;
      if (Array.isArray(response.items)) return response.items;
      return [];
    };

    const fetchMeetings = async () => {
      try {
        const meetings: BoardMeeting[] = [];
        const seenMeetingIds = new Set<number>();
        let skip = 0;
        while (true) {
          const data = await api.get(
            `${API_BASE}/board/meetings?limit=${MEETINGS_PAGE_SIZE}&skip=${skip}`,
          ) as MeetingListResponse;
          const page = extractMeetings(data);
          const newMeetings = page.filter((meeting) => !seenMeetingIds.has(meeting.id));
          if (newMeetings.length === 0 && page.length > 0) break;
          newMeetings.forEach((meeting) => seenMeetingIds.add(meeting.id));
          meetings.push(...newMeetings);
          if (page.length < MEETINGS_PAGE_SIZE) break;
          skip += page.length;
        }
        const now = new Date();
        const upcoming = meetings.filter(
          (m: BoardMeeting) => {
            const meetingDate = getMeetingDate(m);
            return meetingDate !== null && meetingDate >= now && !m.is_cancelled;
          }
        );
        const past = meetings.filter(
          (m: BoardMeeting) => {
            const meetingDate = getMeetingDate(m);
            return meetingDate === null || meetingDate < now || m.is_cancelled;
          }
        );
        // The list endpoint returns scheduled_date DESC. That's right for past
        // meetings (most recent first) but wrong for upcoming, which should
        // read nearest-first. Sort client-side so the order is explicit either
        // way and not contingent on backend default.
        const byDateAsc = (a: BoardMeeting, b: BoardMeeting) => {
          const da = getMeetingDate(a)?.getTime() ?? Number.POSITIVE_INFINITY;
          const db = getMeetingDate(b)?.getTime() ?? Number.POSITIVE_INFINITY;
          return da - db;
        };
        upcoming.sort(byDateAsc);
        past.sort((a, b) => -byDateAsc(a, b));
        setUpcomingMeetings(upcoming);
        // Year-grouping below handles arbitrary depth; no longer cap at 10.
        setPastMeetings(past);
      } catch (_err) {
        setError(t("boardMeetings.unableToLoadMeetingsError", "Unable to load meetings"));
        Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
      } finally {
        setLoading(false);
      }
    };
    fetchMeetings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [retryKey]);

  // Debounced search whenever filters change
  const runSearch = useCallback(async (params: MeetingSearchParams) => {
    setSearchLoading(true);
    try {
      const response = await searchMeetings({ ...params, skip: 0, limit: MEETINGS_PAGE_SIZE });
      setSearchResults(response.results as BoardMeeting[]);
      setSearchTotal(response.total);
      setSearchParamsSnapshot(params);
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
      setSearchResults([]);
      setSearchTotal(0);
    } finally {
      setSearchLoading(false);
    }
  }, [retryKey]);

  const loadMoreSearchResults = async () => {
    setSearchLoadingMore(true);
    try {
      const response = await searchMeetings({
        ...searchParamsSnapshot,
        skip: searchResults.length,
        limit: MEETINGS_PAGE_SIZE,
      });
      setSearchResults((current) => [...current, ...(response.results as BoardMeeting[])]);
      setSearchTotal(response.total);
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
    } finally {
      setSearchLoadingMore(false);
    }
  };

  useEffect(() => {
    if (!isSearchActive) {
      setSearchResults([]);
      setSearchTotal(0);
      return;
    }

    if (debounceTimer.current) clearTimeout(debounceTimer.current);

    debounceTimer.current = setTimeout(() => {
      const params: MeetingSearchParams = {};
      if (query.trim()) params.q = query.trim();
      if (meetingType) params.meeting_type = meetingType;
      if (meetingStatus) params.status = meetingStatus;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      if (hasRecording) params.has_recording = true;
      runSearch(params);
    }, DEBOUNCE_MS);

    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
    };
  }, [query, meetingType, meetingStatus, dateFrom, dateTo, hasRecording, isSearchActive, runSearch]);

  const translateMeetingType = (type: string): string => {
    const key = meetingTypeKeys[type];
    const fallback = meetingTypeLabels[type] ?? type;
    return key ? t(key, fallback) : fallback;
  };

  const clearFilters = () => {
    setQuery("");
    setMeetingType("");
    setMeetingStatus("");
    setDateFrom("");
    setDateTo("");
    setHasRecording(false);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(getCurrentLocale(), {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  const formatTime = (dateString?: string) => {
    if (!dateString) return null;
    return new Date(dateString).toLocaleTimeString(getCurrentLocale(), {
      hour: "numeric",
      minute: "2-digit",
    });
  };

  // Compact "Mon Day" for badge faces.
  const formatShortDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(getCurrentLocale(), {
      month: "short",
      day: "numeric",
    });
  };

  const formatShortDateTime = (dateString: string) => {
    const d = new Date(dateString);
    const date = d.toLocaleDateString(getCurrentLocale(), { month: "short", day: "numeric" });
    const time = d.toLocaleTimeString(getCurrentLocale(), { hour: "numeric", minute: "2-digit" });
    return `${date}, ${time}`;
  };

  // Group past meetings by calendar year (descending). Each entry: { year, meetings }.
  const pastByYear = useMemo(() => {
    const groups = new Map<number, BoardMeeting[]>();
    for (const m of pastMeetings) {
      const d = m.scheduled_date ? new Date(m.scheduled_date) : null;
      const y = d && !Number.isNaN(d.getTime()) ? d.getFullYear() : 0;
      if (!groups.has(y)) groups.set(y, []);
      groups.get(y)!.push(m);
    }
    return Array.from(groups.entries())
      .sort((a, b) => b[0] - a[0])
      .map(([year, meetings]) => ({ year, meetings }));
  }, [pastMeetings]);

  const density = useSyncExternalStore(
    (cb) => {
      const observer = new MutationObserver(cb);
      observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-density"] });
      return () => observer.disconnect();
    },
    () => (document.documentElement.dataset.density as string) || "comfortable"
  );

  const MeetingCard = ({ meeting }: { meeting: BoardMeeting }) => {
    const meetingDate = meeting.scheduled_date ? new Date(meeting.scheduled_date) : null;
    const now = new Date();
    const isUpcoming =
      meetingDate !== null && !Number.isNaN(meetingDate.getTime()) && meetingDate >= now && !meeting.is_cancelled;
    const locations = meeting.notice_posting_locations ?? [];
    const hasNoticeProvenance = Boolean(meeting.notice_posted_at) || locations.length > 0;
    const leadDaysRequired = meeting.notice_lead_days_required ?? 2;
    const daysUntilMeeting =
      meetingDate && !Number.isNaN(meetingDate.getTime())
        ? (meetingDate.getTime() - now.getTime()) / MS_PER_DAY
        : Number.POSITIVE_INFINITY;
    const noticeOverdue =
      isUpcoming && !hasNoticeProvenance && daysUntilMeeting < leadDaysRequired;

    return (
    <div className={"bg-lsc-white dark:bg-earth-800 rounded-xl shadow " + (density === "compact" ? "p-4 " : density === "spacious" ? "p-8 " : "p-6 ") + (meeting.is_cancelled ? "bg-status-danger-50/30 dark:bg-status-danger-900/10 border border-status-danger-200/50 dark:border-status-danger-800/30" : "")}>
      <div className="pb-2">
        <div className="flex justify-between items-start">
          <h3 className={"font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream" + (meeting.is_cancelled ? " line-through decoration-red-400/60" : "")}>{meeting.title}</h3>
          {meeting.is_cancelled && (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300" aria-label={t("boardMeetings.statusCancelledAriaLabel", "Status: Cancelled")}>
              <XCircle className="h-3 w-3" aria-hidden="true" />
              {t("boardMeetings.status.cancelled", "Cancelled")}
            </span>
          )}
        </div>
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-sage-100 text-sage-800 dark:bg-sage-900/30 dark:text-sage-300 border border-sage-200 dark:border-sage-700 mt-2">
          {translateMeetingType(meeting.meeting_type)}
        </span>
      </div>
      <div className={`text-sm ${density === "spacious" ? "space-y-3 mt-6" : "space-y-2 mt-4"}`}>
        <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/90">
          <Calendar className="h-4 w-4" />
          <span>{formatDate(meeting.scheduled_date)}</span>
        </div>
        {meeting.start_time && (
          <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/90">
            <Clock className="h-4 w-4" />
            <span>
              {formatTime(meeting.start_time)}
              {meeting.end_time && " - " + formatTime(meeting.end_time)}
            </span>
          </div>
        )}
        {meeting.location && (
          <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/90">
            <MapPin className="h-4 w-4" />
            <span>{meeting.location}</span>
          </div>
        )}
        {meeting.is_virtual && meeting.virtual_meeting_url && (
          <div className="flex items-center gap-2 text-lsc-rose dark:text-lsc-rose-light">
            <Video className="h-4 w-4" />
            <a
              href={meeting.virtual_meeting_url}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:underline"
            >
              {t("boardMeetings.joinVirtualMeeting", "Join Virtual Meeting")}
            </a>
          </div>
        )}
        {meeting.description && (
          <p className="text-lsc-dark/70 dark:text-lsc-cream/90 mt-2">{meeting.description}</p>
        )}
        {meeting.agenda_preview && meeting.agenda_preview.length > 0 && (
          <div className="mt-3 flex items-start gap-2">
            <ListChecks className="h-4 w-4 mt-0.5 text-lsc-dark/70 dark:text-lsc-cream/70 shrink-0" />
            <ul className="space-y-0.5">
              {meeting.agenda_preview.map((item) => (
                <li key={item.item_number} className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-1">
                  {item.item_number}. {item.title}
                </li>
              ))}
            </ul>
          </div>
        )}
        {/* Public-notice provenance: governance evidence that the meeting
            was noticed per open-meetings rules. Quiet caption when present;
            red badge if the notice deadline has lapsed without a posting. */}
        {hasNoticeProvenance && (
          <div className="mt-3 flex items-start gap-2 text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
            <Megaphone className="h-3.5 w-3.5 mt-0.5 shrink-0" aria-hidden="true" />
            <p>
              {t("boardMeetings.publicNoticePostedPrefix", "Public notice posted")}
              {meeting.notice_posted_at && ` ${formatShortDateTime(meeting.notice_posted_at)}`}
              {locations.length > 0 && (
                <>
                  {" "}{t("boardMeetings.publicNoticeAtPrefix", "at:")} <span className="italic">{locations.map((l) => l.location).join(" · ")}</span>
                </>
              )}.
            </p>
          </div>
        )}
        {noticeOverdue && (
          <div className="mt-3">
            <span
              className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-700 dark:text-status-danger-300 border border-status-danger-200 dark:border-status-danger-800"
              aria-label={t("boardMeetings.noticeNotYetPostedAriaLabel", "Public notice not yet posted")}
            >
              <AlertCircle className="h-3 w-3" aria-hidden="true" />
              {t("boardMeetings.noticeNotYetPosted", "Notice not yet posted")}
            </span>
          </div>
        )}
        {(meeting.public_comment_enabled ?? true) && (
          <div className="mt-3 flex items-start gap-2">
            <MessageSquare className="h-4 w-4 mt-0.5 text-lsc-dark/70 dark:text-lsc-cream/70 shrink-0" aria-hidden="true" />
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/90">
              <span className="font-medium text-lsc-dark dark:text-lsc-cream">{t("boardMeetings.howToCommentPrefix", "How to comment:")}</span>{" "}
              {meeting.public_comment_instructions || DEFAULT_PUBLIC_COMMENT_INSTRUCTIONS}
            </p>
          </div>
        )}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {/* Agenda badge.
              published timestamp -> "Agenda posted [Mon Day]" link
              null + upcoming     -> faded "Agenda pending" with tooltip
              null + past         -> render nothing */}
          {meeting.agenda_published_at ? (
            <a
              href={"/board/meetings/" + meeting.id}
              className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium bg-sage-50 dark:bg-sage-900/20 text-sage-800 dark:text-sage-200 border border-sage-200 dark:border-sage-700 hover:bg-sage-100 dark:hover:bg-sage-900/40"
              aria-label={t("boardMeetings.viewAgendaForAriaLabel", "View agenda for {{title}}").replace("{{title}}", meeting.title)}
            >
              <FileText className="h-3 w-3" aria-hidden="true" />
              {t("boardMeetings.agendaPostedPrefix", "Agenda posted")} {formatShortDate(meeting.agenda_published_at)}
            </a>
          ) : isUpcoming ? (
            <span
              className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium bg-lsc-cream/60 dark:bg-earth-700/40 text-lsc-dark/60 dark:text-lsc-cream/60 border border-lsc-border/60 dark:border-earth-700/60 cursor-help"
              title={t("boardMeetings.agendaTypicallyPostedTooltip", "Agenda typically posted 72 hours before the meeting.")}
              aria-label={t("boardMeetings.agendaPendingAriaLabel", "Agenda pending; typically posted 72 hours before the meeting")}
            >
              <FileText className="h-3 w-3" aria-hidden="true" />
              {t("boardMeetings.agendaPending", "Agenda pending")}
            </span>
          ) : null}
          {/* Minutes artifact badge.
              true   -> approved; link to detail page where minutes content surfaces
              false  -> past meeting awaiting board approval; disabled with tooltip
              null   -> upcoming; render nothing */}
          {meeting.minutes_approved === true && (
            <a
              href={"/board/meetings/" + meeting.id}
              className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium bg-sage-50 dark:bg-sage-900/20 text-sage-800 dark:text-sage-200 border border-sage-200 dark:border-sage-700 hover:bg-sage-100 dark:hover:bg-sage-900/40"
              aria-label={t("boardMeetings.viewMinutesForAriaLabel", "View minutes for {{title}}").replace("{{title}}", meeting.title)}
            >
              <FileText className="h-3 w-3" aria-hidden="true" />
              {t("boardMeetings.viewMinutesLabel", "View Minutes")}
            </a>
          )}
          {meeting.minutes_approved === false && (
            <span
              className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium bg-lsc-cream/60 dark:bg-earth-700/40 text-lsc-dark/60 dark:text-lsc-cream/60 border border-lsc-border/60 dark:border-earth-700/60 cursor-not-allowed"
              title={t("boardMeetings.minutesPendingApprovalTooltip", "Minutes pending board approval")}
              aria-label={t("boardMeetings.minutesPendingApprovalTooltip", "Minutes pending board approval")}
            >
              <FileText className="h-3 w-3" aria-hidden="true" />
              {t("boardMeetings.minutesPendingApprovalBadge", "Minutes pending approval")}
            </span>
          )}
          <a href={"/board/meetings/" + meeting.id} aria-label={t("boardMeetings.viewDetailsForAriaLabel", "View details for {{title}}").replace("{{title}}", meeting.title)} className="inline-block px-4 py-2 border border-lsc-border dark:border-earth-700 rounded text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown">{t("boardMeetings.viewDetailsLabel", "View Details")}</a>
        </div>
      </div>
    </div>
    );
  };

  // Hero block: countdown copy for the next upcoming meeting.
  const NextMeetingHero = ({ meeting }: { meeting: BoardMeeting }) => {
    const meetingDate = new Date(meeting.scheduled_date);
    const now = new Date();
    const startOfMeetingDay = new Date(
      meetingDate.getFullYear(),
      meetingDate.getMonth(),
      meetingDate.getDate(),
    );
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const dayDiff = Math.round(
      (startOfMeetingDay.getTime() - startOfToday.getTime()) / MS_PER_DAY,
    );
    let countdown: string;
    if (dayDiff <= 0) countdown = t("boardMeetings.countdownToday", "Today");
    else if (dayDiff === 1) countdown = t("boardMeetings.countdownTomorrow", "Tomorrow");
    else countdown = t("boardMeetings.countdownInDays", "In {{days}} days").replace("{{days}}", String(dayDiff));
    const formattedDate = meetingDate.toLocaleDateString(getCurrentLocale(), {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
    const formattedTime = meeting.start_time
      ? new Date(meeting.start_time).toLocaleTimeString(getCurrentLocale(), {
          hour: "numeric",
          minute: "2-digit",
        })
      : null;
    return (
      <section
        aria-label={t("boardMeetings.nextMeetingLabel", "Next meeting")}
        className="mb-8 rounded-xl bg-sage-50 dark:bg-sage-900/20 border border-sage-200 dark:border-sage-800 p-6"
      >
        <p className="text-xs uppercase tracking-wide font-semibold text-sage-800 dark:text-sage-300">
          {t("boardMeetings.nextMeetingLabel", "Next meeting")}
        </p>
        <h2 className="font-serif text-2xl font-semibold text-lsc-dark dark:text-lsc-cream mt-1">
          {meeting.title}
        </h2>
        <p className="mt-2 text-lsc-dark dark:text-lsc-cream">
          <span className="font-medium">{countdown}</span>
          <span className="text-lsc-dark/70 dark:text-lsc-cream/80">
            {" "}&middot; {formattedDate}
            {formattedTime && `, ${formattedTime}`}
          </span>
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
          {meeting.is_virtual ? (
            <span className="inline-flex items-center gap-1">
              <Video className="h-4 w-4" aria-hidden="true" />
              {t("boardMeetings.virtualLabel", "Virtual")}
            </span>
          ) : meeting.location ? (
            <span className="inline-flex items-center gap-1">
              <MapPin className="h-4 w-4" aria-hidden="true" />
              {meeting.location}
            </span>
          ) : null}
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <a
            href={`${API_BASE}/board/meetings/calendar.ics`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium bg-lsc-rose text-white hover:bg-lsc-rose/90"
          >
            <CalendarPlus className="h-4 w-4" aria-hidden="true" />
            {t("boardMeetings.addToCalendarLabel", "Add to calendar")}
          </a>
          {meeting.agenda_published_at ? (
            <a
              href={`/board/meetings/${meeting.id}`}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium border border-sage-300 dark:border-sage-700 text-sage-900 dark:text-sage-100 hover:bg-sage-100 dark:hover:bg-sage-900/40"
            >
              <FileText className="h-4 w-4" aria-hidden="true" />
              {t("boardMeetings.readAgendaLabel", "Read agenda")}
            </a>
          ) : (
            <span
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium border border-lsc-border/60 dark:border-earth-700/60 text-lsc-dark/50 dark:text-lsc-cream/50 cursor-not-allowed"
              title={t("boardMeetings.agendaNotYetPostedTooltip", "Agenda not yet posted")}
              aria-label={t("boardMeetings.readAgendaNotYetPostedAriaLabel", "Read agenda: agenda not yet posted")}
              aria-disabled="true"
            >
              <FileText className="h-4 w-4" aria-hidden="true" />
              {t("boardMeetings.readAgendaLabel", "Read agenda")}
            </span>
          )}
          <a
            href="#how-to-speak"
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium border border-sage-300 dark:border-sage-700 text-sage-900 dark:text-sage-100 hover:bg-sage-100 dark:hover:bg-sage-900/40"
          >
            <Mic className="h-4 w-4" aria-hidden="true" />
            {t("boardMeetings.howToSpeakHeading", "How to speak at a meeting")}
          </a>
        </div>
      </section>
    );
  };

  if (loading) {
    return (
      <>
      <PageContainer className="py-8">
        <div className="motion-safe:animate-pulse space-y-4">
          <div className="h-8 bg-lsc-cream dark:bg-lsc-brown rounded w-1/3"></div>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-48 bg-lsc-cream dark:bg-lsc-brown rounded"></div>
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
      <div className="mb-8">
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">{t("boardMeetings.pageHeading", "Board Meetings")}</h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/90 mt-2">
          {t("boardMeetings.pageIntro", "All board meetings are open to the public. Community members are welcome to attend and participate during the public comment period.")}
        </p>
        <div className="flex items-center gap-2 mt-3">
          <a
            href={`${API_BASE}/board/meetings/calendar.ics`}
            target="_blank"
            rel="noopener noreferrer"
            title={t("boardMeetings.subscribeCalendarFeedTooltip", "Subscribe to calendar feed")}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose transition-colors"
          >
            <Calendar className="h-4 w-4" />
            <span className="sr-only sm:not-sr-only">iCal</span>
          </a>
          <a
            href={`${API_BASE}/board/meetings/feed.xml`}
            target="_blank"
            rel="noopener noreferrer"
            title={t("boardMeetings.rssFeedTooltip", "RSS feed")}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose transition-colors"
          >
            <Rss className="h-4 w-4" />
            <span className="sr-only sm:not-sr-only">RSS</span>
          </a>
        </div>
      </div>

      <ActiveCommentPeriodBanner />

      {upcomingMeetings[0] && <NextMeetingHero meeting={upcomingMeetings[0]} />}

      {/* Persistent "How to speak" module. Independent of any active comment
          period — always rendered so the answer is one anchor link away. */}
      <section
        id="how-to-speak"
        aria-labelledby="how-to-speak-heading"
        className="mb-8 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-6"
      >
        <h2
          id="how-to-speak-heading"
          className="font-serif text-xl font-semibold text-lsc-dark dark:text-lsc-cream"
        >
          {t("boardMeetings.howToSpeakHeading", "How to speak at a meeting")}
        </h2>
        <ol className="mt-4 space-y-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/90 list-decimal pl-5">
          <li>{t("boardMeetings.howToSpeakStep1", "Sign in at the door, or email board@l30.org at least 48 hours ahead.")}</li>
          <li>{t("boardMeetings.howToSpeakStep2", "You'll have 3 minutes.")}</li>
          <li>{t("boardMeetings.howToSpeakStep3", "Comments are recorded in the minutes and become part of the public record.")}</li>
        </ol>
      </section>

      {/* Search & Filter Panel */}
      <div className="mb-8 bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-5 space-y-4">
        {/* Text search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-lsc-dark/70 dark:text-lsc-cream/70 pointer-events-none" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('boardMeetings.searchMeetingsByTitleDescription')}
            aria-label={t('boardMeetings.searchMeetingsByTitleDescription2')}
            className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-lsc-border bg-transparent text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-brown"
          />
          {query && (
            <button
              onClick={() => setQuery("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
              aria-label={t('aria.boardMeetings.clearSearchText')}
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Filter row */}
        <div className="flex flex-wrap gap-3 items-end" role="group" aria-label={t("boardMeetings.meetingFiltersAriaLabel", "Meeting filters")}>
          {/* Meeting type */}
          <div className="flex flex-col gap-1 min-w-[160px]">
            <label htmlFor="meeting-filter-type" className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1">
              <Filter className="h-3 w-3" /> {t("boardMeetings.filterTypeLabel", "Type")}
            </label>
            <select
              id="meeting-filter-type"
              value={meetingType}
              onChange={(e) => setMeetingType(e.target.value)}
              className="rounded-lg border border-lsc-border bg-transparent px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-brown dark:bg-earth-800"
            >
              {MEETING_TYPES.map((opt) => (
                <option key={opt.value} value={opt.value}>{t(opt.labelKey, opt.label)}</option>
              ))}
            </select>
          </div>

          {/* Status */}
          <div className="flex flex-col gap-1 min-w-[140px]">
            <label htmlFor="meeting-filter-status" className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{t("boardMeetings.filterStatusLabel", "Status")}</label>
            <select
              id="meeting-filter-status"
              value={meetingStatus}
              onChange={(e) => setMeetingStatus(e.target.value)}
              className="rounded-lg border border-lsc-border bg-transparent px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-brown dark:bg-earth-800"
            >
              {MEETING_STATUSES.map((opt) => (
                <option key={opt.value} value={opt.value}>{t(opt.labelKey, opt.label)}</option>
              ))}
            </select>
          </div>

          {/* Date from */}
          <div className="flex flex-col gap-1 min-w-[140px]">
            <label htmlFor="meeting-filter-from" className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{t("boardMeetings.filterFromLabel", "From")}</label>
            <input
              id="meeting-filter-from"
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="rounded-lg border border-lsc-border bg-transparent px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-brown dark:bg-earth-800"
            />
          </div>

          {/* Date to */}
          <div className="flex flex-col gap-1 min-w-[140px]">
            <label htmlFor="meeting-filter-to" className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{t("boardMeetings.filterToLabel", "To")}</label>
            <input
              id="meeting-filter-to"
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="rounded-lg border border-lsc-border bg-transparent px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-brown dark:bg-earth-800"
            />
          </div>

          {/* "Has Recording" filter hidden: no meeting in current production
              data exposes a recording_url, so the affordance promises something
              that never delivers. Re-enable here once recording URLs are
              surfaced on the list endpoint and rendered as artifact badges on
              MeetingCard above. State (`hasRecording`/`setHasRecording`) is
              retained so the search effect still honors `?has_recording=true`
              via URL if it ever returns. */}

          {/* Clear filters */}
          {isSearchActive && (
            <button
              onClick={clearFilters}
              className="self-end pb-2 flex items-center gap-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream underline underline-offset-2"
            >
              <X className="h-3.5 w-3.5" />
              {t("boardMeetings.clearFiltersLabel", "Clear filters")}
            </button>
          )}
        </div>
      </div>

      {/* Screen reader announcement for search/filter results */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {!loading && !searchLoading && isSearchActive && (
          searchTotal === 1
            ? t("boardMeetings.meetingsFoundAnnouncementOne", "{{count}} meeting found").replace("{{count}}", String(searchTotal))
            : t("boardMeetings.meetingsFoundAnnouncementOther", "{{count}} meetings found").replace("{{count}}", String(searchTotal))
        )}
      </div>

      {error ? (
        <div className="text-center py-12">
          <p className="text-lsc-dark/70 dark:text-lsc-cream/90">{error}</p>
          <button
            onClick={() => { setError(null); window.location.reload(); }}
            className="mt-4 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors"
          >
            {t("boardMeetings.tryAgainButton", "Try Again")}
          </button>
        </div>
      ) : isSearchActive ? (
        /* Search results view */
        <section aria-label={t("boardMeetings.searchResultsAriaLabel", "Search results")}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-serif text-2xl font-semibold text-lsc-dark dark:text-lsc-cream">
              {t("boardMeetings.searchResultsHeading", "Search Results")}
              {!searchLoading && (
                <span className="ml-2 text-base font-normal text-lsc-dark/70 dark:text-lsc-cream/70">
                  ({searchTotal} {searchTotal === 1
                    ? t("boardMeetings.searchResultsCountOne", "meeting")
                    : t("boardMeetings.searchResultsCountOther", "meetings")})
                </span>
              )}
            </h2>
            {searchLoading && (
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 motion-safe:animate-pulse">{t("boardMeetings.searchingLabel", "Searching...")}</span>
            )}
          </div>

          {!searchLoading && searchResults.length === 0 ? (
            <div className="text-center py-16 bg-lsc-white dark:bg-earth-800 rounded-xl shadow">
              <Search className="mx-auto h-10 w-10 text-lsc-dark/20 dark:text-lsc-cream/20 mb-3" />
              <p className="text-lg font-medium text-lsc-dark dark:text-lsc-cream mb-1">{t("boardMeetings.noMeetingsFoundHeading", "No meetings found")}</p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                {t("boardMeetings.tryAdjustingSearchFilters", "Try adjusting your search terms or filters.")}
              </p>
              <button
                onClick={clearFilters}
                className="px-4 py-2 rounded-lg border border-lsc-border text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown"
              >
                {t("boardMeetings.clearAllFiltersButton", "Clear all filters")}
              </button>
            </div>
          ) : (
            <>
              <p className="mb-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70" aria-live="polite">
                {t("boardMeetings.showingSearchResults", "Showing {{shown}} of {{total}} meetings")
                  .replace("{{shown}}", String(searchResults.length))
                  .replace("{{total}}", String(searchTotal))}
              </p>
              <div className="grid gap-4">
                {searchResults.map((meeting) => (
                  <MeetingCard key={meeting.id} meeting={meeting} />
                ))}
              </div>
              {searchResults.length < searchTotal && (
                <div className="mt-6 text-center">
                  <button
                    type="button"
                    onClick={loadMoreSearchResults}
                    disabled={searchLoadingMore}
                    className="min-h-11 px-5 py-2.5 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream font-medium hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:cursor-wait disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
                  >
                    {searchLoadingMore
                      ? t("boardMeetings.loadingMoreMeetings", "Loading more meetings...")
                      : t("boardMeetings.loadMoreMeetings", "Load more meetings")}
                  </button>
                </div>
              )}
            </>
          )}
        </section>
      ) : (
        /* Default view: upcoming + past */
        <>
          <section className="mb-12" aria-label={t("boardMeetings.upcomingMeetingsAriaLabel", "Upcoming meetings")}>
            <h2 className="font-serif text-2xl font-semibold mb-4 text-lsc-dark dark:text-lsc-cream">{t("boardMeetings.upcomingMeetingsHeading", "Upcoming Meetings")}</h2>
            {upcomingMeetings.length === 0 ? (
              <p className="text-lsc-dark/70 dark:text-lsc-cream/90">
                {t("boardMeetings.noUpcomingMeetingsText", "No upcoming meetings scheduled. Check back soon.")}
              </p>
            ) : (
              <div className="grid gap-4">
                {upcomingMeetings.map((meeting) => (
                  <MeetingCard key={meeting.id} meeting={meeting} />
                ))}
              </div>
            )}
          </section>

          {pastByYear.length > 0 && (
            <section aria-label={t("boardMeetings.pastMeetingsAriaLabel", "Past meetings")}>
              <h2 className="font-serif text-2xl font-semibold mb-4 text-lsc-dark dark:text-lsc-cream">{t("boardMeetings.pastMeetingsHeading", "Past Meetings")}</h2>
              <div className="space-y-3">
                {pastByYear.map(({ year, meetings }, idx) => {
                  // Most recent year open by default; older years collapsed.
                  // ?year=YYYY overrides to open that year on initial load.
                  const yearParamOpen = yearParam !== null && yearParam === String(year);
                  const defaultOpen = idx === 0;
                  const open = yearParam !== null ? yearParamOpen : defaultOpen;
                  return (
                    <details
                      key={year}
                      open={open}
                      className="rounded-xl bg-lsc-white dark:bg-earth-800 shadow"
                    >
                      <summary className="cursor-pointer list-none px-5 py-3 flex items-center justify-between font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                        <span>
                          {year || t("boardMeetings.undatedYearLabel", "Undated")} <span className="text-sm font-normal text-lsc-dark/60 dark:text-lsc-cream/60">&middot; {meetings.length} {meetings.length === 1
                            ? t("boardMeetings.yearMeetingCountOne", "meeting")
                            : t("boardMeetings.yearMeetingCountOther", "meetings")}</span>
                        </span>
                        <span aria-hidden="true" className="text-lsc-dark/60 dark:text-lsc-cream/60">+</span>
                      </summary>
                      <div className="grid gap-4 p-4 pt-2">
                        {meetings.map((meeting) => (
                          <MeetingCard key={meeting.id} meeting={meeting} />
                        ))}
                      </div>
                    </details>
                  );
                })}
              </div>
            </section>
          )}
        </>
      )}

      <div className="mt-12 bg-lsc-cream dark:bg-earth-800 rounded-xl p-6">
        <h2 className="font-serif text-lg font-semibold mb-4 text-lsc-dark dark:text-lsc-cream">{t("boardMeetings.meetingInfoHeading", "Meeting Information")}</h2>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/90 mb-2">
          {t(
            "boardMeetings.meetingInfoParagraph1",
            "Regular board meetings are held monthly at the {{libraryName}}. See the schedule above for exact dates, times, and any cancellations or special meetings.",
          ).replace("{{libraryName}}", branding.library_name)}
        </p>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/90">
          {t("boardMeetings.meetingInfoParagraph2", "Meeting agendas are posted 72 hours before each meeting. Meeting minutes are available after approval by the board.")}
        </p>
      </div>
    </PageContainer>
    </>
  );
}
