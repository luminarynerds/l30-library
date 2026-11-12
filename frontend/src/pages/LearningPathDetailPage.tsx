/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useState, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { LearningPathDetail } from "../components/learning-paths/LearningPathDetail";
import LearningPathRoadmap, { type PathStep } from "../components/learning-paths/LearningPathRoadmap";
import CohortPanel from "../components/learning-paths/CohortPanel";
import { useAuth } from "../contexts/AuthContext";
import { useOrganizationFeatures } from "../contexts/OrganizationFeaturesContext";
import { getLearningPath, enrollInLearningPath, getWaitlistStatus, joinWaitlist, type LearningPathDetail as LearningPathDetailType } from "../api/learning-paths-api";
import { friendlyErrorMessage } from '@/utils/friendlyError'
import { Button } from '@/components/ui/Button'
import { ErrorAlert } from '@/components/ui/ErrorAlert'
import PageContainer from '@/components/layout/PageContainer'

export default function LearningPathDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { isFeatureEnabled } = useOrganizationFeatures();
  const cohortEnabled = isFeatureEnabled('cohort_enabled');
  const [path, setPath] = useState<LearningPathDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [enrolling, setEnrolling] = useState(false);
  const [waitlistJoined, setWaitlistJoined] = useState(false);
  const [waitlistCount, setWaitlistCount] = useState(0);

  const fetchPath = async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const data = await getLearningPath(Number(id));
      setPath(data);

      if (data.status !== 'published') {
        try {
          const wl = await getWaitlistStatus(Number(id));
          setWaitlistJoined(wl.joined);
          setWaitlistCount(wl.waitlist_count);
        } catch {
          // Waitlist fetch is non-critical
        }
      }
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
      setError(friendlyErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (id) fetchPath();
  }, [id]);

  const handleEnroll = async () => {
    if (!id || enrolling) return;

    try {
      setEnrolling(true);
      await enrollInLearningPath(Number(id));
      const data = await getLearningPath(Number(id));
      setPath(data);
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
      toast.error(friendlyErrorMessage(err));
    } finally {
      setEnrolling(false);
    }
  };

  const handleJoinWaitlist = async () => {
    if (!id) return;
    try {
      const result = await joinWaitlist(Number(id));
      setWaitlistJoined(result.joined);
      setWaitlistCount(result.waitlist_count);
      toast.success("You'll be notified when this path launches!");
    } catch (err: unknown) {
      toast.error(friendlyErrorMessage(err));
    }
  };

  const roadmapSteps: PathStep[] = useMemo(() => {
    if (!path?.courses || !path.is_enrolled) return []

    const sorted = [...path.courses].sort((a, b) => a.sort_order - b.sort_order)
    let foundInProgress = false

    return sorted.map((course) => {
      let status: PathStep['status']

      if (course.is_completed) {
        status = 'completed'
      } else if (!course.can_access) {
        status = 'locked'
      } else if (!foundInProgress) {
        status = 'in_progress'
        foundInProgress = true
      } else {
        status = 'available'
      }

      return {
        courseId: course.course_id,
        title: course.course_title || `Course ${course.course_id}`,
        status,
      }
    })
  }, [path])

  if (loading) {
    return (
      <PageContainer className="py-8">
        <div className="motion-safe:animate-pulse">
          <div className="h-8 bg-earth-200 dark:bg-earth-600 rounded w-1/3 mb-4"></div>
          <div className="h-64 bg-earth-200 dark:bg-earth-600 rounded"></div>
        </div>
      </PageContainer>
    );
  }

  if (error || !path) {
    return (
      <PageContainer className="py-8">
        <ErrorAlert
          title="Couldn't load learning path"
          message={error || "Learning path not found"}
          onRetry={fetchPath}
          className="mb-4"
        />
        <Button variant="tertiary"
          onClick={() => navigate("/learning-paths")}
        >
          ← Back to Learning Paths
        </Button>
      </PageContainer>
    );
  }

  return (
    <PageContainer className="py-8">
      <Button variant="tertiary"
        onClick={() => navigate("/learning-paths")}
      >
        ← Back to Learning Paths
      </Button>

      <LearningPathDetail
        title={path.title}
        description={path.description}
        difficulty={path.difficulty}
        total_minutes={path.total_minutes ?? null}
        total_courses={path.total_courses}
        required_courses={path.required_courses}
        optional_courses={path.optional_courses}
        courses={path.courses as unknown as React.ComponentProps<typeof LearningPathDetail>['courses']}
        is_enrolled={path.is_enrolled}
        enrollment_progress={path.enrollment_progress}
        status={path.status}
        isAuthenticated={isAuthenticated}
        onEnroll={handleEnroll}
        onJoinWaitlist={handleJoinWaitlist}
        waitlistJoined={waitlistJoined}
        waitlistCount={waitlistCount}
      />

      {roadmapSteps.length > 0 && (
        <div className="mt-6 bg-lsc-white dark:bg-earth-800 rounded-lg shadow-md p-8 border border-lsc-border dark:border-earth-700 max-w-4xl mx-auto">
          <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">Your Progress</h2>
          <LearningPathRoadmap steps={roadmapSteps} />
        </div>
      )}

      {cohortEnabled && (
        <CohortPanel pathId={Number(id)} isAuthenticated={isAuthenticated} />
      )}
    </PageContainer>
  );
}
