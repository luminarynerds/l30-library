/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-hooks/rules-of-hooks */
/**
 * Modal and Card Components - Storybook Stories
 *
 * Interactive documentation for Modal, Card, and StatCard components.
 */

import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import { Modal } from './Modal';
import { StatCard } from './StatCard';
import { Button } from './Button';
import { BookOpen, Users, Calendar, TrendingUp, Heart, Download } from 'lucide-react';
import { t } from '@/i18n'

/* ===============================================
   MODAL STORIES
   =============================================== */

const modalMeta: Meta<typeof Modal> = {
  title: 'Components/Modal',
  component: Modal,
  tags: ['autodocs'],
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: `
Accessible modal dialog component with focus management.

**Features:**
- Focus trap (keyboard navigation contained)
- Escape key to close (if dismissible)
- Click backdrop to close (if dismissible)
- Automatic body scroll lock
- Focus restoration on close
- Multiple size variants
- Optional header and footer
- Accessible with ARIA attributes

**Accessibility:**
- role="dialog" and aria-modal="true"
- Focus trap using focus-trap-react
- Returns focus to trigger element on close
- Supports screen readers
- Keyboard navigation (Escape, Tab)

**Sizes:**
- sm: 384px (24rem)
- md: 448px (28rem)
- lg: 512px (32rem)
- xl: 576px (36rem)
- 2xl: 672px (42rem)
        `,
      },
    },
  },
  argTypes: {
    size: {
      control: 'select',
      options: ['sm', 'md', 'lg', 'xl', '2xl'],
    },
    dismissible: {
      control: 'boolean',
    },
  },
};

export default modalMeta;

export const Default: StoryObj<typeof Modal> = {
  render: () => {
    const [isOpen, setIsOpen] = useState(false);

    return (
      <>
        <Button onClick={() => setIsOpen(true)}>Open Modal</Button>
        <Modal
          isOpen={isOpen}
          onClose={() => setIsOpen(false)}
          title="Example Modal"
        >
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            This is a basic modal dialog. Click outside or press Escape to close.
          </p>
        </Modal>
      </>
    );
  },
};

export const WithFooter: StoryObj<typeof Modal> = {
  render: () => {
    const [isOpen, setIsOpen] = useState(false);

    return (
      <>
        <Button onClick={() => setIsOpen(true)}>Open Modal with Footer</Button>
        <Modal
          isOpen={isOpen}
          onClose={() => setIsOpen(false)}
          title="Confirm Action"
          footer={
            <>
              <Button variant="secondary" onClick={() => setIsOpen(false)} fullWidth>
                Cancel
              </Button>
              <Button variant="primary" onClick={() => setIsOpen(false)} fullWidth>
                Confirm
              </Button>
            </>
          }
        >
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Are you sure you want to proceed with this action?
          </p>
        </Modal>
      </>
    );
  },
};

export const SmallSize: StoryObj<typeof Modal> = {
  render: () => {
    const [isOpen, setIsOpen] = useState(false);

    return (
      <>
        <Button onClick={() => setIsOpen(true)}>Open Small Modal</Button>
        <Modal
          isOpen={isOpen}
          onClose={() => setIsOpen(false)}
          title="Small Modal"
          size="sm"
        >
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            This is a small modal perfect for confirmations.
          </p>
        </Modal>
      </>
    );
  },
};

export const LargeSize: StoryObj<typeof Modal> = {
  render: () => {
    const [isOpen, setIsOpen] = useState(false);

    return (
      <>
        <Button onClick={() => setIsOpen(true)}>Open Large Modal</Button>
        <Modal
          isOpen={isOpen}
          onClose={() => setIsOpen(false)}
          title="Large Modal"
          size="lg"
        >
          <div className="space-y-4 text-lsc-dark/70 dark:text-lsc-cream/70">
            <p>This is a larger modal with more content space.</p>
            <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
            <p>Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.</p>
          </div>
        </Modal>
      </>
    );
  },
};

export const ExtraLargeSize: StoryObj<typeof Modal> = {
  render: () => {
    const [isOpen, setIsOpen] = useState(false);

    return (
      <>
        <Button onClick={() => setIsOpen(true)}>Open 2XL Modal</Button>
        <Modal
          isOpen={isOpen}
          onClose={() => setIsOpen(false)}
          title="Extra Large Modal"
          size="2xl"
        >
          <div className="space-y-4 text-lsc-dark/70 dark:text-lsc-cream/70">
            <p>This is an extra large modal for complex content or forms.</p>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-lsc-cream dark:bg-earth-700 rounded-lg">
                <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">Section 1</h4>
                <p>Content here...</p>
              </div>
              <div className="p-4 bg-lsc-cream dark:bg-earth-700 rounded-lg">
                <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">Section 2</h4>
                <p>Content here...</p>
              </div>
            </div>
          </div>
        </Modal>
      </>
    );
  },
};

