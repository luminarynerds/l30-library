/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable no-useless-escape */
/**
 * Skeleton Loading Components - Storybook Stories
 *
 * Interactive documentation for all skeleton loading components.
 * Skeletons provide visual feedback while content loads.
 */

import type { Meta, StoryObj } from '@storybook/react';

// Skeleton Components
import { SkeletonTable, SkeletonTableCompact } from './SkeletonTable';
import {
  StaffStatsCardsSkeleton,
  StaffListItemSkeleton,
  StaffListSkeleton,
  StaffPageWithTabsSkeleton,
  StaffDashboardPanelSkeleton,
} from './StaffPageSkeleton';

/* ===============================================
   SKELETON TABLE STORIES
   =============================================== */

const skeletonTableMeta: Meta<typeof SkeletonTable> = {
  title: 'Loading/Skeleton Table',
  component: SkeletonTable,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
    docs: {
      description: {
        component: `
Skeleton loading component for tables. Provides visual feedback while table data loads.

**Features:**
- Configurable rows and columns
- Shimmer animation (respects reduced motion)
- Accessible with aria-label
- Matches table layout patterns
- Optional header and action column

**Accessibility:**
// eslint-disable-next-line no-useless-escape
- Uses \role="status"\ for loading state
- Includes screen reader text "Loading..."
- Respects prefers-reduced-motion\
        `,
      },
    },
  },
};

export default skeletonTableMeta;

type SkeletonTableStory = StoryObj<typeof SkeletonTable>;

export const Default: SkeletonTableStory = {
  args: {
    rows: 5,
    columns: 4,
    showHeader: true,
    showActions: false,
  },
};

export const WithActions: SkeletonTableStory = {
  args: {
    rows: 5,
    columns: 4,
    showHeader: true,
    showActions: true,
  },
  parameters: {
    docs: {
      description: {
        story: 'Table skeleton with an actions column (narrower, for buttons)',
      },
    },
  },
};

export const NoHeader: SkeletonTableStory = {
  args: {
    rows: 5,
    columns: 4,
    showHeader: false,
    showActions: false,
  },
  parameters: {
    docs: {
      description: {
        story: 'Table skeleton without header row',
      },
    },
  },
};

export const FewRows: SkeletonTableStory = {
  args: {
    rows: 3,
    columns: 3,
    showHeader: true,
    showActions: false,
  },
  parameters: {
    docs: {
      description: {
        story: 'Smaller table skeleton with fewer rows and columns',
      },
    },
  },
};

export const ManyColumns: SkeletonTableStory = {
  args: {
    rows: 5,
    columns: 8,
    showHeader: true,
    showActions: true,
  },
  parameters: {
    docs: {
      description: {
        story: 'Wide table skeleton with many columns',
      },
    },
  },
};

/* ===============================================
   COMPACT TABLE SKELETON
   =============================================== */

export const CompactDefault: StoryObj<typeof SkeletonTableCompact> = {
  args: {
    rows: 3,
    columns: 3,
  },
};

export const CompactFewItems: StoryObj<typeof SkeletonTableCompact> = {
  args: {
    rows: 2,
    columns: 2,
  },
};

/* ===============================================
   STAFF STATS CARDS SKELETON
   =============================================== */

export const StatsCards: StoryObj<typeof StaffStatsCardsSkeleton> = {
  args: {
    count: 4,
  },
};

export const StatsCardsFew: StoryObj<typeof StaffStatsCardsSkeleton> = {
  args: {
    count: 2,
  },
  parameters: {
    docs: {
      description: {
        story: 'Fewer stat cards for smaller dashboards',
      },
    },
  },
};

export const StatsCardsMany: StoryObj<typeof StaffStatsCardsSkeleton> = {
  args: {
    count: 6,
  },
  parameters: {
    docs: {
      description: {
        story: 'More stat cards for comprehensive dashboards',
      },
    },
  },
};

/* ===============================================
   STAFF LIST SKELETON
   =============================================== */

export const List: StoryObj<typeof StaffListSkeleton> = {
  args: {
    count: 5,
  },
};

export const ListShort: StoryObj<typeof StaffListSkeleton> = {
  args: {
    count: 3,
  },
  parameters: {
    docs: {
      description: {
        story: 'Shorter list for compact displays',
      },
    },
  },
};

export const ListLong: StoryObj<typeof StaffListSkeleton> = {
  args: {
    count: 10,
  },
  parameters: {
    docs: {
      description: {
        story: 'Longer list for full page displays',
      },
    },
  },
};

export const ListItem: StoryObj<typeof StaffListItemSkeleton> = {
  render: () => <StaffListItemSkeleton />,
  parameters: {
    docs: {
      description: {
        story: 'Single list item skeleton',
      },
    },
  },
};

/* ===============================================
   STAFF PAGE SKELETONS
   =============================================== */

export const PageWithTabs: StoryObj<typeof StaffPageWithTabsSkeleton> = {
  render: () => <StaffPageWithTabsSkeleton />,
};

/* ===============================================
   STAFF DASHBOARD PANEL
   =============================================== */

export const DashboardPanel: StoryObj<typeof StaffDashboardPanelSkeleton> = {
  render: () => <StaffDashboardPanelSkeleton />,
};
