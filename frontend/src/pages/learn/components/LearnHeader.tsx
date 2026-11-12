/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from "react-router-dom";
import { GraduationCap, Sparkles, Settings } from "lucide-react";
import { useTranslation } from "@/i18n";
import { useBranding } from "@/contexts/BrandingContext";

interface LearnHeaderProps {
  isAuthenticated: boolean;
  firstName?: string | undefined;
}

const linkCls =
  "text-lsc-rose hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded";

export function LearnHeader({ isAuthenticated, firstName }: LearnHeaderProps) {
  const { t } = useTranslation();
  const branding = useBranding();
  const telHref = `tel:${branding.phone.replace(/[^0-9+]/g, "")}`;

  return (
    <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 mb-8">
      <div>
        {isAuthenticated ? (
          <>
            <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              {t("learn.welcomeBack", "Welcome back")}, {firstName}
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t("learn.continueYourLearningJourney")}</p>
          </>
        ) : (
          <>
            <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              {t("learn.libraryLearningCenter", "Library Learning Center")}
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              {t("learn.freeCoursesDesigned", "Free courses designed with your learning style in mind")}
            </p>
            <p className="text-lsc-dark/80 dark:text-lsc-cream/80 mt-3 max-w-xl">
              {t("learn.browseFreelyBlurb", "Browse our courses freely. Create a free account to enroll in classes and track your progress.")}
            </p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
              {t("learn.alreadyHaveAccount", "Already have an account?")}{" "}
              <Link to="/account" className={linkCls}>{t("learn.signIn", "Sign in")}</Link>
              {" · "}
              {t("learn.preferToTalk", "Prefer to talk it through?")}{" "}
              {branding.phone && (
                <>
                  <a href={telHref} className={linkCls}>{t("learn.callUs", "Call us")}</a>
                  {" · "}
                </>
              )}
              <Link to="/ask-librarian" className={linkCls}>{t("navigation.askALibrarian", "Ask a Librarian")}</Link>
            </p>
          </>
        )}
      </div>
      <div className="flex flex-wrap gap-3 md:justify-end flex-shrink-0">
        {isAuthenticated ? (
          <>
            <Link
              to="/account?tab=settings"
              aria-label={t("learn.settings", "Settings")}
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream rounded-xl font-medium hover:bg-lsc-cream dark:hover:bg-lsc-brown/90"
            >
              <Settings aria-hidden="true" className="w-5 h-5" />
              <span className="hidden sm:inline">{t("learn.settings", "Settings")}</span>
            </Link>
            <Link
              to="/learn/catalog"
              className="inline-flex items-center gap-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white px-6 py-2.5 rounded-xl font-medium"
            >
              <Sparkles aria-hidden="true" className="w-5 h-5" />
              {t("learn.browseCourses", "Browse Courses")}
            </Link>
          </>
        ) : (
          <>
            <Link
              to="/account"
              className="inline-flex items-center gap-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white px-6 py-2.5 rounded-xl font-medium"
            >
              <GraduationCap aria-hidden="true" className="w-5 h-5" />
              {t("learn.createFreeAccount", "Create Free Account")}
            </Link>
            <Link
              to="/learn/catalog"
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream rounded-xl font-medium hover:bg-lsc-cream dark:hover:bg-lsc-brown/90"
            >
              <Sparkles aria-hidden="true" className="w-5 h-5" />
              {t("learn.browseCourses", "Browse Courses")}
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
