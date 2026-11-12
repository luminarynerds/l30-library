/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { API_BASE } from '@/api/types'
/**
 * API Configuration Constants
 * Centralized API endpoint configuration
 */

// Determine API base URL based on environment
const getApiBaseUrl = (): string => {
  // If running in a browser, use relative path to current origin
  if (typeof window !== 'undefined') {
    return `${API_BASE}`
  }

  // Default for SSR/build time
  return process.env.REACT_APP_API_URL || `${API_BASE}`
}

export const API_BASE_URL = getApiBaseUrl()

// API Endpoints
export const API_ENDPOINTS = {
  // Auth
  AUTH: {
    LOGIN: `${API_BASE_URL}/auth/login`,
    LOGOUT: `${API_BASE_URL}/auth/logout`,
    REFRESH: `${API_BASE_URL}/auth/refresh`,
    VERIFY: `${API_BASE_URL}/auth/verify`,
  },

  // Admin/Staff
  ADMIN: {
    ANALYTICS: {
      SHARING_DASHBOARD: `${API_BASE_URL}/admin/analytics/sharing-dashboard`,
    },
  },

  // Catalog
  CATALOG: {
    ITEMS: `${API_BASE_URL}/catalog`,
  },

  // Reading Programs
  READING_PROGRAMS: {
    LIST: `${API_BASE_URL}/reading-programs`,
  },

  // Events
  EVENTS: {
    LIST: `${API_BASE_URL}/events`,
  },
}

export const API_TIMEOUT = 30000 // 30 seconds
export const REQUEST_RETRY_ATTEMPTS = 3