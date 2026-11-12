/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Empty States and Error Components - Storybook Stories
 *
 * Interactive documentation for EmptyState and ErrorAlert components.
 * These components handle feedback for empty/error states with brand-aligned messaging.
 */

import type { Meta, StoryObj } from '@storybook/react';
import { EmptyState, EmptyStateCard, EmptyStateInline } from './EmptyState';
import { ErrorAlert, ErrorAlertCompact } from './ErrorAlert';
import { BookOpen, Heart, Search, Users, Calendar, Database } from 'lucide-react'

/* ===============================================
   EMPTY STATE STORIES
   =============================================== */

const emptyStateMeta: Meta<typeof EmptyState> = {
  title: 'Feedback/Empty State',
  component: EmptyState,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
    docs: {
      description: {
        component: `
A reusable component for displaying empty states with the L30 brand voice.

**Brand Voice Principles:**
- Warm & welcoming (not negative or failure-focused)
- Helpful & actionable (always suggest next steps)
- Encouraging (make empty feel like opportunity, not failure)
- Clear & specific (no vague messaging)

**Features:**
- Multiple size variants (sm, md, lg)
- Visual style variants (default, subtle)
- Primary and secondary actions
- Optional help text
- Custom illustrations support
- Fully accessible with ARIA attributes

**Use Cases:**
- No search results
- Empty favorites/checkout lists
- No upcoming events
- First-time user states
        `,
      },
    },
  },
};

export default emptyStateMeta;

type EmptyStateStory = StoryObj<typeof EmptyState>;

export const NoCheckouts: EmptyStateStory = {
  args: {
    icon: BookOpen,
    title: 'No checkouts right now',
    description: "Ready for your next read? We've got plenty to choose from.",
    primaryAction: {
      label: 'Browse catalog',
      onClick: () => alert('Navigate to catalog'),
    },
    size: 'md',
    variant: 'default',
  },
  parameters: {
    docs: {
      description: {
        story: 'Empty state for user with no current checkouts - encouraging and action-oriented',
      },
    },
  },
};

export const NoFavorites: EmptyStateStory = {
  args: {
    icon: Heart,
    title: 'No favorites saved yet',
    description: 'Heart items you love to find them easily later.',
    primaryAction: {
      label: 'Explore catalog',
      onClick: () => alert('Navigate to catalog'),
    },
    helpText: 'Tip: Click the heart icon on any item to save it here',
    size: 'md',
  },
};

export const NoSearchResults: EmptyStateStory = {
  args: {
    icon: Search,
    title: 'No results found',
    description: 'Try different keywords or browse our catalog.',
    primaryAction: {
      label: 'Clear filters',
      onClick: () => alert('Clear filters'),
    },
    secondaryAction: {
      label: 'Browse all items',
      onClick: () => alert('Browse catalog'),
    },
    size: 'md',
  },
  parameters: {
    docs: {
      description: {
        story: 'Empty search results with both primary and secondary actions',
      },
    },
  },
};

export const SmallSize: EmptyStateStory = {
  args: {
    icon: Database,
    title: 'No records found',
    description: 'There are no records matching your criteria.',
    size: 'sm',
  },
  parameters: {
    docs: {
      description: {
        story: 'Smaller empty state for compact UI sections',
      },
    },
  },
};

export const LargeSize: EmptyStateStory = {
  args: {
    icon: Calendar,
    title: 'No upcoming events',
    description: "We're planning some great programs! Check back soon or join our mailing list to hear about new events first.",
    primaryAction: {
      label: 'Subscribe to updates',
      onClick: () => alert('Subscribe'),
    },
    secondaryAction: {
      label: 'View past events',
      onClick: () => alert('View past events'),
    },
    size: 'lg',
  },
  parameters: {
    docs: {
      description: {
        story: 'Larger empty state for full page displays',
      },
    },
  },
};

export const SubtleVariant: EmptyStateStory = {
  args: {
    icon: Users,
    title: 'No members in this group',
    description: 'Invite people to join your book club.',
    variant: 'subtle',
    size: 'md',
  },
  parameters: {
    docs: {
      description: {
        story: 'Subtle variant with muted icon color',
      },
    },
  },
};

