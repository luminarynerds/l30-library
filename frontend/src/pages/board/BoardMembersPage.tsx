/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useState } from "react";
import { LayoutGrid, List } from "lucide-react";
import api from "../../api/api";
import BoardMemberGallery from "../../components/board/BoardMemberGallery";
import { API_BASE } from '@/api/types'
import { useBranding } from '@/contexts/BrandingContext'
import { t, getCurrentLocale } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

interface BoardMember {
  id: number;
  full_name: string;
  email?: string;
  position: string;
  term_start_date: string;
  term_end_date?: string;
  is_current: boolean;
  bio?: string;
  photo_url?: string;
  public_email?: string;
  office_hours?: string;
}

interface CommitteeSummary {
  id: number;
  name: string;
}

interface CommitteeMemberLink {
  board_member_id: number;
  committee_id: number;
  is_active: boolean;
}

const positionOrder: Record<string, number> = {
  president: 1,
  vice_president: 2,
  secretary: 3,
  treasurer: 4,
  member: 5,
};

const positionLabels: Record<string, string> = {
  president: "President",
  vice_president: "Vice President",
  secretary: "Secretary",
  treasurer: "Treasurer",
  member: "Trustee",
};

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString(getCurrentLocale(), {
    year: "numeric",
    month: "long",
  });
}

type ViewMode = "gallery" | "list";

export default function BoardMembersPage() {
  const branding = useBranding()
  const [members, setMembers] = useState<BoardMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [memberCommittees, setMemberCommittees] = useState<Record<number, CommitteeSummary[]>>({});

  useEffect(() => {
    const fetchMembers = async () => {
      try {
        const response = await api.get(`${API_BASE}/board/members`);
        const sortedMembers = response.sort(
          (a: BoardMember, b: BoardMember) =>
            (positionOrder[a.position] || 99) - (positionOrder[b.position] || 99)
        );
        setMembers(sortedMembers);
      } catch (_err) {
        setError("Unable to load board members");
        Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
      } finally {
        setLoading(false);
      }
    };
    const fetchCommitteeLinks = async () => {
      try {
        const committees: Array<{ id: number; name: string; members: CommitteeMemberLink[] }> =
          await api.get(`${API_BASE}/board/committees/with-members`);
        const map: Record<number, CommitteeSummary[]> = {};
        for (const c of committees) {
          for (const m of c.members) {
            if (m.is_active) {
              if (!map[m.board_member_id]) map[m.board_member_id] = [];
              map[m.board_member_id]!.push({ id: c.id, name: c.name });
            }
          }
        }
        setMemberCommittees(map);
      } catch { /* non-critical, silently fail */ }
    };
    fetchMembers();
    fetchCommitteeLinks();
  }, []);

  if (loading) {
    return (
      <PageContainer className="py-8">
        <div className="motion-safe:animate-pulse space-y-4">
          <div className="h-8 bg-earth-200 dark:bg-earth-600 rounded w-1/3"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-64 bg-earth-200 dark:bg-earth-600 rounded"></div>
            ))}
          </div>
        </div>
      </PageContainer>
    );
  }

  return (
    <>
    <PageContainer className="py-8">
      {/* Page header */}
      <div className="mb-8 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Board of Trustees</h1>
          <p className="text-earth-600 dark:text-earth-200 mt-2 max-w-2xl">
            The {branding.library_name} is governed by a Board of Trustees who
            volunteer their time to oversee library operations and ensure the
            library serves our community effectively.
          </p>
        </div>

        {/* View toggle */}
        {members.length > 0 && (
          <div
            className="flex items-center gap-1 p-1 bg-lsc-cream dark:bg-earth-700 rounded-lg self-start flex-shrink-0"
            role="group"
            aria-label={t('aria.boardMembers.viewMode')}
          >
            <button
              onClick={() => setViewMode("gallery")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                viewMode === "gallery"
                  ? "bg-lsc-white dark:bg-earth-600 text-lsc-dark dark:text-lsc-cream shadow-sm"
                  : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
              }`}
              aria-pressed={viewMode === "gallery"}
            >
              <LayoutGrid className="w-4 h-4" aria-hidden="true" />
              Gallery
            </button>
            <button
              onClick={() => setViewMode("list")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                viewMode === "list"
                  ? "bg-lsc-white dark:bg-earth-600 text-lsc-dark dark:text-lsc-cream shadow-sm"
                  : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
              }`}
              aria-pressed={viewMode === "list"}
            >
              <List className="w-4 h-4" aria-hidden="true" />
              List
            </button>
          </div>
        )}
      </div>

      {error ? (
        <div className="text-center py-12">
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{error}</p>
        </div>
      ) : members.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Board member information will be available soon.
          </p>
        </div>
      ) : viewMode === "gallery" ? (
        <BoardMemberGallery members={members.map(m => ({ ...m, committees: memberCommittees[m.id] }))} />
      ) : (
        /* List view — original table-style layout */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {members.map((member) => (
            <div key={member.id} className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-md overflow-hidden border border-lsc-border dark:border-earth-700">
              <div className="p-6">
                {member.photo_url && (
                  <img
                    src={member.photo_url}
                    alt={member.full_name}
                    className="w-24 h-24 rounded-full mx-auto mb-4 object-cover"
                  />
                )}
                <h2 className="font-serif text-lg font-semibold text-center text-lsc-dark dark:text-lsc-cream">{member.full_name}</h2>
                <div className="text-center mt-1">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300">
                    {positionLabels[member.position] || member.position}
                  </span>
                </div>
                <div className="mt-4 text-sm text-earth-600 dark:text-earth-200 space-y-2">
                  {member.bio && <p>{member.bio}</p>}
                  <p>
                    <span className="font-medium">Term:</span>{" "}
                    {formatDate(member.term_start_date)}
                    {member.term_end_date && ` - ${formatDate(member.term_end_date)}`}
                  </p>
                  {member.public_email && (
                    <p>
                      <span className="font-medium">Email:</span>{" "}
                      <a
                        href={`mailto:${member.public_email}`}
                        className="text-lsc-rose hover:underline"
                      >
                        {member.public_email}
                      </a>
                    </p>
                  )}
                  {member.office_hours && (
                    <p>
                      <span className="font-medium">Office Hours:</span>{" "}
                      {member.office_hours}
                    </p>
                  )}
                  {(memberCommittees[member.id]?.length ?? 0) > 0 && (
                    <div className="flex flex-wrap gap-1 pt-1">
                      {memberCommittees[member.id]!.map((c) => (
                        <a
                          key={c.id}
                          href={`/board/committees/${c.id}`}
                          className="text-xs bg-lsc-cream dark:bg-earth-700 text-lsc-dark/80 dark:text-lsc-cream/80 px-2 py-0.5 rounded hover:bg-lsc-rose/20 dark:hover:bg-lsc-rose/30 transition-colors"
                        >
                          {c.name}
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* About the Board */}
      <div className="mt-12 bg-lsc-cream dark:bg-earth-700/50 rounded-xl p-6">
        <h2 className="font-serif text-lg font-semibold mb-4 text-lsc-dark dark:text-lsc-cream">About the Board</h2>
        <p className="text-earth-600 dark:text-earth-200 mb-4">
          Board meetings are open to the public and held monthly. Check our{" "}
          <a href="/board/meetings" className="text-lsc-rose hover:underline">
            meeting schedule
          </a>{" "}
          for upcoming dates and agendas.
        </p>
        <p className="text-earth-600 dark:text-earth-200">
          If you have questions or would like to contact the board, please email{" "}
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