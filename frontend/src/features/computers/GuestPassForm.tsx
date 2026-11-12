/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/** React component for guest pass creation and usage. */

import React, { useState } from "react";
import { Users, Mail, Phone, Ticket } from "lucide-react";
import { clean } from '@/lib/utils';
import { t } from '@/i18n'

interface GuestPassFormProps {
  onSubmit: (data: GuestPassFormData) => void;
  isLoading?: boolean;
}

export interface GuestPassFormData {
  guest_name: string;
  guest_email?: string;
  guest_phone?: string;
  max_sessions: number;
  max_duration_minutes_per_session: number;
  allowed_computer_types?: string[];
}

export function GuestPassForm({ onSubmit, isLoading = false }: GuestPassFormProps) {
  const [formData, setFormData] = useState<GuestPassFormData>({
    guest_name: "",
    guest_email: "",
    guest_phone: "",
    max_sessions: 1,
    max_duration_minutes_per_session: 60,
    allowed_computer_types: [],
  });

  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [nameError, setNameError] = useState<string | null>(null);

  const computerTypes = [
    { value: "kids", label: t("computers.guestPass.typeKids") },
    { value: "teen", label: t("computers.guestPass.typeTeen") },
    { value: "adult", label: t("computers.guestPass.typeAdult") },
    { value: "accessible", label: t("computers.guestPass.typeAccessible") },
  ];

  const handleToggleComputerType = (type: string) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.guest_name.trim()) {
      setNameError(t("computers.guestPass.errorNameRequired"));
      return;
    }
    setNameError(null);

    onSubmit(clean({
      ...formData,
      allowed_computer_types: selectedTypes.length > 0 ? selectedTypes : undefined,
    }));
  };

  return (
    <form onSubmit={handleSubmit} className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-md p-6 max-w-md">
      <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-6 flex items-center gap-2">
        <Ticket aria-hidden="true" className="w-6 h-6" />
        {t("computers.guestPass.issuePass")}
      </h2>

      {/* Guest Name */}
      <div className="mb-4">
        <label htmlFor="guest-name" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
          {t("computers.guestPass.guestNameRequired")}
        </label>
        <div className="relative">
          <Users aria-hidden="true" className="absolute left-3 top-3 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <input
            id="guest-name"
            type="text"
            value={formData.guest_name}
            onChange={(e) => {
              setFormData({ ...formData, guest_name: e.target.value });
              if (nameError) setNameError(null);
            }}
            placeholder={t('placeholder.guestPassForm.fullName')}
            aria-invalid={nameError ? true : undefined}
            aria-describedby={nameError ? "guest-name-error" : undefined}
            className="w-full pl-10 pr-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-lsc-rose-light dark:bg-earth-700 dark:text-earth-100"
            required
          />
        </div>
        {nameError && (
          <p
            id="guest-name-error"
            role="alert"
            className="mt-1 text-sm text-status-danger-700 dark:text-status-danger-300"
          >
            {nameError}
          </p>
        )}
      </div>

      {/* Email */}
      <div className="mb-4">
        <label htmlFor="guest-email" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
          {t("computers.guestPass.emailOptional")}
        </label>
        <div className="relative">
          <Mail aria-hidden="true" className="absolute left-3 top-3 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <input
            id="guest-email"
            type="email"
            value={formData.guest_email || ""}
            onChange={(e) =>
              setFormData({ ...formData, guest_email: e.target.value })
            }
            placeholder={t('placeholder.guestPassForm.emailexamplecom')}
            className="w-full pl-10 pr-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-lsc-rose-light dark:bg-earth-700 dark:text-earth-100"
          />
        </div>
      </div>

      {/* Phone */}
      <div className="mb-4">
        <label htmlFor="guest-phone" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
          {t("computers.guestPass.phoneOptional")}
        </label>
        <div className="relative">
          <Phone aria-hidden="true" className="absolute left-3 top-3 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <input
            id="guest-phone"
            type="tel"
            value={formData.guest_phone || ""}
            onChange={(e) =>
              setFormData({ ...formData, guest_phone: e.target.value })
            }
            placeholder={t('placeholder.guestPassForm.5551234567')}
            className="w-full pl-10 pr-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-lsc-rose-light dark:bg-earth-700 dark:text-earth-100"
          />
        </div>
      </div>

      {/* Max Sessions */}
      <div className="mb-4">
        <label htmlFor="guest-max-sessions" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
          {t("computers.guestPass.maxSessions")}
        </label>
        <select
          id="guest-max-sessions"
          value={formData.max_sessions}
          onChange={(e) =>
            setFormData({
              ...formData,
              max_sessions: Number(e.target.value),
            })
          }
          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-lsc-rose-light dark:bg-earth-700 dark:text-earth-100"
        >
          <option value={1}>{t("computers.guestPass.sessionsCount", { count: 1 })}</option>
          <option value={3}>{t("computers.guestPass.sessionsCount", { count: 3 })}</option>
          <option value={5}>{t("computers.guestPass.sessionsCount", { count: 5 })}</option>
          <option value={10}>{t("computers.guestPass.sessionsCount", { count: 10 })}</option>
        </select>
      </div>

      {/* Session Duration */}
      <div className="mb-4">
        <label htmlFor="guest-max-duration" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
          {t("computers.guestPass.maxDurationPerSession")}
        </label>
        <select
          id="guest-max-duration"
          value={formData.max_duration_minutes_per_session}
          onChange={(e) =>
            setFormData({
              ...formData,
              max_duration_minutes_per_session: Number(e.target.value),
            })
          }
          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-lsc-rose-light dark:bg-earth-700 dark:text-earth-100"
        >
          <option value={30}>{t("computers.guestPass.duration30")}</option>
          <option value={60}>{t("computers.guestPass.duration60")}</option>
          <option value={120}>{t("computers.guestPass.duration120")}</option>
          <option value={180}>{t("computers.guestPass.duration180")}</option>
        </select>
      </div>

      {/* Computer Types */}
      <fieldset className="mb-6">
        <legend className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
          {t("computers.guestPass.allowedTypesLegend")}
        </legend>
        <div className="space-y-2">
          {computerTypes.map((type) => (
            <label key={type.value} className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={selectedTypes.includes(type.value)}
                onChange={() => handleToggleComputerType(type.value)}
                className="w-4 h-4 rounded border-lsc-border dark:border-earth-700 focus:ring-2 focus:ring-lsc-rose dark:focus:ring-lsc-rose-light"
              />
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{type.label}</span>
            </label>
          ))}
        </div>
      </fieldset>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isLoading}
        className="w-full bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-earth-400 dark:disabled:bg-earth-600 text-white font-medium py-2 rounded-lg transition-colors"
      >
        {isLoading ? t("computers.guestPass.creating") : t("computers.guestPass.submitButton")}
      </button>
    </form>
  );
}
