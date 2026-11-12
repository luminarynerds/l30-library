/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { GraduationCap } from "lucide-react";
import { LearningPathList } from "../components/learning-paths/LearningPathList";
import { useAuth } from "../contexts/AuthContext";
import { getLearningPaths, type LearningPath } from "../api/learning-paths-api";
import { friendlyErrorMessage } from '@/utils/friendlyError'
import { useTranslation } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

export default function LearningPathsPage() {
  const { t } = useTranslation()
  const { isAuthenticated } = useAuth();
  const [paths, setPaths] = useState<LearningPath[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPaths = async () => {
      try {
        setLoading(true);
        const [published, drafts] = await Promise.all([
          getLearningPaths({ status: "published" }),
          getLearningPaths({ status: "draft" }),
        ]);
        const data = [...published, ...drafts];
        setPaths(data);
      } catch (err: unknown) {
        Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
        setError(friendlyErrorMessage(err));
      } finally {
        setLoading(false);
      }
    };

    fetchPaths();
  }, []);

  return (
    <PageContainer className="py-8">
      <div className="mb-8">
        <h1 className="font-serif text-4xl font-bold text-lsc-dark dark:text-lsc-cream mb-2">Learning Paths</h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('learningPaths.discoverGuidedLearningPathsTo')}</p>
      </div>

      {/* Registration prompt for unauthenticated users */}
      {!isAuthenticated && (
        <div className="bg-lsc-rose/10 dark:bg-lsc-rose/20 border border-lsc-rose/30 rounded-xl p-4 mb-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <GraduationCap aria-hidden="true" className="w-8 h-8 text-lsc-rose flex-shrink-0" />
            <p className="text-lsc-dark dark:text-lsc-cream">
              <span className="font-medium">{t('learningPaths.readyToStartALearning')}</span>{' '}
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('learningPaths.registerForFreeToEnroll')}</span>
            </p>
          </div>
          <Link
            to="/account"
            className="inline-flex items-center gap-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white px-5 py-2 rounded-xl font-medium whitespace-nowrap"
          >
            Sign Up
          </Link>
        </div>
      )}

      {error && (
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-300 dark:border-status-danger-700 text-status-danger-800 dark:text-status-danger-300 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      <LearningPathList paths={paths} loading={loading} />
    </PageContainer>
  );
}
