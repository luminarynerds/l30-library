/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

interface RequireAuthProps {
  children: React.ReactNode
  /** Optional array of required roles. If not provided, only authentication is required. */
  requiredRoles?: string[]
}

export default function RequireAuth({ children, requiredRoles }: RequireAuthProps): React.ReactElement | null {
  const { user, isLoading, isAuthenticated } = useAuth()
  const location = useLocation()

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-lsc-cream dark:bg-lsc-dark">
        <div className="text-center">
          <div className="motion-safe:animate-spin rounded-full h-12 w-12 border-b-2 border-lsc-rose mx-auto mb-4" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Loading...</p>
        </div>
      </div>
    )
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    // Save the current location so we can redirect back after login
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  // Check role requirements if specified
  if (requiredRoles && requiredRoles.length > 0 && user) {
    const userRole = (user.role || 'patron').toLowerCase()

    // super_admin has access to everything
    if (userRole === 'super_admin') {
      return <>{children}</>
    }

    const hasRequiredRole = requiredRoles.some(role => {
      if (role.toLowerCase() === "board_member") return !!user.is_board_member
      return userRole === role.toLowerCase()
    })

    if (!hasRequiredRole) {
      // User doesn't have required role - redirect to account page with error
      return <Navigate to="/account" state={{ accessDenied: true }} replace />
    }
  }

  // User is authenticated (and has required role if specified)
  return <>{children}</>
}
