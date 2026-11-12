/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { API_BASE } from '@/api/types';
import {
  ChevronLeft,
  Users,
  Calendar,
  FileText,
  Clock,
  MapPin,
  Video,
  User,
  AlertCircle,
} from "lucide-react";
import api from "../../api/api";
import PageContainer from '@/components/layout/PageContainer'
import { getCurrentLocale } from '@/i18n'

interface Committee {
  id: number;
  name: string;
  description: string | null;
  committee_type: string;
  status: "active" | "inactive" | "dissolved";
  is_public: boolean;
  charter_text: string | null;
  meeting_schedule: string | null;
  max_members: number | null;
  min_members: number | null;
  formation_date: string | null;
  dissolution_date: string | null;
  dissolution_reason: string | null;
}

interface CommitteeMember {
  id: number;
  committee_id: number;
  board_member_id: number;
  role: string;
  appointed_date: string;
  term_end_date: string | null;
  is_active: boolean;
  board_member_name?: string;
  board_member_position?: string;
}

interface CommitteeMeeting {
  id: number;
  meeting_type: string;
  title: string;
  description: string | null;
  scheduled_date: string;
  start_time: string | null;
  end_time: string | null;
  location: string | null;
  is_virtual: boolean;
  virtual_meeting_url: string | null;
  is_cancelled: boolean;
}

interface CommitteeDocument {
  id: number;
  title: string;
  description: string | null;
  document_type: string;
  file_url: string | null;
  published_date: string | null;
}

const committeeTypeLabels: Record<string, string> = {
  standing: "Standing Committee",
  ad_hoc: "Ad Hoc Committee",
  advisory: "Advisory Committee",
  executive: "Executive Committee",
  special: "Special Committee",
};

const roleLabels: Record<string, string> = {
  chair: "Chair",
  vice_chair: "Vice Chair",
  secretary: "Secretary",
  member: "Member",
};

const roleOrder: Record<string, number> = {
  chair: 1,
  vice_chair: 2,
  secretary: 3,
  member: 4,
};

const statusColors: Record<string, string> = {
  active: "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300",
  inactive: "bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300",
  dissolved: "bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70",
};