/* ===============================================
   EMPTY STATE CARD
   =============================================== */

export const CardVariant: StoryObj<typeof EmptyStateCard> = {
  args: {
    icon: BookOpen,
    title: 'Reading list is empty',
    description: 'Add books to your reading list to track what you want to read next.',
    primaryAction: {
      label: 'Find books',
      onClick: () => alert('Find books'),
    },
  },
};

/* ===============================================
   EMPTY STATE INLINE
   =============================================== */

export const Inline: StoryObj<typeof EmptyStateInline> = {
  args: {
    icon: Heart,
    title: 'No favorites',
    description: 'Save items here for quick access',
    primaryAction: {
      label: 'Browse',
      onClick: () => alert('Browse'),
    },
  },
};

/* ===============================================
   ERROR ALERT STORIES
   =============================================== */

export const ErrorSeverity: StoryObj<typeof ErrorAlert> = {
  args: {
    title: "Couldn't save your changes",
    message: "We're having a temporary issue. Your work is safe and we'll keep trying.",
    variant: 'error',
    onRetry: () => alert('Retrying...'),
    errorCode: 'ERR_500',
  },
  parameters: {
    docs: {
      description: {
        story: 'Error severity with retry button and error code',
      },
    },
  },
};

export const WarningSeverity: StoryObj<typeof ErrorAlert> = {
  args: {
    title: 'Low storage space',
    message: 'You have less than 10% of your storage remaining. Consider removing some saved items.',
    variant: 'warning',
    onAction: () => alert('Manage storage'),
    actionText: 'Manage storage',
  },
  parameters: {
    docs: {
      description: {
        story: 'Warning severity with custom action button',
      },
    },
  },
};

export const InfoSeverity: StoryObj<typeof ErrorAlert> = {
  args: {
    title: 'Maintenance scheduled',
    message: 'The library catalog will be offline tomorrow from 2-4 AM for maintenance.',
    variant: 'info',
  },
  parameters: {
    docs: {
      description: {
        story: 'Info severity for informational messages',
      },
    },
  },
};

export const WithSupport: StoryObj<typeof ErrorAlert> = {
  args: {
    title: 'Payment processing failed',
    message: "We couldn't process your payment. Please check your payment method or try a different card.",
    variant: 'error',
    onRetry: () => alert('Retry'),
    showSupport: true,
    errorCode: 'PAY_001',
  },
  parameters: {
    docs: {
      description: {
        story: 'Error with support contact link',
      },
    },
  },
};

export const Dismissible: StoryObj<typeof ErrorAlert> = {
  args: {
    title: 'Update available',
    message: 'A new version of the library app is available. Refresh to get the latest features.',
    variant: 'info',
    dismissible: true,
    onAction: () => alert('Refresh'),
    actionText: 'Refresh now',
  },
  parameters: {
    docs: {
      description: {
        story: 'Dismissible alert with close button',
      },
    },
  },
};

export const LongMessage: StoryObj<typeof ErrorAlert> = {
  args: {
    title: 'Form validation errors',
    message: (
      <ul className="list-disc list-inside space-y-1">
        <li>Email address is required</li>
        <li>Password must be at least 8 characters</li>
        <li>Phone number format is invalid</li>
      </ul>
    ),
    variant: 'error',
  },
  parameters: {
    docs: {
      description: {
        story: 'Error alert with custom React element as message',
      },
    },
  },
};

/* ===============================================
   ERROR ALERT COMPACT
   =============================================== */

export const CompactError: StoryObj<typeof ErrorAlertCompact> = {
  args: {
    message: 'Please check your internet connection',
    variant: 'error',
  },
};

export const CompactWarning: StoryObj<typeof ErrorAlertCompact> = {
  args: {
    message: 'This action cannot be undone',
    variant: 'warning',
    dismissible: true,
  },
};

export const CompactInfo: StoryObj<typeof ErrorAlertCompact> = {
  args: {
    message: 'Your session will expire in 5 minutes',
    variant: 'info',
    dismissible: true,
  },
};
