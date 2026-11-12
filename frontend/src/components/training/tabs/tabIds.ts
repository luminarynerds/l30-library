/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Stable id helpers for tying tabs to their panels.
 *
 * Lives in its own module so the tab component file can stay
 * components-only (react-refresh/only-export-components).
 */
import type { TrainingTab } from '../utils/dueDate';

export function tabIdFor(tab: TrainingTab): string {
  return `training-tab-${tab}`;
}

export function panelIdFor(tab: TrainingTab): string {
  return `training-panel-${tab}`;
}
