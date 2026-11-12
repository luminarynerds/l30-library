/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Users, Calendar, ChevronRight, Filter } from "lucide-react";
import api from "../../api/api";
import { API_BASE } from '@/api/types'
import { useBranding } from '@/contexts/BrandingContext'
import PageContainer from '@/components/layout/PageContainer'
import { getCurrentLocale } from '@/i18n'

interface Committee {
  id: number;
  name: string;
  description: string | null;
  committee_type: string;
  status: "active" | "inactive" | "dissolved";
  is_public: boolean;
  meeting_schedule: string | null;
  max_members: number | null;
  formation_date: string | null;
  dissolution_date: string | null;
}

interface BoardMemberInfo {
  id: number;
  full_name: string;
}

interface CommitteeMemberInfo {
  board_member_name?: string;
  board_member_id: number;
  role: string;
  is_active: boolean;
}

const committeeTypeLabels: Record<string, string> = {
  standing: "Standing Committee",
  ad_hoc: "Ad Hoc Committee",
  advisory: "Advisory Committee",
  executive: "Executive Committee",
  special: "Special Committee",
};

const statusLabels: Record<string, string> = {
  active: "Active",
  inactive: "Inactive",
  dissolved: "Dissolved",
};

const statusColors: Record<string, string> = {
  active: "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300",
  inactive: "bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300",
  dissolved: "bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70",
};

export default function BoardCommittees() {
  const branding = useBranding()
  const [committees, setCommittees] = useState<Committee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [filterType, setFilterType] = useState<string>("");
  const [committeeMembersMap, setCommitteeMembersMap] = useState<Record<number, BoardMemberInfo[]>>({});

  useEffect(() => {
    const fetchCommittees = async () => {
      setLoading(true);
      try {
        let url = `${API_BASE}/board/committees/with-members?include_inactive=${includeInactive}`;
        if (filterType) {
          url += `&committee_type=${encodeURIComponent(filterType)}`;
        }
        const response = await api.get(url);
        const committeeList = Array.isArray(response) ? response : [];
        setCommittees(committeeList);
        // Build member map from nested members data
        const memberMap: Record<number, BoardMemberInfo[]> = {};
        for (const c of committeeList) {
          if (c.members) {
            memberMap[c.id] = c.members
              .filter((m: CommitteeMemberInfo) => m.is_active)
              .map((m: CommitteeMemberInfo) => ({ id: m.board_member_id, full_name: m.board_member_name }));
          }
        }
        setCommitteeMembersMap(memberMap);
      } catch (_err) {
        setError("Unable to load committees");
        Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
      } finally {
        setLoading(false);
      }
    };
    fetchCommittees();
  }, [includeInactive, filterType]);

  const formatDate = (dateString: string | null) => {
    if (!dateString) return null;
    return new Date(dateString).toLocaleDateString(getCurrentLocale(), {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  const activeCommittees = committees.filter((c) => c.status === "active");
  const inactiveCommittees = committees.filter((c) => c.status !== "active");

  if (loading) {
    return (
      <>
        <div className="motion-safe:animate-pulse space-y-4">
          <div className="h-8 bg-lsc-cream dark:bg-lsc-brown rounded w-1/3"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-48 bg-lsc-cream dark:bg-lsc-brown rounded-xl"></div>
            ))}
          </div>
        </div>
      </>
    );
  }

  return (
    <>
    <PageContainer className="py-8">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4 mb-6">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-lsc-dark/70 dark:text-lsc-cream/60" />
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-3 py-1.5 border border-lsc-border dark:border-earth-700 rounded-lg text-sm bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          >
            <option value="">All Types</option>
            <option value="standing">Standing Committees</option>
            <option value="ad_hoc">Ad Hoc Committees</option>
            <option value="advisory">Advisory Committees</option>
            <option value="executive">Executive Committees</option>
            <option value="special">Special Committees</option>
          </select>
        </div>
        <label className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <input
            type="checkbox"
            checked={includeInactive}
            onChange={(e) => setIncludeInactive(e.target.checked)}
            className="rounded border-lsc-border dark:border-earth-700 text-lsc-rose focus:ring-lsc-rose"
          />
          Show inactive/dissolved committees
        </label>
      </div>

      {error ? (
        <div className="text-center py-12">
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{error}</p>
        </div>
      ) : committees.length === 0 ? (
        <div className="text-center py-12">
          <Users className="h-12 w-12 text-lsc-border mx-auto mb-4" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            No committees found matching your criteria.
          </p>
        </div>
      ) : (
        <>
          {/* Active Committees */}
          {activeCommittees.length > 0 && (
            <section className="mb-12">
              <h2 className="font-serif text-2xl font-semibold mb-4 text-lsc-dark dark:text-lsc-cream">
                Active Committees
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {activeCommittees.map((committee) => (
                  <CommitteeCard key={committee.id} committee={committee} formatDate={formatDate} members={committeeMembersMap[committee.id]} />
                ))}
              </div>
            </section>
          )}

          {/* Inactive/Dissolved Committees */}
          {includeInactive && inactiveCommittees.length > 0 && (
            <section>
              <h2 className="font-serif text-2xl font-semibold mb-4 text-lsc-dark dark:text-lsc-cream">
                Inactive & Dissolved Committees
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {inactiveCommittees.map((committee) => (
                  <CommitteeCard key={committee.id} committee={committee} formatDate={formatDate} members={committeeMembersMap[committee.id]} />
                ))}
              </div>
            </section>
          )}
        </>
      )}

      <div className="mt-12 bg-lsc-cream dark:bg-earth-800 rounded-xl p-6">
        <h2 className="font-serif text-lg font-semibold mb-4 text-lsc-dark dark:text-lsc-cream">
          About Board Committees
        </h2>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          Board committees meet regularly to review policies, discuss initiatives,
          and make recommendations to the full board. Committee meetings are
          generally open to the public unless otherwise noted.
        </p>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          For questions about committee activities, please contact{" "}
          <a
            href={`mailto:${branding.contact_email}`}
            className="text-lsc-rose hover:underline"
          >
            {branding.contact_email}
          </a>
          .
        </p>
      </div>
    </PageContainer>
    </>
  );
}

