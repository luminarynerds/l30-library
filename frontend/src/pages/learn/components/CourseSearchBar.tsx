/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Search } from "lucide-react";
import { useTranslation } from "@/i18n";

interface CourseSearchBarProps {
  searchTerm: string;
  onSearchChange: (value: string) => void;
}

export function CourseSearchBar({ searchTerm, onSearchChange }: CourseSearchBarProps) {
  const { t } = useTranslation();

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-4 mb-6">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
        <input
          type="text"
          placeholder={t("placeholder.learn.searchYourCourses")}
          aria-label={t("learn.searchYourEnrolledCourses")}
          value={searchTerm}
          onChange={e => onSearchChange(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder:text-lsc-dark/70 dark:placeholder:text-lsc-cream/60"
        />
      </div>
    </div>
  );
}
