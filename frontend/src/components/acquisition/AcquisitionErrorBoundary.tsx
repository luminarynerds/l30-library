/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Component, type ReactNode } from "react"
import { AlertTriangle } from "lucide-react"

interface Props {
  children: ReactNode
  fallbackMessage?: string
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class AcquisitionErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="border border-status-danger-200 dark:border-status-danger-800 bg-status-danger-50 dark:bg-status-danger-900/20 rounded-xl p-6 text-center" role="alert">
          <AlertTriangle aria-hidden="true" className="w-8 h-8 text-status-danger-500 mx-auto mb-3" />
          <p className="font-medium text-status-danger-700 dark:text-status-danger-300">
            {this.props.fallbackMessage || "We had trouble loading this section."}
          </p>
          <p className="text-sm text-status-danger-600 dark:text-status-danger-400 mt-1">
            {this.state.error?.message}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="mt-4 px-4 py-2 bg-status-danger-100 dark:bg-status-danger-900/40 text-status-danger-700 dark:text-status-danger-300 rounded-xl text-sm font-medium hover:bg-status-danger-200 dark:hover:bg-status-danger-900/60"
          >
            Try Again
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