export default function BoardCommitteeDetail() {
  const { committeeId } = useParams();
  const [committee, setCommittee] = useState<Committee | null>(null);
  const [members, setMembers] = useState<CommitteeMember[]>([]);
  const [meetings, setMeetings] = useState<CommitteeMeeting[]>([]);
  const [documents, setDocuments] = useState<CommitteeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "members" | "meetings" | "documents">("overview");

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch committee details
        const committeeData = await api.get(`${API_BASE}/board/committees/${committeeId}`);
        setCommittee(committeeData);

        // Fetch committee members
        try {
          const membersData = await api.get(`${API_BASE}/board/committees/${committeeId}/members`);
          const sortedMembers = (Array.isArray(membersData) ? membersData : []).sort(
            (a: CommitteeMember, b: CommitteeMember) =>
              (roleOrder[a.role] || 99) - (roleOrder[b.role] || 99)
          );
          setMembers(sortedMembers);
        } catch {
          // Members might not be available
        }

        // Fetch upcoming meetings
        try {
          const meetingsData = await api.get(
            `${API_BASE}/board/committees/${committeeId}/meetings?upcoming_only=false&limit=10`
          );
          setMeetings(Array.isArray(meetingsData) ? meetingsData : []);
        } catch {
          // Meetings might not be available
        }

        // Fetch documents
        try {
          const docsData = await api.get(`${API_BASE}/board/committees/${committeeId}/documents?limit=20`);
          setDocuments(Array.isArray(docsData) ? docsData : []);
        } catch {
          // Documents might not be available
        }
      } catch (_err) {
        Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
        setError("Unable to load committee details");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [committeeId]);

  const formatDate = (dateString: string | null) => {
    if (!dateString) return null;
    return new Date(dateString).toLocaleDateString(getCurrentLocale(), {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(getCurrentLocale(), {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  const formatTime = (dateString: string | null) => {
    if (!dateString) return null;
    return new Date(dateString).toLocaleTimeString(getCurrentLocale(), {
      hour: "numeric",
      minute: "2-digit",
    });
  };

  if (loading) {
    return (
      <>
      <PageContainer className="py-8">
        <div className="motion-safe:animate-pulse space-y-4">
          <div className="h-8 bg-lsc-cream dark:bg-lsc-brown rounded w-1/3"></div>
          <div className="h-64 bg-lsc-cream dark:bg-lsc-brown rounded-xl"></div>
        </div>
      </PageContainer>
      </>
    );
  }

  if (error || !committee) {
    return (
      <>
      <PageContainer className="py-8">
        <Link
          to="/board/committees"
          className="flex items-center gap-2 text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream mb-4"
        >
          <ChevronLeft className="h-4 w-4" /> Back to Committees
        </Link>
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-6">
          <div className="flex items-center gap-2 text-status-danger-700 dark:text-status-danger-300">
            <AlertCircle className="h-5 w-5" />
            <span>{error || "Committee not found"}</span>
          </div>
        </div>
      </PageContainer>
      </>
    );
  }

  const upcomingMeetings = meetings.filter(
    (m) => new Date(m.scheduled_date) >= new Date() && !m.is_cancelled
  );
  const pastMeetings = meetings.filter(
    (m) => new Date(m.scheduled_date) < new Date() || m.is_cancelled
  );

  return (
    <>
    <PageContainer className="py-8">
      <Link
        to="/board/committees"
        className="flex items-center gap-2 text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream mb-4"
      >
        <ChevronLeft className="h-4 w-4" /> Back to Committees
      </Link>

      {/* Header */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6 mb-6">
        <div className="flex flex-wrap justify-between items-start gap-4 mb-4">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              {committee.name}
            </h1>
            <div className="flex flex-wrap items-center gap-2 mt-2">
              <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream">
                {committeeTypeLabels[committee.committee_type] || committee.committee_type}
              </span>
              <span className={"inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium " +
                statusColors[committee.status]}>
                {committee.status.charAt(0).toUpperCase() + committee.status.slice(1)}
              </span>
            </div>
          </div>
          {committee.meeting_schedule && (
            <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              {committee.meeting_schedule}
            </div>
          )}
        </div>

        {committee.description && (
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{committee.description}</p>
        )}

        {committee.status === "dissolved" && committee.dissolution_reason && (
          <div className="mt-4 p-4 bg-earth-50 dark:bg-earth-700 rounded-xl">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              <strong>Dissolved:</strong> {formatDate(committee.dissolution_date)}
            </p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              <strong>Reason:</strong> {committee.dissolution_reason}
            </p>
          </div>
        )}

        {committee.formation_date && (
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-4">
            Formed: {formatDate(committee.formation_date)}
          </p>
        )}
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-lsc-border dark:border-earth-700 mb-6 overflow-x-auto">
        <button
          onClick={() => setActiveTab("overview")}
          className={"px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap " +
            (activeTab === "overview"
              ? "border-lsc-rose text-lsc-rose"
              : "border-transparent text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream")}
        >
          Overview
        </button>
        <button
          onClick={() => setActiveTab("members")}
          className={"px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap " +
            (activeTab === "members"
              ? "border-lsc-rose text-lsc-rose"
              : "border-transparent text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream")}
        >
          Members ({members.filter((m) => m.is_active).length})
        </button>
        <button
          onClick={() => setActiveTab("meetings")}
          className={"px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap " +
            (activeTab === "meetings"
              ? "border-lsc-rose text-lsc-rose"
              : "border-transparent text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream")}
        >
          Meetings ({meetings.length})
        </button>
        <button
          onClick={() => setActiveTab("documents")}
          className={"px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap " +
            (activeTab === "documents"
              ? "border-lsc-rose text-lsc-rose"
              : "border-transparent text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream")}
        >
          Documents ({documents.length})
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === "overview" && (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            {/* Charter */}
            {committee.charter_text && (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
                  Committee Charter
                </h2>
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-pre-wrap">
                    {committee.charter_text}
                  </p>
                </div>
              </div>
            )}

            {/* Upcoming Meetings Preview */}
            {upcomingMeetings.length > 0 && (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
                  Upcoming Meetings
                </h2>
                <div className="space-y-4">
                  {upcomingMeetings.slice(0, 3).map((meeting) => (
                    <MeetingCard key={meeting.id} meeting={meeting} formatDateTime={formatDateTime} formatTime={formatTime} />
                  ))}
                </div>
                {upcomingMeetings.length > 3 && (
                  <button
                    onClick={() => setActiveTab("meetings")}
                    className="mt-4 text-sm text-lsc-rose hover:underline"
                  >
                    View all {upcomingMeetings.length} upcoming meetings
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Committee Info */}
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
                Committee Info
              </h2>
              <dl className="space-y-3 text-sm">
                <div>
                  <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">Type</dt>
                  <dd className="text-lsc-dark dark:text-lsc-cream">
                    {committeeTypeLabels[committee.committee_type] || committee.committee_type}
                  </dd>
                </div>
                {committee.min_members && (
                  <div>
                    <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">Minimum Members</dt>
                    <dd className="text-lsc-dark dark:text-lsc-cream">{committee.min_members}</dd>
                  </div>
                )}
                {committee.max_members && (
                  <div>
                    <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">Maximum Members</dt>
                    <dd className="text-lsc-dark dark:text-lsc-cream">{committee.max_members}</dd>
                  </div>
                )}
                <div>
                  <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">Current Members</dt>
                  <dd className="text-lsc-dark dark:text-lsc-cream">
                    {members.filter((m) => m.is_active).length}
                  </dd>
                </div>
              </dl>
            </div>

            {/* Quick Links */}
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
                Related Links
              </h2>
              <div className="space-y-2">
                <Link
                  to="/board/members"
                  className="block text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline"
                >
                  Board Members
                </Link>
                <Link
                  to="/board/meetings"
                  className="block text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline"
                >
                  All Board Meetings
                </Link>
                <Link
                  to="/board/documents"
                  className="block text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline"
                >
                  Board Documents
                </Link>
                <Link
                  to="/board/minutes"
                  className="block text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline"
                >
                  Meeting Minutes
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === "members" && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
          <div className="flex items-center gap-2 mb-6">
            <Users className="h-5 w-5 text-lsc-rose" />
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              Committee Members
            </h2>
          </div>

          {members.length === 0 ? (
            <div className="text-center py-8">
              <User className="h-12 w-12 text-lsc-border mx-auto mb-4" />
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                No member information available.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {members
                .filter((m) => m.is_active)
                .map((member) => (
                  <div
                    key={member.id}
                    className="p-4 bg-lsc-cream/50 dark:bg-earth-700 rounded-xl"
                  >
                    <Link to={`/board/members#member-${member.board_member_id}`} className="font-medium text-lsc-rose dark:text-lsc-rose-light hover:underline">
                      {member.board_member_name || `Board Member #${member.board_member_id}`}
                    </Link>
                    <div className="text-sm text-lsc-rose font-medium">
                      {roleLabels[member.role] || member.role}
                    </div>
                    {member.board_member_position && (
                      <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                        {member.board_member_position}
                      </div>
                    )}
                    <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                      Since {formatDate(member.appointed_date)}
                      {member.term_end_date && (
                        <span> (until {formatDate(member.term_end_date)})</span>
                      )}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "meetings" && (
        <div className="space-y-6">
          {/* Upcoming Meetings */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
            <div className="flex items-center gap-2 mb-6">
              <Calendar className="h-5 w-5 text-lsc-rose" />
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                Upcoming Meetings
              </h2>
            </div>

            {upcomingMeetings.length === 0 ? (
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 py-4">
                No upcoming meetings scheduled.
              </p>
            ) : (
              <div className="space-y-4">
                {upcomingMeetings.map((meeting) => (
                  <MeetingCard key={meeting.id} meeting={meeting} formatDateTime={formatDateTime} formatTime={formatTime} />
                ))}
              </div>
            )}
          </div>

          {/* Past Meetings */}
          {pastMeetings.length > 0 && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-6">
                Past Meetings
              </h2>
              <div className="space-y-4">
                {pastMeetings.map((meeting) => (
                  <MeetingCard key={meeting.id} meeting={meeting} formatDateTime={formatDateTime} formatTime={formatTime} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === "documents" && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
          <div className="flex items-center gap-2 mb-6">
            <FileText className="h-5 w-5 text-lsc-rose" />
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              Committee Documents
            </h2>
          </div>

          {documents.length === 0 ? (
            <div className="text-center py-8">
              <FileText className="h-12 w-12 text-lsc-border mx-auto mb-4" />
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                No documents available for this committee.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className="p-4 bg-lsc-cream/50 dark:bg-earth-700 rounded-xl flex items-start gap-4"
                >
                  <FileText className="h-8 w-8 text-lsc-rose shrink-0" />
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">
                      {doc.title}
                    </h3>
                    {doc.description && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                        {doc.description}
                      </p>
                    )}
                    <div className="flex items-center gap-3 mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      <span className="capitalize">{doc.document_type?.replace(/_/g, " ") ?? 'document'}</span>
                      {doc.published_date && (
                        <span>Published: {formatDate(doc.published_date)}</span>
                      )}
                    </div>
                  </div>
                  {doc.file_url && (
                    <a
                      href={doc.file_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-1.5 text-sm bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors"
                    >
                      View
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </PageContainer>
    </>
  );
}

function MeetingCard({
  meeting,
  formatDateTime,
  formatTime,
}: {
  meeting: CommitteeMeeting;
  formatDateTime: (date: string) => string;
  formatTime: (date: string | null) => string | null;
}) {
  return (
    <div className={"p-4 bg-lsc-cream/50 dark:bg-earth-700 rounded-xl " + (meeting.is_cancelled ? "opacity-60" : "")}>
      <div className="flex justify-between items-start">
        <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">{meeting.title}</h3>
        {meeting.is_cancelled && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300">
            Cancelled
          </span>
        )}
      </div>
      <div className="space-y-1 mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4" />
          <span>{formatDateTime(meeting.scheduled_date)}</span>
        </div>
        {meeting.start_time && (
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4" />
            <span>
              {formatTime(meeting.start_time)}
              {meeting.end_time && ` - ${formatTime(meeting.end_time)}`}
            </span>
          </div>
        )}
        {meeting.location && (
          <div className="flex items-center gap-2">
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
              Join Virtual Meeting
            </a>
          </div>
        )}
      </div>
      {meeting.description && (
        <p className="mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {meeting.description}
        </p>
      )}
      <Link
        to={`/board/meetings/${meeting.id}`}
        className="inline-block mt-2 text-sm text-lsc-rose hover:underline"
      >
        View Details
      </Link>
    </div>
  );
}