export const NotDismissible: StoryObj<typeof Modal> = {
  render: () => {
    const [isOpen, setIsOpen] = useState(false);

    return (
      <>
        <Button onClick={() => setIsOpen(true)}>Open Non-Dismissible Modal</Button>
        <Modal
          isOpen={isOpen}
          onClose={() => setIsOpen(false)}
          title="Important Notice"
          dismissible={false}
          footer={
            <Button variant="primary" onClick={() => setIsOpen(false)} fullWidth>
              I Understand
            </Button>
          }
        >
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            This modal requires explicit confirmation. You cannot close it by clicking outside or pressing Escape.
          </p>
        </Modal>
      </>
    );
  },
  parameters: {
    docs: {
      description: {
        story: 'Modal that cannot be dismissed by clicking backdrop or pressing Escape',
      },
    },
  },
};

export const LongContent: StoryObj<typeof Modal> = {
  render: () => {
    const [isOpen, setIsOpen] = useState(false);

    return (
      <>
        <Button onClick={() => setIsOpen(true)}>Open Modal with Long Content</Button>
        <Modal
          isOpen={isOpen}
          onClose={() => setIsOpen(false)}
          title="Terms and Conditions"
          size="lg"
          footer={
            <Button variant="primary" onClick={() => setIsOpen(false)} fullWidth>
              Accept
            </Button>
          }
        >
          <div className="space-y-4 text-lsc-dark/70 dark:text-lsc-cream/70">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Introduction</h3>
            <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>

            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Terms</h3>
            <p>Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.</p>
            <p>Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.</p>

            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Privacy</h3>
            <p>Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
            <p>Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium.</p>

            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Additional Information</h3>
            <p>Totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo.</p>
            <p>Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt.</p>
          </div>
        </Modal>
      </>
    );
  },
  parameters: {
    docs: {
      description: {
        story: 'Modal with scrollable content (max-height: 90vh)',
      },
    },
  },
};

export const FormExample: StoryObj<typeof Modal> = {
  render: () => {
    const [isOpen, setIsOpen] = useState(false);

    return (
      <>
        <Button onClick={() => setIsOpen(true)}>Open Form Modal</Button>
        <Modal
          isOpen={isOpen}
          onClose={() => setIsOpen(false)}
          title="Add New Book"
          size="md"
          footer={
            <>
              <Button variant="secondary" onClick={() => setIsOpen(false)} fullWidth>
                Cancel
              </Button>
              <Button variant="primary" onClick={() => setIsOpen(false)} fullWidth>
                Add Book
              </Button>
            </>
          }
        >
          <form className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                Title
              </label>
              <input
                type="text"
                className="w-full px-4 py-3 border-2 border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                placeholder={t('placeholder.ui.enterBookTitle')}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                Author
              </label>
              <input
                type="text"
                className="w-full px-4 py-3 border-2 border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                placeholder={t('placeholder.ui.enterAuthorName')}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                ISBN
              </label>
              <input
                type="text"
                className="w-full px-4 py-3 border-2 border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                placeholder={t('placeholder.ui.enterIsbn')}
              />
            </div>
          </form>
        </Modal>
      </>
    );
  },
  parameters: {
    docs: {
      description: {
        story: 'Modal containing a form with footer actions',
      },
    },
  },
};

/* ===============================================
   STAT CARD STORIES
   =============================================== */

export const StatCardBasic: StoryObj<typeof StatCard> = {
  args: {
    title: 'Total Checkouts',
    value: '1,234',
    icon: BookOpen,
    color: 'blue',
  },
};

export const StatCardWithPositiveTrend: StoryObj<typeof StatCard> = {
  args: {
    title: 'Active Members',
    value: '856',
    icon: Users,
    color: 'green',
    trend: { value: 12, label: 'from last month' },
  },
  parameters: {
    docs: {
      description: {
        story: 'Stat card with positive trend indicator',
      },
    },
  },
};

export const StatCardWithNegativeTrend: StoryObj<typeof StatCard> = {
  args: {
    title: 'Overdue Items',
    value: '23',
    icon: Calendar,
    color: 'red',
    trend: { value: -8, label: 'from last week' },
  },
  parameters: {
    docs: {
      description: {
        story: 'Stat card with negative trend indicator (shows improvement)',
      },
    },
  },
};

export const StatCardClickable: StoryObj<typeof StatCard> = {
  args: {
    title: 'Favorites',
    value: '42',
    icon: Heart,
    color: 'purple',
    onClick: () => alert('Navigate to favorites'),
  },
  parameters: {
    docs: {
      description: {
        story: 'Clickable stat card (becomes button with hover effect)',
      },
    },
  },
};

export const StatCardAllColors: StoryObj<typeof StatCard> = {
  render: () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <StatCard title="Blue" value="100" icon={BookOpen} color="accent" />
      <StatCard title="Green" value="200" icon={Users} color="success" trend={{ value: 10 }} />
      <StatCard title="Orange" value="300" icon={Calendar} color="warning" trend={{ value: -5 }} />
      <StatCard title="Red" value="400" icon={TrendingUp} color="danger" />
      <StatCard title="Purple" value="500" icon={Heart} color="category" />
      <StatCard title="Clickable" value="600" icon={Download} color="accent" onClick={() => alert('Clicked!')} />
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: 'Overview of all stat card colors and variants',
      },
    },
  },
};
