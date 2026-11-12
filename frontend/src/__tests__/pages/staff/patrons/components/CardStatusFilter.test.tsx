/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { screen, fireEvent } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import { render } from "../../../../utils/test-utils"
import { PatronSearchPanel } from "@/pages/staff/patrons/components/PatronSearchPanel"
import { PatronStatisticsDashboard } from "@/components/staff/patrons/PatronStatisticsDashboard"
import type { PatronStatistics } from "@/api/staff-api/patrons"

const baseAdvancedProps = {
  advancedFilters: {},
  onAdvancedFiltersChange: vi.fn(),
  onClearAdvancedFilters: vi.fn(),
  activeFilterCount: 0,
}

function renderPanel(extra: Partial<typeof baseAdvancedProps> = {}) {
  const onChange = vi.fn()
  const utils = render(
    <PatronSearchPanel
      searchQuery=""
      onSearchQueryChange={vi.fn()}
      statusFilter="all"
      onStatusFilterChange={vi.fn()}
      onSearch={vi.fn()}
      isSearching={false}
      {...baseAdvancedProps}
      {...extra}
      onAdvancedFiltersChange={onChange}
    />
  )
  return { ...utils, onChange }
}

function buildStats(
  overrides: Partial<PatronStatistics> = {}
): PatronStatistics {
  return {
    total_patrons: 100,
    active_patrons: 95,
    blocked_patrons: 5,
    new_this_week: 0,
    new_this_month: 0,
    total_fines_outstanding: 0,
    total_overdue_items: 0,
    at_risk_counts: {
      patrons_with_many_overdue: 0,
      patrons_with_high_fines: 0,
      inactive_patrons: 0,
    },
    expiring_cards_counts: {
      expiring_within_30d: 7,
      expiring_within_90d: 21,
      expired: 3,
    },
    patrons_with_many_overdue: [],
    patrons_with_high_fines: [],
    inactive_patrons: [],
    ...overrides,
  }
}

describe("PatronSearchPanel cardStatus filter", () => {
  it("renders the cardStatus select when advanced panel opens", () => {
    const { container } = renderPanel()
    fireEvent.click(screen.getByRole("button", { name: /advanced filters/i }))
    const select = container.querySelector(
      "#patron-card-status-filter"
    ) as HTMLSelectElement | null
    expect(select).not.toBeNull()
    expect(select!.value).toBe("any")
  })

  it("emits cardStatus when the select changes", () => {
    const { onChange, container } = renderPanel()
    fireEvent.click(screen.getByRole("button", { name: /advanced filters/i }))
    const select = container.querySelector(
      "#patron-card-status-filter"
    ) as HTMLSelectElement
    fireEvent.change(select, { target: { value: "expiring_30d" } })
    expect(onChange).toHaveBeenCalledWith({ cardStatus: "expiring_30d" })
  })

  it("clears cardStatus when 'any' is chosen", () => {
    const { onChange, container } = renderPanel({
      advancedFilters: { cardStatus: "expired" },
    })
    fireEvent.click(screen.getByRole("button", { name: /advanced filters/i }))
    const select = container.querySelector(
      "#patron-card-status-filter"
    ) as HTMLSelectElement
    fireEvent.change(select, { target: { value: "any" } })
    expect(onChange).toHaveBeenCalledWith({})
  })
})

describe("PatronStatisticsDashboard expiring-cards tile", () => {
  const baseProps = {
    isLoading: false,
    isDashboardExpanded: true,
    onExpandChange: vi.fn(),
    activeAlertFilter: "none" as const,
    onAlertFilterChange: vi.fn(),
    onAlertClick: vi.fn(),
    onOpenPatron: vi.fn(),
    onRemindPatron: vi.fn(),
    formatDate: (d: string) => d,
  }

  it("renders all three expiring-card counts when present", () => {
    render(
      <PatronStatisticsDashboard
        {...baseProps}
        statistics={buildStats()}
        onExpiringCardsClick={vi.fn()}
      />
    )
    const tile = screen.getByTestId("expiring-cards-tile")
    expect(tile).toHaveTextContent("7")
    expect(tile).toHaveTextContent("21")
    expect(tile).toHaveTextContent("3")
  })

  it("calls onExpiringCardsClick with the right band on click", () => {
    const onClick = vi.fn()
    render(
      <PatronStatisticsDashboard
        {...baseProps}
        statistics={buildStats()}
        onExpiringCardsClick={onClick}
      />
    )
    fireEvent.click(screen.getByTestId("expiring-cards-tile-30d"))
    fireEvent.click(screen.getByTestId("expiring-cards-tile-90d"))
    fireEvent.click(screen.getByTestId("expiring-cards-tile-expired"))
    expect(onClick).toHaveBeenNthCalledWith(1, "expiring_30d")
    expect(onClick).toHaveBeenNthCalledWith(2, "expiring_90d")
    expect(onClick).toHaveBeenNthCalledWith(3, "expired")
  })

  it("hides the tile entirely when all expiring counts are zero", () => {
    render(
      <PatronStatisticsDashboard
        {...baseProps}
        statistics={buildStats({
          expiring_cards_counts: {
            expiring_within_30d: 0,
            expiring_within_90d: 0,
            expired: 0,
          },
        })}
        onExpiringCardsClick={vi.fn()}
      />
    )
    expect(screen.queryByTestId("expiring-cards-tile")).toBeNull()
  })
})
