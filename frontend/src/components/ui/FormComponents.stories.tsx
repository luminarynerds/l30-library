/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable no-useless-escape */
/* eslint-disable react-hooks/rules-of-hooks */
/**
 * Form Components - Storybook Stories
 *
 * Interactive documentation for form-related components including
 * error messages, helper text, success indicators, and validated inputs.
 */

import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';

// Form Components
import { FormError } from './form-error';
import { FormHelper } from './form-helper';
import { FormSuccess } from './form-success';
import { ValidatedInput } from './validated-input';
import { t } from '@/i18n'

/* ===============================================
   FORM ERROR STORIES
   =============================================== */

const formErrorMeta: Meta<typeof FormError> = {
  title: 'Forms/Form Error',
  component: FormError,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
    docs: {
      description: {
        component: `
Reusable error message component with brand-aligned styling. Displays validation errors with proper accessibility attributes.

**Features:**
- Alert icon with error text
- Proper ARIA attributes (\role="alert", aria-live="polite")
- Brand-aligned error colors
- Dark mode support

**Accessibility:**
// eslint-disable-next-line no-useless-escape
- Uses \role="alert"\ for immediate screen reader announcement
// eslint-disable-next-line no-useless-escape
- aria-live="polite"\ for dynamic updates
        `,
      },
    },
  },
};

export default formErrorMeta;

type FormErrorStory = StoryObj<typeof FormError>;

export const ErrorDefault: FormErrorStory = {
  args: {
    error: 'This field is required',
  },
};

export const ErrorLongMessage: FormErrorStory = {
  args: {
    error: 'Your password must be at least 8 characters long and include at least one uppercase letter, one lowercase letter, and one number.',
  },
  parameters: {
    docs: {
      description: {
        story: 'Error message with longer, more detailed text',
      },
    },
  },
};

export const ErrorBrandVoice: FormErrorStory = {
  args: {
    error: 'Hmm, that email doesn\'t look quite right. Double-check for typos?',
  },
  parameters: {
    docs: {
      description: {
        story: 'Error message using L30 brand voice - warm and helpful',
      },
    },
  },
};

/* ===============================================
   FORM HELPER STORIES
   =============================================== */

export const HelperDefault: StoryObj<typeof FormHelper> = {
  args: {
    text: 'Enter your email address to receive updates',
  },
};

export const HelperWithIcon: StoryObj<typeof FormHelper> = {
  args: {
    text: 'Choose a password with at least 8 characters',
    showIcon: true,
  },
  parameters: {
    docs: {
      description: {
        story: 'Helper text with question mark icon for extra visibility',
      },
    },
  },
};

export const HelperLongText: StoryObj<typeof FormHelper> = {
  args: {
    text: 'Your library card number can be found on the back of your physical library card, or in your welcome email. Contact us if you need help finding it.',
    showIcon: true,
  },
  parameters: {
    docs: {
      description: {
        story: 'Longer helper text with detailed instructions',
      },
    },
  },
};

/* ===============================================
   FORM SUCCESS STORIES
   =============================================== */

export const SuccessWithMessage: StoryObj<typeof FormSuccess> = {
  args: {
    message: 'Looks good!',
  },
};

export const SuccessIconOnly: StoryObj<typeof FormSuccess> = {
  args: {},
  parameters: {
    docs: {
      description: {
        story: 'Success indicator without visible message (still has screen reader text)',
      },
    },
  },
};

export const SuccessDetailedMessage: StoryObj<typeof FormSuccess> = {
  args: {
    message: 'Email format is valid and available',
  },
  parameters: {
    docs: {
      description: {
        story: 'Success with more detailed confirmation message',
      },
    },
  },
};

/* ===============================================
   VALIDATED INPUT STORIES
   =============================================== */

export const InputBasic: StoryObj<typeof ValidatedInput> = {
  render: () => {
    const [value, setValue] = useState('');
    return (
      <ValidatedInput
        id="basic-input"
        label="Email Address"
        value={value}
        onChange={setValue}
        placeholder={t('placeholder.ui.youexamplecom')}
        type="email"
      />
    );
  },
  parameters: {
    docs: {
      description: {
        story: 'Basic validated input without validation function',
      },
    },
  },
};

export const InputWithValidation: StoryObj<typeof ValidatedInput> = {
  render: () => {
    const [value, setValue] = useState('');

    const validateEmail = (email: string): string | null => {
      if (!email) return 'Email is required';
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        return 'Please enter a valid email address';
      }
      return null;
    };

    return (
      <ValidatedInput
        id="email-input"
        label="Email Address"
        value={value}
        onChange={setValue}
        validationFn={validateEmail}
        placeholder={t('placeholder.ui.youexamplecom')}
        type="email"
        required
        helperText="We'll use this to send you library updates"
      />
    );
  },
  parameters: {
    docs: {
      description: {
        story: 'Input with validation function - try entering invalid email and then blur',
      },
    },
  },
};