function CommitteeCard({
  committee,
  formatDate,
  members,
}: {
  committee: Committee;
  formatDate: (date: string | null) => string | null;
  members?: BoardMemberInfo[] | undefined;
}) {
  return (
    <Link
      to={`/board/committees/${committee.id}`}
      className={"block bg-lsc-white dark:bg-earth-800 rounded-xl shadow hover:shadow-md transition-shadow p-6 " +
        (committee.status !== "active" ? "opacity-75" : "")}
    >
      <div className="flex justify-between items-start mb-3">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          {committee.name}
        </h3>
        <span className={"inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium " +
          statusColors[committee.status]}>
          {statusLabels[committee.status]}
        </span>
      </div>

      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream mb-3">
        {committeeTypeLabels[committee.committee_type] || committee.committee_type}
      </span>

      {committee.description && (
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4 line-clamp-2" title={committee.description}>
          {committee.description}
        </p>
      )}

      <div className="space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        {committee.meeting_schedule && (
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            <span>{committee.meeting_schedule}</span>
          </div>
        )}
        {committee.max_members && (
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4" />
            <span>Up to {committee.max_members} members</span>
          </div>
        )}
        {committee.formation_date && (
          <div className="text-xs">
            Formed: {formatDate(committee.formation_date)}
          </div>
        )}
        {committee.dissolution_date && (
          <div className="text-xs">
            Dissolved: {formatDate(committee.dissolution_date)}
          </div>
        )}
      </div>

      {members && members.length > 0 && (
        <div className="mt-3 pt-3 border-t border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            <Users className="h-3.5 w-3.5 flex-shrink-0" />
            <span>
              {members.slice(0, 3).map(m => m.full_name).join(", ")}
              {members.length > 3 && ` +${members.length - 3} more`}
            </span>
          </div>
        </div>
      )}

      <div className="flex items-center justify-end mt-4 text-lsc-rose">
        <span className="text-sm">View Details</span>
        <ChevronRight className="h-4 w-4 ml-1" />
      </div>
    </Link>
  );
}