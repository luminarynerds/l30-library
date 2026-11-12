/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Button Components - Storybook Stories
 *
 * Interactive documentation for Button components.
 */

import type { Meta, StoryObj } from '@storybook/react';
import { Button } from './Button';
import { Heart, Download } from 'lucide-react';

/* ===============================================
   BUTTON STORIES
   =============================================== */

const buttonMeta: Meta<typeof Button> = {
  title: 'Components/Button',
  component: Button,
  tags: ['autodocs'],
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: `
Button component with clear visual hierarchy and accessibility.

**Variants:**
- primary: Main call-to-action (orange)
- secondary: Secondary actions (cream/brown)
- \tertiary: Subtle actions (transparent)
- danger: Destructive actions (red)

**Features:**
- Touch target compliant (minimum 44px height)
- Loading states with contextual messages
- Brand-friendly loading text
- Left/right icon support
- Full width option
- Accessible focus states
- Dark mode support

**Loading Actions:**
- save, submit, register, login, checkout, delete, upload, download, send, reserve
        `,
      },
    },
  },
  argTypes: {
    variant: {
      control: 'select',
      options: ['primary', 'secondary', 'tertiary', 'danger'],
    },
    size: {
      control: 'select',
      options: ['sm', 'md', 'lg'],
    },
    isLoading: {
      control: 'boolean',
    },
    disabled: {
      control: 'boolean',
    },
    fullWidth: {
      control: 'boolean',
    },
  },
};

export default buttonMeta;

type ButtonStory = StoryObj<typeof Button>;

export const Primary: ButtonStory = {
  args: {
    children: 'Primary Button',
    variant: 'primary',
    size: 'md',
  },
};

export const Secondary: ButtonStory = {
  args: {
    children: 'Secondary Button',
    variant: 'secondary',
    size: 'md',
  },
};

export const Tertiary: ButtonStory = {
  args: {
    children: 'Tertiary Button',
    variant: 'tertiary',
    size: 'md',
  },
};

export const Danger: ButtonStory = {
  args: {
    children: 'Delete Item',
    variant: 'danger',
    size: 'md',
  },
};

export const Small: ButtonStory = {
  args: {
    children: 'Small Button',
    variant: 'primary',
    size: 'sm',
  },
};

export const Large: ButtonStory = {
  args: {
    children: 'Large Button',
    variant: 'primary',
    size: 'lg',
  },
};

export const WithLeftIcon: ButtonStory = {
  args: {
    children: 'Add to Favorites',
    variant: 'primary',
    leftIcon: <Heart className="w-5 h-5" />,
  },
};

export const WithRightIcon: ButtonStory = {
  args: {
    children: 'Download PDF',
    variant: 'secondary',
    rightIcon: <Download className="w-5 h-5" />,
  },
};

export const Loading: ButtonStory = {
  args: {
    children: 'Save Changes',
    variant: 'primary',
    isLoading: true,
    loadingAction: 'save',
  },
  parameters: {
    docs: {
      description: {
        story: 'Loading state with contextual message "Saving your changes..."',
      },
    },
  },
};

export const LoadingSubmit: ButtonStory = {
  args: {
    children: 'Submit Form',
    variant: 'primary',
    isLoading: true,
    loadingAction: 'submit',
  },
  parameters: {
    docs: {
      description: {
        story: 'Loading state with contextual message "Submitting..."',
      },
    },
  },
};

export const LoadingCustomText: ButtonStory = {
  args: {
    children: 'Process Payment',
    variant: 'primary',
    isLoading: true,
    loadingText: 'Processing payment...',
  },
  parameters: {
    docs: {
      description: {
        story: 'Loading state with custom loading text',
      },
    },
  },
};

export const Disabled: ButtonStory = {
  args: {
    children: 'Disabled Button',
    variant: 'primary',
    disabled: true,
  },
};

export const FullWidth: ButtonStory = {
  args: {
    children: 'Full Width Button',
    variant: 'primary',
    fullWidth: true,
  },
  parameters: {
    layout: 'padded',
  },
};

export const AllVariants: ButtonStory = {
  render: () => (
    <div className="space-y-4 p-4">
      <div className="space-y-2">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Variants</h3>
        <div className="flex flex-wrap gap-3">
          <Button variant="primary">Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="tertiary">Tertiary</Button>
          <Button variant="danger">Danger</Button>
        </div>
      </div>

      <div className="space-y-2">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Sizes</h3>
        <div className="flex flex-wrap items-center gap-3">
          <Button size="sm">Small</Button>
          <Button size="md">Medium</Button>
          <Button size="lg">Large</Button>
        </div>
      </div>

      <div className="space-y-2">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">With Icons</h3>
        <div className="flex flex-wrap gap-3">
          <Button leftIcon={<Heart className="w-5 h-5" />}>Favorite</Button>
          <Button rightIcon={<Download className="w-5 h-5" />} variant="secondary">Download</Button>
        </div>
      </div>

      <div className="space-y-2">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">States</h3>
        <div className="flex flex-wrap gap-3">
          <Button isLoading loadingAction="save">Loading</Button>
          <Button disabled>Disabled</Button>
        </div>
      </div>
    </div>
  ),
  parameters: {
    layout: 'padded',
    docs: {
      description: {
        story: 'Overview of all button variants, sizes, and states',
      },
    },
  },
};
