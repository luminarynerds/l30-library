/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Brand Messages Constants — i18n Key Exports
 *
 * This file exports translation keys (not raw strings) for the L30 brand voice.
 * Consumers call t(key) to get the translated string at render time.
 *
 * All actual strings live in i18n/translations/{en,es,fr}.json under "brand.*"
 */

// ============================================================================
// LOADING MESSAGE KEYS
// ============================================================================

export const LOADING_MESSAGE_KEYS = [
  "brand.loading.general.0",
  "brand.loading.general.1",
  "brand.loading.general.2",
  "brand.loading.general.3",
  "brand.loading.general.4",
  "brand.loading.general.5",
] as const

export const PAGE_LOADING_MESSAGE_KEYS = {
  catalog: "brand.loading.catalog",
  events: "brand.loading.events",
  notifications: "brand.loading.notifications",
  account: "brand.loading.account",
  default: "brand.loading.default",
} as const

export const BUTTON_LOADING_MESSAGE_KEYS = {
  save: "brand.buttonLoading.save",
  submit: "brand.buttonLoading.submit",
  register: "brand.buttonLoading.register",
  search: "brand.buttonLoading.search",
  delete: "brand.buttonLoading.delete",
  update: "brand.buttonLoading.update",
  load: "brand.buttonLoading.load",
  default: "brand.buttonLoading.default",
} as const

// ============================================================================
// EMPTY STATE KEYS
// ============================================================================

export const EMPTY_STATE_KEYS = {
  catalog: {
    noResults: {
      message: "brand.emptyState.catalog.noResults.message",
      suggestion: "brand.emptyState.catalog.noResults.suggestion",
    },
    noResultsWithFilters: {
      message: "brand.emptyState.catalog.noResultsWithFilters.message",
      suggestion: "brand.emptyState.catalog.noResultsWithFilters.suggestion",
    },
    initial: {
      message: "brand.emptyState.catalog.initial.message",
      suggestion: "brand.emptyState.catalog.initial.suggestion",
    },
  },
  events: {
    noEvents: {
      message: "brand.emptyState.events.noEvents.message",
      suggestion: "brand.emptyState.events.noEvents.suggestion",
    },
    noUpcoming: {
      message: "brand.emptyState.events.noUpcoming.message",
      suggestion: "brand.emptyState.events.noUpcoming.suggestion",
    },
    noPastEvents: {
      message: "brand.emptyState.events.noPastEvents.message",
      suggestion: "brand.emptyState.events.noPastEvents.suggestion",
    },
    noSavedEvents: {
      message: "brand.emptyState.events.noSavedEvents.message",
      suggestion: "brand.emptyState.events.noSavedEvents.suggestion",
    },
    noRegistrations: {
      message: "brand.emptyState.events.noRegistrations.message",
      suggestion: "brand.emptyState.events.noRegistrations.suggestion",
    },
  },
  notifications: {
    noNotifications: {
      message: "brand.emptyState.notifications.noNotifications.message",
      suggestion: "brand.emptyState.notifications.noNotifications.suggestion",
    },
    noNotificationsWithFilters: {
      message: "brand.emptyState.notifications.noNotificationsWithFilters.message",
      suggestion: "brand.emptyState.notifications.noNotificationsWithFilters.suggestion",
    },
  },
  account: {
    noCheckouts: {
      message: "brand.emptyState.account.noCheckouts.message",
      suggestion: "brand.emptyState.account.noCheckouts.suggestion",
    },
    noHolds: {
      message: "brand.emptyState.account.noHolds.message",
      suggestion: "brand.emptyState.account.noHolds.suggestion",
    },
    noHistory: {
      message: "brand.emptyState.account.noHistory.message",
      suggestion: "brand.emptyState.account.noHistory.suggestion",
    },
    noFavorites: {
      message: "brand.emptyState.account.noFavorites.message",
      suggestion: "brand.emptyState.account.noFavorites.suggestion",
    },
    noLists: {
      message: "brand.emptyState.account.noLists.message",
      suggestion: "brand.emptyState.account.noLists.suggestion",
    },
  },
  programs: {
    noPrograms: {
      message: "brand.emptyState.programs.noPrograms.message",
      suggestion: "brand.emptyState.programs.noPrograms.suggestion",
    },
    noCourses: {
      message: "brand.emptyState.programs.noCourses.message",
      suggestion: "brand.emptyState.programs.noCourses.suggestion",
    },
  },
  community: {
    noResources: {
      message: "brand.emptyState.community.noResources.message",
      suggestion: "brand.emptyState.community.noResources.suggestion",
    },
    noAnnouncements: {
      message: "brand.emptyState.community.noAnnouncements.message",
      suggestion: "brand.emptyState.community.noAnnouncements.suggestion",
    },
  },
  staff: {
    noResults: {
      message: "brand.emptyState.staff.noResults.message",
      suggestion: "brand.emptyState.staff.noResults.suggestion",
    },
    noItems: {
      message: "brand.emptyState.staff.noItems.message",
      suggestion: "brand.emptyState.staff.noItems.suggestion",
    },
  },
  generic: {
    noResults: {
      message: "brand.emptyState.generic.noResults.message",
      suggestion: "brand.emptyState.generic.noResults.suggestion",
    },
    empty: {
      message: "brand.emptyState.generic.empty.message",
      suggestion: "brand.emptyState.generic.empty.suggestion",
    },
  },
} as const

