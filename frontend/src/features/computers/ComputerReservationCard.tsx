/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/** React component for displaying and booking a computer. */

import { useState } from "react";
import { Computer, ComputerType } from "@/types/computer";
import {
  Accessibility,
  Wifi,
  Printer,
  MapPin,
  Clock,
} from "lucide-react";
import { t } from "@/i18n";

interface ComputerReservationCardProps {
  computer: Computer;
  onReserve: (computerId: number, startTime: Date, duration: number) => void;
  onStartSession: (computerId: number, duration: number) => void;
  isAvailable: boolean;
}

export function ComputerReservationCard({
  computer,
  onReserve,
  onStartSession,
  isAvailable,
}: ComputerReservationCardProps) {
  const [selectedDuration, setSelectedDuration] = useState(60);
  const [selectedTime, setSelectedTime] = useState<Date>(() => new Date());

  const getComputerTypeLabel = (type: ComputerType): string => {
    const labels: Record<ComputerType, string> = {
      kids: t("computers.card.typeKids"),
      teen: t("computers.card.typeTeen"),
      adult: t("computers.card.typeAdult"),
      accessible: t("computers.card.typeAccessible"),
    };
    return labels[type];
  };

  const getTypeColor = (type: ComputerType): string => {
    const colors: Record<ComputerType, string> = {
      kids: "bg-category-100 dark:bg-category-900/30 text-category-800 dark:text-category-300",
      teen: "bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light",
      adult: "bg-earth-100 dark:bg-earth-700 text-earth-800 dark:text-earth-100",
      accessible: "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300",
    };
    return colors[type];
  };

  const handleReserve = () => {
    onReserve(computer.id, selectedTime, selectedDuration);
  };

  const handleStart = () => {
    onStartSession(computer.id, selectedDuration);
  };

  // Format for datetime-local min attribute: "YYYY-MM-DDTHH:mm"
  const nowIsoLocal = (() => {
    const d = new Date();
    const pad = (n: number) => n.toString().padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  })();

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {computer.name}
          </h3>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{computer.computer_number}</p>
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getTypeColor(computer.computer_type)}`}>
          {getComputerTypeLabel(computer.computer_type)}
        </span>
      </div>

      {/* Location */}
      {computer.location && (
        <div className="flex items-center gap-2 mb-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <MapPin aria-hidden="true" className="w-4 h-4" />
          {computer.location}
        </div>
      )}

      {/* Features */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        {computer.has_internet && (
          <div className="flex items-center gap-2 text-sm text-status-success-700 dark:text-status-success-300 bg-status-success-50 dark:bg-status-success-900/20 px-2 py-1 rounded">
            <Wifi aria-hidden="true" className="w-4 h-4" />
            {t("computers.card.internet")}
          </div>
        )}
        {computer.has_print_release && (
          <div className="flex items-center gap-2 text-sm text-lsc-rose dark:text-lsc-rose-light bg-earth-50 dark:bg-earth-800/20 px-2 py-1 rounded">
            <Printer aria-hidden="true" className="w-4 h-4" />
            {t("computers.card.printing")}
          </div>
        )}
        {(computer.has_screen_reader ||
          computer.has_magnifier ||
          computer.has_keyboard_options) && (
          <div className="flex items-center gap-2 text-sm text-category-700 dark:text-category-300 bg-category-50 dark:bg-category-900/20 px-2 py-1 rounded">
            <Accessibility aria-hidden="true" className="w-4 h-4" />
            {t("computers.card.accessible")}
          </div>
        )}
        <div className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 bg-earth-50 dark:bg-earth-900 px-2 py-1 rounded">
          <Clock aria-hidden="true" className="w-4 h-4" />
          {t("computers.card.maxMinutes", { minutes: computer.max_session_minutes })}
        </div>
      </div>

      {/* Software */}
      {computer.installed_software && computer.installed_software.length > 0 && (
        <div className="mb-4">
          <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">{t("computers.card.softwareLabel")}</p>
          <div className="flex flex-wrap gap-1">
            {computer.installed_software.slice(0, 4).map((software) => (
              <span
                key={software}
                className="bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 text-xs px-2 py-1 rounded"
              >
                {software}
              </span>
            ))}
            {computer.installed_software.length > 4 && (
              <span className="bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 text-xs px-2 py-1 rounded">
                {t("computers.card.softwareMore", { count: computer.installed_software.length - 4 })}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Status */}
      <div className="mb-4 p-3 rounded-lg bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700">
        {(() => {
          const status = computer.status
          if (status === 'available') {
            return <p className="text-sm text-status-success-700 dark:text-status-success-300 font-medium">{t("computers.card.availableNow")}</p>
          }
          const labelKey = status === 'maintenance' ? 'computers.card.maintenance'
            : status === 'offline' ? 'computers.card.offline'
            : status === 'reserved' ? 'computers.card.reserved'
            : 'computers.card.inUse'
          return <p className="text-sm text-status-warning-700 dark:text-status-warning-300 font-medium">{t(labelKey)}</p>
        })()}
      </div>

      {/* Reservation Controls */}
      {isAvailable && (
        <div className="space-y-3 border-t pt-4">
          <div>
            <label htmlFor={`session-duration-${computer.id}`} className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              {t("computers.card.sessionDuration")}
            </label>
            <select
              id={`session-duration-${computer.id}`}
              value={selectedDuration}
              onChange={(e) => setSelectedDuration(Number(e.target.value))}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-lsc-rose-light dark:bg-earth-800 dark:text-earth-50"
            >
              <option value={30}>{t("computers.card.duration30")}</option>
              <option value={60}>{t("computers.card.duration60")}</option>
              {computer.is_extendable && <option value={120}>{t("computers.card.duration120")}</option>}
            </select>
          </div>

          <button
            onClick={handleStart}
            disabled={!isAvailable}
            className="w-full bg-status-success-600 hover:bg-status-success-700 disabled:bg-earth-400 text-white font-medium py-2 rounded-lg transition-colors"
          >
            {t("computers.card.startSessionButton")}
          </button>

          <div>
            <label htmlFor={`start-time-${computer.id}`} className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              {t("computers.card.startTime")}
            </label>
            <input
              id={`start-time-${computer.id}`}
              type="datetime-local"
              min={nowIsoLocal}
              onChange={(e) => setSelectedTime(new Date(e.target.value))}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-lsc-rose-light dark:bg-earth-800 dark:text-earth-50"
            />
          </div>

          <button
            onClick={handleReserve}
            disabled={!isAvailable}
            className="w-full bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-earth-400 text-white font-medium py-2 rounded-lg transition-colors"
          >
            {t("computers.card.reserveButton")}
          </button>
        </div>
      )}
    </div>
  );
}
