/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Calendar, MapPin, Video, Clock, FileText, Sparkles, ChevronLeft, AlertCircle, CheckCircle, Loader2, Download, Printer } from "lucide-react";
import api from "../../api/api";
import MeetingRecordingPlayer from "../../components/board/MeetingRecordingPlayer";
import { API_BASE } from '@/api/types'
import { useTranslation, getCurrentLocale } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'
import { useBranding } from '@/contexts/BrandingContext'

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
  recording_url?: string | null;
}

interface MeetingBrief {
  id: number;
  meeting_id: number;
  status: string;
  brief_content?: string;
  key_discussion_points?: string[];
  recommended_questions?: string[];
  background_context?: string;
  model_used?: string;
  generation_time_ms?: number;
  error_message?: string;
  created_at: string;
}

interface ChecklistItem {
  item: string;
  completed: boolean;
  priority: string;
}

const meetingTypeLabels: Record<string, string> = {
  regular: "Regular Meeting",
  special: "Special Meeting",
  emergency: "Emergency Meeting",
  committee: "Committee Meeting",
  workshop: "Workshop",
  public_hearing: "Public Hearing",
};

export default function MeetingDetailPage() {
  const { t } = useTranslation()
  const branding = useBranding()
  const { meetingId } = useParams();
  const [meeting, setMeeting] = useState<BoardMeeting | null>(null);
  const [brief, setBrief] = useState<MeetingBrief | null>(null);
  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [generatingBrief, setGeneratingBrief] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Check if user is authenticated
        let authed = false;
        try {
          await api.get(`${API_BASE}/auth/me`);
          authed = true;
        } catch {
          authed = false;
        }
        setIsAuthenticated(authed);

        // Fetch meeting details by ID
        const found = await api.get(`${API_BASE}/board/meetings/${meetingId}`);
        if (!found) {
          setError("Meeting not found");
          return;
        }
        setMeeting(found);

        // If authenticated, fetch brief and checklist
        if (authed) {
          try {
            const briefData = await api.get(`${API_BASE}/board/meetings/` + meetingId + "/brief");
            setBrief(briefData);
          } catch {
            // No brief yet
          }

          try {
            const checklistData = await api.get(`${API_BASE}/board/meetings/` + meetingId + "/checklist");
            setChecklist(checklistData);
          } catch {
            // Checklist not available
          }
        }
      } catch (_err) {
        Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
        setError("Unable to load meeting details");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [meetingId]);

  // Schema.org Event JSON-LD for search-engine discoverability of board meetings.
  // Injected client-side; Google indexes client-rendered JSON-LD.
  useEffect(() => {
    if (!meeting) return;

    const location = meeting.is_virtual
      ? meeting.virtual_meeting_url
        ? { "@type": "VirtualLocation", url: meeting.virtual_meeting_url }
        : undefined
      : meeting.location
        ? { "@type": "Place", name: meeting.location, address: meeting.location }
        : undefined;

    const jsonLd: Record<string, unknown> = {
      "@context": "https://schema.org",
      "@type": "Event",
      name: meeting.title,
      startDate: meeting.start_time || meeting.scheduled_date,
      endDate: meeting.end_time || meeting.start_time || meeting.scheduled_date,
      eventStatus: meeting.is_cancelled
        ? "https://schema.org/EventCancelled"
        : "https://schema.org/EventScheduled",
      eventAttendanceMode: meeting.is_virtual
        ? "https://schema.org/OnlineEventAttendanceMode"
        : "https://schema.org/OfflineEventAttendanceMode",
      organizer: {
        "@type": "GovernmentOrganization",
        name: branding.library_name,
        url: branding.domain || window.location.origin,
      },
    };
    if (location) jsonLd.location = location;
    if (meeting.description) jsonLd.description = meeting.description;

    const script = document.createElement("script");
    script.type = "application/ld+json";
    script.setAttribute("data-meeting-jsonld", String(meeting.id));
    script.textContent = JSON.stringify(jsonLd);
    document.head.appendChild(script);

    return () => {
      script.remove();
    };
  }, [meeting, branding.library_name, branding.domain]);

  const generateBrief = async () => {
    setGeneratingBrief(true);
    try {
      const result = await api.post(`${API_BASE}/board/meetings/` + meetingId + "/brief", {});
      setBrief(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to generate brief. Make sure Ollama is running.");
    } finally {
      setGeneratingBrief(false);
    }
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

  if (loading) {
    return (
      <PageContainer className="py-8">
        <div className="motion-safe:animate-pulse space-y-4">
          <div className="h-8 bg-lsc-cream dark:bg-lsc-brown rounded w-1/3"></div>
          <div className="h-64 bg-lsc-cream dark:bg-lsc-brown rounded"></div>
        </div>
      </PageContainer>
    );
  }

  if (error || !meeting) {
    return (
      <PageContainer className="py-8">
        <Link to="/board/meetings" className="flex items-center gap-2 text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream hover:underline mb-4 print:hidden">
          <ChevronLeft className="h-4 w-4" /> Back to Meetings
        </Link>
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-6">
          <p className="text-status-danger-700 dark:text-status-danger-300">{error || "Meeting not found"}</p>
        </div>
      </PageContainer>
    );
  }

  return (
    <>
    <PageContainer className="py-8">
      <Link to="/board/meetings" className="flex items-center gap-2 text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream hover:underline mb-4 print:hidden">
        <ChevronLeft className="h-4 w-4" /> Back to Meetings
      </Link>

      {/* Print-only packet header */}
      <div className="hidden print:block print:mb-6 print:border-b print:border-lsc-border print:pb-4">
        <h1 className="text-2xl font-serif font-bold">Meeting Packet</h1>
        <p className="text-sm text-lsc-dark/70 mt-1">
          {meeting.title} &mdash; {formatDate(meeting.scheduled_date)}
          {meeting.start_time && " at " + formatTime(meeting.start_time)}
          {meeting.location && " | " + meeting.location}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3 print:block">
        {/* Main meeting info */}
        <div className="lg:col-span-2 space-y-6 print:space-y-4">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6 print:shadow-none print:p-0 print:rounded-none">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream print:hidden">{meeting.title}</h1>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-earth-200 mt-2">
                  {meetingTypeLabels[meeting.meeting_type] || meeting.meeting_type}
                </span>
              </div>
              <div className="flex items-center gap-2">
                {meeting.is_cancelled && (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300">Cancelled</span>
                )}
                <button
                  onClick={() => window.print()}
                  className="inline-flex items-center gap-2 px-3 py-1.5 border border-lsc-border text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg text-sm font-medium transition-colors print:hidden"
                  title="Print Meeting Packet"
                >
                  <Printer className="h-4 w-4" />
                  Print Packet
                </button>
                <Link
                  to={`/transparency/records-requests?meeting_id=${meeting.id}`}
                  className="text-sm underline text-lsc-dark/80 dark:text-lsc-cream/80 hover:text-lsc-rose dark:hover:text-lsc-rose print:hidden"
                >
                  {t('board.meeting.requestRecord')}
                </Link>
              </div>
            </div>

            <div className="space-y-3 text-lsc-dark/70 dark:text-lsc-cream/90">
              <div className="flex items-center gap-3">
                <Calendar className="h-5 w-5" />
                <span>{formatDate(meeting.scheduled_date)}</span>
              </div>
              {meeting.start_time && (
                <div className="flex items-center gap-3">
                  <Clock className="h-5 w-5" />
                  <span>
                    {formatTime(meeting.start_time)}
                    {meeting.end_time && " - " + formatTime(meeting.end_time)}
                  </span>
                </div>
              )}
              {meeting.location && (
                <div className="flex items-center gap-3">
                  <MapPin className="h-5 w-5" />
                  <span>{meeting.location}</span>
                </div>
              )}
              {meeting.is_virtual && meeting.virtual_meeting_url && (
                <div className="flex items-center gap-3 text-lsc-rose dark:text-lsc-rose-light print:hidden">
                  <Video className="h-5 w-5" />
                  <a href={meeting.virtual_meeting_url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                    Join Virtual Meeting
                  </a>
                </div>
              )}
            </div>

            {meeting.description && (
              <div className="mt-6 pt-6 border-t border-lsc-border dark:border-earth-700">
                <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">Description</h2>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/90">{meeting.description}</p>
              </div>
            )}
          </div>

          {/* Meeting Recording Player - only for past meetings with a recording */}
          {meeting.recording_url && new Date(meeting.scheduled_date) < new Date() && (
            <div className="print:hidden">
              <MeetingRecordingPlayer recordingUrl={meeting.recording_url} />
            </div>
          )}

          {/* AI Brief Section - Only for authenticated users */}
          {isAuthenticated && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6 print:shadow-none print:p-0 print:rounded-none print:border-t print:border-lsc-border print:pt-4 print:mt-4 print:break-before-page">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="h-5 w-5 text-lsc-rose" />
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">AI Meeting Brief</h2>
              </div>

              {!brief ? (
                <div className="text-center py-8 print:hidden">
                  <FileText className="h-12 w-12 text-lsc-border mx-auto mb-4" />
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/90 mb-4">
                    No AI brief generated yet. Generate one to get AI-powered insights for this meeting.
                  </p>
                  <button
                    onClick={generateBrief}
                    disabled={generatingBrief}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {generatingBrief ? (
                      <>
                        <Loader2 className="h-4 w-4 motion-safe:animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-4 w-4" />
                        Generate Brief
                      </>
                    )}
                  </button>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{t('meetingDetail.requiresOllamaToBeRunning')}</p>
                </div>
              ) : brief.status === "generating" ? (
                <div className="text-center py-8 print:hidden">
                  <Loader2 className="h-12 w-12 text-lsc-rose motion-safe:animate-spin mx-auto mb-4" />
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/90">Generating AI brief...</p>
                </div>
              ) : brief.status === "failed" ? (
                <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-4 print:hidden">
                  <div className="flex items-center gap-2 text-status-danger-700 dark:text-status-danger-300">
                    <AlertCircle className="h-5 w-5" />
                    <span>Brief generation failed: {brief.error_message}</span>
                  </div>
                  <button
                    onClick={generateBrief}
                    disabled={generatingBrief}
                    className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-status-danger-600 text-white rounded-xl hover:bg-status-danger-700"
                  >
                    Retry
                  </button>
                </div>
              ) : (
                <div className="space-y-6 print:break-inside-avoid">
                  {brief.brief_content && (
                    <div>
                      <h3 className="font-medium text-lsc-dark dark:text-earth-300 mb-2">Summary</h3>
                      <p className="text-lsc-dark/70 dark:text-lsc-cream/90 whitespace-pre-wrap">{brief.brief_content}</p>
                    </div>
                  )}

                  {brief.key_discussion_points && brief.key_discussion_points.length > 0 && (
                    <div className="print:break-inside-avoid">
                      <h3 className="font-medium text-lsc-dark dark:text-earth-300 mb-2">Key Discussion Points</h3>
                      <ul className="list-disc list-inside space-y-1 text-lsc-dark/70 dark:text-lsc-cream/90">
                        {brief.key_discussion_points.map((point, i) => (
                          <li key={i}>{point}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {brief.recommended_questions && brief.recommended_questions.length > 0 && (
                    <div className="print:break-inside-avoid">
                      <h3 className="font-medium text-lsc-dark dark:text-earth-300 mb-2">Questions to Consider</h3>
                      <ul className="list-disc list-inside space-y-1 text-lsc-dark/70 dark:text-lsc-cream/90">
                        {brief.recommended_questions.map((q, i) => (
                          <li key={i}>{q}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {brief.background_context && (
                    <div className="print:break-inside-avoid">
                      <h3 className="font-medium text-lsc-dark dark:text-earth-300 mb-2">Background Context</h3>
                      <p className="text-lsc-dark/70 dark:text-lsc-cream/90 whitespace-pre-wrap">{brief.background_context}</p>
                    </div>
                  )}

                  <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 pt-4 border-t border-lsc-border dark:border-earth-700 print:hidden">
                    Generated with {brief.model_used} in {brief.generation_time_ms}ms
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Sidebar - hidden on print */}
        <div className="space-y-6 print:hidden">
          {/* Checklist - Only for authenticated users */}
          {isAuthenticated && checklist.length > 0 && (
            <aside aria-label="Pre-meeting checklist" className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
              <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Pre-Meeting Checklist</h2>
              <ul className="space-y-3">
                {checklist.map((item, i) => (
                  <li key={i} className="flex items-start gap-3">
                    {item.completed ? (
                      <CheckCircle className="h-5 w-5 text-status-success-500 shrink-0 mt-0.5" />
                    ) : (
                      <div className={"h-5 w-5 rounded-full border-2 shrink-0 mt-0.5 " + (item.priority === "high" ? "border-status-danger-400" : "border-lsc-border")}></div>
                    )}
                    <span className={"text-sm " + (item.completed ? "text-lsc-dark/70 line-through" : "text-lsc-dark/70 dark:text-lsc-cream/90")}>
                      {item.item}
                    </span>
                  </li>
                ))}
              </ul>
            </aside>
          )}

          {/* Quick Links */}
          <nav aria-label="Meeting resources" className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
            <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Resources</h2>
            <div className="space-y-3">
              <a
                href={`${API_BASE}/board/meetings/${meetingId}/packet/pdf`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-4 py-2.5 bg-lsc-rose text-white rounded-xl text-sm font-semibold hover:bg-lsc-rose/90 transition-colors"
              >
                <Download className="w-4 h-4" />
                Download Board Packet
              </a>
              <Link to="/board/documents" className="block text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline">
                View Meeting Documents
              </Link>
              <Link to="/board/minutes" className="block text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline">
                Past Meeting Minutes
              </Link>
              <Link to="/board/members" className="block text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline">
                Board Members
              </Link>
            </div>
          </nav>
        </div>
      </div>
    </PageContainer>
  </>
  );
}