/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react';
import { EndOfShiftChecklist } from '@/components/staff/EndOfShiftChecklist';
import { AdminShell } from '../../components/shells/AdminShell'

/**
 * End-of-Shift Wrap-Up Page
 * Guides staff through completing their shift checklist and transition
 */
const EndOfShiftPage: React.FC = () => {
  return (

    <AdminShell title="End Of Shift">    <div className="min-h-screen bg-gradient-to-br from-earth-50 to-earth-100 dark:from-earth-900 dark:to-earth-800 p-8">
      <div className="max-w-2xl mx-auto">
        <EndOfShiftChecklist />
      </div>
    </div>
  </AdminShell>
  );
};

export default EndOfShiftPage;
