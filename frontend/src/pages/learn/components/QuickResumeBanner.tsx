/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from "react-router-dom";
import { Play, ChevronRight } from "lucide-react";
import { useTranslation } from "@/i18n";
import type { LastLesson } from "@/types/learning";

interface QuickResumeBannerProps {
  lastLesson: LastLesson;
}

export function QuickResumeBanner({ lastLesson }: QuickResumeBannerProps) {
  const { t } = useTranslation();

  return (
    <Link
      to={`/learn/course/${lastLesson.courseId}/lesson/${lastLesson.lessonId}`}
      className="block mb-6 bg-gradient-to-r from-lsc-rose/10 to-lsc-brown/10 dark:from-lsc-rose/20 dark:to-lsc-brown/20 rounded-xl border border-lsc-rose/30 dark:border-lsc-rose/40 p-4 hover:border-lsc-rose dark:hover:border-lsc-rose transition-all group"
    >
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 rounded-full bg-lsc-rose/20 dark:bg-lsc-rose/30 flex items-center justify-center flex-shrink-0 group-hover:bg-lsc-rose/30 transition-colors">
          <Play aria-hidden="true" className="w-5 h-5 text-lsc-rose ml-0.5" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t("learn.pickUpWhereYouLeft")}</p>
          <h3 className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={lastLesson.lessonTitle}>{lastLesson.lessonTitle}</h3>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 truncate" title={`${t("learn.from", "from")} ${lastLesson.courseTitle}`}>{t("learn.from", "from")} {lastLesson.courseTitle}</p>
        </div>
        <div className="flex-shrink-0">
          <span className="inline-flex items-center gap-1 px-4 py-2 bg-lsc-rose text-white rounded-xl font-medium text-sm group-hover:bg-lsc-rose/90">
            {t("learn.resume", "Resume")} <ChevronRight className="w-4 h-4" />
          </span>
        </div>
      </div>
    </Link>
  );
}
