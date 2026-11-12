/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Toast Notification Utilities & Constants
 * Centralized toast message management for consistent user feedback
 */

import toast from 'react-hot-toast'

/**
 * Standardized toast messages organized by category
 */
export const TOAST_MESSAGES = {
  // User Management
  user: {
    createSuccess: 'User created successfully',
    updateSuccess: 'User updated successfully',
    deleteSuccess: 'User deleted successfully',
    createError: 'Failed to create user',
    updateError: 'Failed to update user',
    deleteError: 'Failed to delete user',
    lockSuccess: 'User locked successfully',
    unlockSuccess: 'User unlocked successfully',
    passwordResetSuccess: 'Password reset link sent',
    passwordResetError: 'Failed to reset password',
  },

  // Role Management
  role: {
    createSuccess: 'Role created successfully',
    updateSuccess: 'Role updated successfully',
    deleteSuccess: 'Role deleted successfully',
    createError: 'Failed to create role',
    updateError: 'Failed to update role',
    deleteError: 'Failed to delete role',
    permissionsUpdated: 'Role permissions updated',
  },

  // Catalog/Item Management
  item: {
    createSuccess: 'Item added to catalog successfully',
    updateSuccess: 'Item updated successfully',
    deleteSuccess: 'Item removed from catalog',
    createError: 'Failed to add item to catalog',
    updateError: 'Failed to update item',
    deleteError: 'Failed to remove item',
    bulkUploadSuccess: 'Items imported successfully',
    bulkUploadError: 'Failed to import items',
  },

  // Announcement Management
  announcement: {
    createSuccess: 'Announcement created successfully',
    updateSuccess: 'Announcement updated successfully',
    deleteSuccess: 'Announcement deleted successfully',
    publishSuccess: 'Announcement published',
    archiveSuccess: 'Announcement archived',
    createError: 'Failed to create announcement',
    updateError: 'Failed to update announcement',
    deleteError: 'Failed to delete announcement',
  },

  // Event Management
  event: {
    createSuccess: 'Event created successfully',
    updateSuccess: 'Event updated successfully',
    deleteSuccess: 'Event deleted successfully',
    registerSuccess: 'Successfully registered for event',
    unregisterSuccess: 'Event registration cancelled',
    createError: 'Failed to create event',
    updateError: 'Failed to update event',
    deleteError: 'Failed to delete event',
  },

  // Patron Management
  patron: {
    createSuccess: 'Patron account created successfully',
    updateSuccess: 'Patron information updated',
    deleteSuccess: 'Patron account deleted',
    blockSuccess: 'Patron account blocked',
    unblockSuccess: 'Patron account unblocked',
    createError: 'Failed to create patron account',
    updateError: 'Failed to update patron information',
    deleteError: 'Failed to delete patron account',
  },

  // Circulation Operations
  circulation: {
    checkoutSuccess: 'Item checked out successfully',
    returnSuccess: 'Item returned successfully',
    renewSuccess: 'Item renewed successfully',
    holdSuccess: 'Hold placed successfully',
    holdCancelSuccess: 'Hold cancelled',
    checkoutError: 'Checkout failed',
    returnError: 'Return failed',
    renewError: 'Renewal failed',
    holdError: 'Failed to place hold',
  },

  // Fine Management
  fine: {
    paymentSuccess: 'Payment processed successfully',
    waiverSuccess: 'Fine waived successfully',
    paymentError: 'Payment processing failed',
    waiverError: 'Failed to waive fine',
  },

  // Staff Management
  staff: {
    scheduleUpdated: 'Schedule updated successfully',
    performanceRecorded: 'Performance record saved',
    trainingCompleted: 'Training marked as complete',
    scheduleError: 'Failed to update schedule',
    performanceError: 'Failed to save performance record',
  },

  // General Operations
  general: {
    success: 'Operation completed successfully',
    error: 'Operation failed',
    saveSuccess: 'Changes saved successfully',
    saveError: 'Failed to save changes',
    deleteConfirmation: 'Item deleted',
    confirmationNeeded: 'Please confirm this action',
    loadingError: 'Failed to load data',
    networkError: 'Network error occurred',
    validationError: 'Please check your input and try again',
  },

  // Authentication
  auth: {
    loginSuccess: 'Logged in successfully',
    logoutSuccess: 'Logged out successfully',
    loginError: 'Login failed',
    sessionExpired: 'Your session has expired',
    unauthorizedError: 'You do not have permission to perform this action',
  },

  // Form Operations
  form: {
    submitSuccess: 'Form submitted successfully',
    submitError: 'Failed to submit form',
    validationRequired: 'Please complete all required fields',
    fieldError: 'Please fix the errors in the form',
  },
} as const

export function notifySuccess(message: string, duration = 4000): void {
  toast.success(message, { duration })
}

export function notifyError(
  error: unknown,
  defaultMessage: string,
  duration = 5000
): void {
  let errorMessage = defaultMessage

  if (error instanceof Error) {
    errorMessage = error.message || defaultMessage
  } else if (typeof error === 'string') {
    errorMessage = error
  } else if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as Record<string, unknown>).detail
    errorMessage = typeof detail === 'string' ? detail : defaultMessage
  }

  toast.error(errorMessage, { duration })
}

export function notifyWarning(message: string, duration = 4500): void {
  toast(message, {
    duration,
    icon: '⚠️',
  })
}

export function notifyInfo(message: string, duration = 4000): void {
  toast(message, {
    duration,
    icon: 'ℹ️',
  })
}

export function notifyLoading(message: string): string {
  return toast.loading(message)
}

export function dismissToast(toastId: string): void {
  toast.dismiss(toastId)
}

export function updateToast(
  toastId: string,
  message: string,
  type: 'success' | 'error' | 'info' | 'warning' = 'success'
): void {
  const toastFunctions: Record<string, (msg: string) => void> = {
    success: (msg) => toast.success(msg, { id: toastId }),
    error: (msg) => toast.error(msg, { id: toastId }),
    info: (msg) => toast(msg, { id: toastId }),
    warning: (msg) => toast(msg, { id: toastId, icon: '⚠️' }),
  }

  const fn = toastFunctions[type]
  if (fn) {
    fn(message)
  }
}
