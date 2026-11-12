/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Admin Sharing Analytics Page
 * Displays the social sharing analytics dashboard for staff+ users
 */

import React from 'react';
import { AdminShell } from '../components/shells/AdminShell';
import SharingAnalyticsDashboard from '../components/admin/SharingAnalyticsDashboard';
import PageContainer from '@/components/layout/PageContainer'

const AdminSharingAnalyticsPage: React.FC = () => {
  return (
    <AdminShell title="Sharing Analytics">
      <PageContainer width="wide" className="py-8">
        <SharingAnalyticsDashboard />
      </PageContainer>
    </AdminShell>
  );
};

export default AdminSharingAnalyticsPage;