export const InputPassword: StoryObj<typeof ValidatedInput> = {
  render: () => {
    const [value, setValue] = useState('');

    const validatePassword = (password: string): string | null => {
      if (!password) return 'Password is required';
      if (password.length < 8) {
        return 'Password must be at least 8 characters';
      }
      if (!/[A-Z]/.test(password)) {
        return 'Password must include at least one uppercase letter';
      }
      if (!/[a-z]/.test(password)) {
        return 'Password must include at least one lowercase letter';
      }
      if (!/[0-9]/.test(password)) {
        return 'Password must include at least one number';
      }
      return null;
    };

    return (
      <ValidatedInput
        id="password-input"
        label="Password"
        value={value}
        onChange={setValue}
        validationFn={validatePassword}
        type="password"
        required
        helperText="At least 8 characters with uppercase, lowercase, and number"
        autoComplete="new-password"
      />
    );
  },
  parameters: {
    docs: {
      description: {
        story: 'Password input with visibility toggle and comprehensive validation',
      },
    },
  },
};

export const InputWithCharacterCount: StoryObj<typeof ValidatedInput> = {
  render: () => {
    const [value, setValue] = useState('');

    return (
      <ValidatedInput
        id="bio-input"
        label="Bio"
        value={value}
        onChange={setValue}
        placeholder={t('placeholder.ui.tellUsAboutYourself')}
        maxLength={150}
        showCharacterCount
        helperText="This will appear on your public profile"
      />
    );
  },
  parameters: {
    docs: {
      description: {
        story: 'Input with character counter that changes color when approaching limit',
      },
    },
  },
};

export const InputDisabled: StoryObj<typeof ValidatedInput> = {
  render: () => {
    const [value, setValue] = useState('john.doe@example.com');

    return (
      <ValidatedInput
        id="disabled-input"
        label="Email Address"
        value={value}
        onChange={setValue}
        disabled
        helperText="Email cannot be changed once account is created"
      />
    );
  },
  parameters: {
    docs: {
      description: {
        story: 'Disabled input field',
      },
    },
  },
};

export const InputWithExternalError: StoryObj<typeof ValidatedInput> = {
  render: () => {
    const [value, setValue] = useState('taken@example.com');

    return (
      <ValidatedInput
        id="external-error-input"
        label="Email Address"
        value={value}
        onChange={setValue}
        error="This email is already registered. Try logging in instead?"
        helperText="We'll use this to send you library updates"
        required
      />
    );
  },
  parameters: {
    docs: {
      description: {
        story: 'Input with external error (e.g., from server-side validation)',
      },
    },
  },
};

export const InputSuccessState: StoryObj<typeof ValidatedInput> = {
  render: () => {
    const [value, setValue] = useState('valid@example.com');

    const validateEmail = (email: string): string | null => {
      if (!email) return 'Email is required';
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        return 'Please enter a valid email address';
      }
      return null;
    };

    return (
      <ValidatedInput
        id="success-input"
        label="Email Address"
        value={value}
        onChange={setValue}
        validationFn={validateEmail}
        showSuccessState
        helperText="Click outside the field to trigger validation"
        required
      />
    );
  },
  parameters: {
    docs: {
      description: {
        story: 'Input showing success state after validation passes (blur the field to see)',
      },
    },
  },
};

/* ===============================================
   COMPLETE FORM EXAMPLE
   =============================================== */

export const CompleteFormExample: StoryObj = {
  render: () => {
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');

    const validateEmail = (email: string): string | null => {
      if (!email) return null; // Don't show error for empty
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        return 'Hmm, that doesn\'t look like a valid email. Double-check for typos?';
      }
      return null;
    };

    const validatePassword = (password: string): string | null => {
      if (!password) return null;
      if (password.length < 8) {
        return 'Password needs to be at least 8 characters';
      }
      return null;
    };

    return (
      <form className="space-y-6 max-w-md" onSubmit={(e) => e.preventDefault()}>
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          Create Account
        </h2>

        <ValidatedInput
          id="name"
          label="Full Name"
          value={name}
          onChange={setName}
          placeholder={t('placeholder.ui.janeDoe')}
          required
          helperText="As it appears on your library card"
        />

        <ValidatedInput
          id="email"
          label="Email Address"
          value={email}
          onChange={setEmail}
          validationFn={validateEmail}
          type="email"
          required
          helperText="We'll send your welcome info here"
        />

        <ValidatedInput
          id="password"
          label="Password"
          value={password}
          onChange={setPassword}
          validationFn={validatePassword}
          type="password"
          required
          helperText="At least 8 characters"
          maxLength={50}
          showCharacterCount
        />

        <button
          type="submit"
          className="w-full px-6 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-semibold shadow-sm hover:shadow-md transition-all focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2"
        >
          Sign Up
        </button>
      </form>
    );
  },
  parameters: {
    docs: {
      description: {
        story: 'Complete registration form example using validated inputs',
      },
    },
  },
};