// ============================================================================
// ERROR MESSAGE KEYS
// ============================================================================

export const ERROR_MESSAGE_KEYS = {
  loadFailed: {
    title: "brand.errors.loadFailed.title",
    message: "brand.errors.loadFailed.message",
    suggestion: "brand.errors.loadFailed.suggestion",
  },
  saveFailed: {
    title: "brand.errors.saveFailed.title",
    message: "brand.errors.saveFailed.message",
    suggestion: "brand.errors.saveFailed.suggestion",
  },
  networkError: {
    title: "brand.errors.network.title",
    message: "brand.errors.network.message",
    suggestion: "brand.errors.network.suggestion",
  },
  notFound: {
    title: "brand.errors.notFound.title",
    message: "brand.errors.notFound.message",
    suggestion: "brand.errors.notFound.suggestion",
  },
} as const

// ============================================================================
// BRAND ERROR MESSAGE KEYS
// ============================================================================

export const BRAND_ERROR_MESSAGE_KEYS = {
  network: {
    offline: "brand.brandErrors.network.offline",
    timeout: "brand.brandErrors.network.timeout",
    serverUnavailable: "brand.brandErrors.network.serverUnavailable",
  },
  auth: {
    loginFailed: "brand.brandErrors.auth.loginFailed",
    cardLoginFailed: "brand.brandErrors.auth.cardLoginFailed",
    registrationFailed: "brand.brandErrors.auth.registrationFailed",
    sessionExpired: "brand.brandErrors.auth.sessionExpired",
    accountLocked: "brand.brandErrors.auth.accountLocked",
    rateLimited: "brand.brandErrors.auth.rateLimited",
    invalidCredentials: "brand.brandErrors.auth.invalidCredentials",
  },
  actions: {
    saveFailed: "brand.brandErrors.actions.saveFailed",
    deleteFailed: "brand.brandErrors.actions.deleteFailed",
    updateFailed: "brand.brandErrors.actions.updateFailed",
    submitFailed: "brand.brandErrors.actions.submitFailed",
    sendFailed: "brand.brandErrors.actions.sendFailed",
    loadFailed: "brand.brandErrors.actions.loadFailed",
  },
  access: {
    notFound: "brand.brandErrors.access.notFound",
    forbidden: "brand.brandErrors.access.forbidden",
    unauthorized: "brand.brandErrors.access.unauthorized",
  },
  fallback: {
    generic: "brand.brandErrors.fallback.generic",
    tryAgain: "brand.brandErrors.fallback.tryAgain",
    contactSupport: "brand.brandErrors.fallback.contactSupport",
  },
} as const

// ============================================================================
// VALIDATION MESSAGE KEYS
// ============================================================================

export const VALIDATION_MESSAGE_KEYS = {
  required: {
    default: "brand.validation.required.default",
    email: "brand.validation.required.email",
    password: "brand.validation.required.password",
    firstName: "brand.validation.required.firstName",
    lastName: "brand.validation.required.lastName",
    libraryCard: "brand.validation.required.libraryCard",
    pin: "brand.validation.required.pin",
  },
  format: {
    email: "brand.validation.format.email",
    passwordShort: "brand.validation.format.passwordShort",
    passwordNeedsNumber: "brand.validation.format.passwordNeedsNumber",
    passwordMismatch: "brand.validation.format.passwordMismatch",
    libraryCard: "brand.validation.format.libraryCard",
    pin: "brand.validation.format.pin",
    phone: "brand.validation.format.phone",
    url: "brand.validation.format.url",
    date: "brand.validation.format.date",
    number: "brand.validation.format.number",
  },
  tips: {
    password: "brand.validation.tips.password",
    email: "brand.validation.tips.email",
    phone: "brand.validation.tips.phone",
    address: "brand.validation.tips.address",
  },
} as const

// ============================================================================
// SUCCESS MESSAGE KEYS
// ============================================================================

export const SUCCESS_MESSAGE_KEYS = {
  saved: "brand.success.saved",
  submitted: "brand.success.submitted",
  sent: "brand.success.sent",
  deleted: "brand.success.deleted",
  updated: "brand.success.updated",
  loggedIn: "brand.success.loggedIn",
  registered: "brand.success.registered",
  passwordReset: "brand.success.passwordReset",
  holdPlaced: "brand.success.holdPlaced",
  itemReturned: "brand.success.itemReturned",
} as const

// ============================================================================
// CONFIRMATION DIALOG KEYS
// ============================================================================

export const CONFIRM_MESSAGE_KEYS = {
  unsavedChanges: {
    title: "brand.confirm.unsavedChangesTitle",
    message: "brand.confirm.unsavedChangesMessage",
    confirmText: "brand.confirm.unsavedChangesConfirm",
    cancelText: "brand.confirm.unsavedChangesCancel",
  },
  deleteItem: {
    title: "brand.confirm.deleteItemTitle",
    message: "brand.confirm.deleteItemMessage",
    confirmText: "brand.confirm.deleteItemConfirm",
    cancelText: "brand.confirm.deleteItemCancel",
  },
  cancelAction: {
    title: "brand.confirm.cancelActionTitle",
    message: "brand.confirm.cancelActionMessage",
    confirmText: "brand.confirm.cancelActionConfirm",
    cancelText: "brand.confirm.cancelActionCancel",
  },
  logout: {
    title: "brand.confirm.logoutTitle",
    message: "brand.confirm.logoutMessage",
    confirmText: "brand.confirm.logoutConfirm",
    cancelText: "brand.confirm.logoutCancel",
  },
} as const

// ============================================================================
// RESULT MESSAGE KEYS
// ============================================================================

export const RESULT_MESSAGE_KEYS = {
  foundOne: "brand.results.foundOne",
  foundFew: "brand.results.foundFew",
  foundSome: "brand.results.foundSome",
  foundMany: "brand.results.foundMany",
} as const

// ============================================================================
// HELPER FUNCTIONS (return keys, not strings)
// ============================================================================

export function getRandomLoadingMessageKey(): string {
  const idx = Math.floor(Math.random() * LOADING_MESSAGE_KEYS.length)
  return LOADING_MESSAGE_KEYS[idx] ?? "brand.loading.default"
}

export function getPageLoadingMessageKey(
  page: keyof typeof PAGE_LOADING_MESSAGE_KEYS,
): string {
  return PAGE_LOADING_MESSAGE_KEYS[page] || PAGE_LOADING_MESSAGE_KEYS.default
}

export function getButtonLoadingTextKey(
  action: keyof typeof BUTTON_LOADING_MESSAGE_KEYS,
): string {
  return BUTTON_LOADING_MESSAGE_KEYS[action] || BUTTON_LOADING_MESSAGE_KEYS.default
}

export function getResultsMessageKey(
  total: number,
  hasFilters: boolean = false,
): { key: string; params?: Record<string, unknown> } {
  if (total === 0) {
    return hasFilters
      ? { key: EMPTY_STATE_KEYS.catalog.noResultsWithFilters.message }
      : { key: EMPTY_STATE_KEYS.catalog.noResults.message }
  }
  if (total === 1) return { key: RESULT_MESSAGE_KEYS.foundOne }
  if (total <= 5) return { key: RESULT_MESSAGE_KEYS.foundFew, params: { count: total } }
  if (total <= 20) return { key: RESULT_MESSAGE_KEYS.foundSome, params: { count: total } }
  return { key: RESULT_MESSAGE_KEYS.foundMany }
}

// ============================================================================
// BACKWARD-COMPATIBLE ALIASES (deprecated — prefer *_KEYS exports)
// ============================================================================

/** @deprecated Use LOADING_MESSAGE_KEYS + t() */
export const LOADING_MESSAGES = LOADING_MESSAGE_KEYS
/** @deprecated Use PAGE_LOADING_MESSAGE_KEYS + t() */
export const PAGE_LOADING_MESSAGES = PAGE_LOADING_MESSAGE_KEYS
/** @deprecated Use BUTTON_LOADING_MESSAGE_KEYS + t() */
export const BUTTON_LOADING_MESSAGES = BUTTON_LOADING_MESSAGE_KEYS
/** @deprecated Use EMPTY_STATE_KEYS + t() */
export const EMPTY_STATE_MESSAGES = EMPTY_STATE_KEYS
/** @deprecated Use ERROR_MESSAGE_KEYS + t() */
export const ERROR_MESSAGES = ERROR_MESSAGE_KEYS
/** @deprecated Use BRAND_ERROR_MESSAGE_KEYS + t() */
export const BRAND_ERROR_MESSAGES = BRAND_ERROR_MESSAGE_KEYS
/** @deprecated Use VALIDATION_MESSAGE_KEYS + t() */
export const VALIDATION_MESSAGES = VALIDATION_MESSAGE_KEYS
/** @deprecated Use SUCCESS_MESSAGE_KEYS + t() */
export const SUCCESS_MESSAGES = SUCCESS_MESSAGE_KEYS
/** @deprecated Use CONFIRM_MESSAGE_KEYS + t() */
export const CONFIRM_MESSAGES = CONFIRM_MESSAGE_KEYS
/** @deprecated Use getRandomLoadingMessageKey + t() */
export const getRandomLoadingMessage = getRandomLoadingMessageKey
/** @deprecated Use getPageLoadingMessageKey + t() */
export const getPageLoadingMessage = getPageLoadingMessageKey
/** @deprecated Use getButtonLoadingTextKey + t() */
export const getButtonLoadingText = getButtonLoadingTextKey
/** @deprecated Use getResultsMessageKey + t() */
export const getResultsMessage = getResultsMessageKey
