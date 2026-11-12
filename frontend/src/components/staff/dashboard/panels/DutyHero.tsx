/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from "react"
import { Target, Coffee, BookOpen, Users, Sparkles, Moon } from "lucide-react"

interface DutySlot {
  mission: string
  subtitle: string
  icon: React.ElementType
}

const ROLE_LABELS: Record<string, string> = {
  front_desk: "Front desk",
  page_shelver: "Shelving",
  marketing: "Marketing",
  kids_services: "Kids services",
  board_ops: "Board ops",
  board_president: "Board president",
}

const DUTY_MAP: Record<string, DutySlot[]> = {
  front_desk: [
    { mission: "Opening Prep", subtitle: "Desk check, cash drawer, holds shelf", icon: Coffee },
    { mission: "Morning Circulation", subtitle: "Steady flow -- checkouts and renewals", icon: BookOpen },
    { mission: "Lunch Rush", subtitle: "High volume -- keep the line moving", icon: Users },
    { mission: "Afternoon Programs", subtitle: "Program support and patron assistance", icon: Sparkles },
    { mission: "After-School Wave", subtitle: "Students arriving -- homework help ready", icon: Users },
    { mission: "Evening Wind-Down", subtitle: "Final holds, closing prep", icon: Moon },
  ],
  page_shelver: [
    { mission: "Overnight Returns", subtitle: "Process the book drop", icon: BookOpen },
    { mission: "Cart Processing", subtitle: "Sort and stage for reshelving", icon: Target },
    { mission: "Reshelving Push", subtitle: "Clear the backlog", icon: BookOpen },
    { mission: "Display Maintenance", subtitle: "Refresh end caps and feature shelves", icon: Sparkles },
    { mission: "End-of-Day Carts", subtitle: "Final round of returns", icon: BookOpen },
    { mission: "Closing Sweep", subtitle: "Shelf-read priority sections", icon: Moon },
  ],
  marketing: [
    { mission: "Social Check-In", subtitle: "Review overnight engagement", icon: Coffee },
    { mission: "Content Creation", subtitle: "Draft posts, design graphics", icon: Sparkles },
    { mission: "Analytics Review", subtitle: "Check campaign performance", icon: Target },
    { mission: "Campaign Planning", subtitle: "Upcoming events and promotions", icon: Target },
    { mission: "Community Engagement", subtitle: "Respond to comments and messages", icon: Users },
    { mission: "Schedule Tomorrow", subtitle: "Queue posts for morning", icon: Moon },
  ],
  kids_services: [
    { mission: "Program Setup", subtitle: "Prepare craft supplies and space", icon: Coffee },
    { mission: "Story Time Prep", subtitle: "Books selected, reading nook ready", icon: BookOpen },
    { mission: "Craft Cleanup", subtitle: "Reset activity stations", icon: Sparkles },
    { mission: "After-School Welcome", subtitle: "Greet young patrons", icon: Users },
    { mission: "Homework Help", subtitle: "Support students with resources", icon: BookOpen },
    { mission: "Activity Wrap-Up", subtitle: "Clean up and plan tomorrow", icon: Moon },
  ],
  board_ops: [
    { mission: "Morning Review", subtitle: "Check pending items and correspondence", icon: Coffee },
    { mission: "Document Prep", subtitle: "Board materials and agenda items", icon: Target },
    { mission: "Midday Check", subtitle: "Follow up on action items", icon: BookOpen },
    { mission: "Afternoon Planning", subtitle: "Committee coordination", icon: Users },
    { mission: "Evening Prep", subtitle: "Prepare for evening meetings", icon: Sparkles },
    { mission: "Day Close", subtitle: "Review and wrap up", icon: Moon },
  ],
  board_president: [
    { mission: "Morning Briefing", subtitle: "Review director updates", icon: Coffee },
    { mission: "Strategic Review", subtitle: "Policy and planning focus", icon: Target },
    { mission: "Midday Check-In", subtitle: "Staff and community matters", icon: Users },
    { mission: "Governance Work", subtitle: "Sign-offs and approvals", icon: BookOpen },
    { mission: "Community Relations", subtitle: "Stakeholder engagement", icon: Sparkles },
    { mission: "Day Summary", subtitle: "Review and plan ahead", icon: Moon },
  ],
}

function getCurrentSlotIndex(): number {
  const hour = new Date().getHours()
  if (hour < 9) return -1
  if (hour < 10) return 0
  if (hour < 12) return 1
  if (hour < 14) return 2
  if (hour < 16) return 3
  if (hour < 18) return 4
  if (hour < 20) return 5
  return -1
}

interface DutyHeroProps {
  role: string
  inline?: boolean
}

export default function DutyHero({ role, inline = false }: DutyHeroProps) {
  const [slotIndex, setSlotIndex] = useState(getCurrentSlotIndex)

  useEffect(() => {
    const interval = setInterval(() => setSlotIndex(getCurrentSlotIndex()), 60_000)
    return () => clearInterval(interval)
  }, [])

  const slots = DUTY_MAP[role]
  if (!slots || slotIndex < 0) return null

  const slot = slots[slotIndex]
  if (!slot) return null

  const Icon = slot.icon

  if (inline) {
    const roleLabel = ROLE_LABELS[role] ?? role
    return (
      <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60 flex items-center gap-1.5">
        <Icon className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
        <span>
          <span className="font-medium text-lsc-dark/80 dark:text-lsc-cream/80">{roleLabel}</span>
          <span className="mx-1.5 text-lsc-dark/30 dark:text-lsc-cream/30">/</span>
          <span>{slot.mission}</span>
          <span className="text-lsc-dark/40 dark:text-lsc-cream/40"> -- {slot.subtitle}</span>
        </span>
      </p>
    )
  }

  return (
    <div className="bg-gradient-to-r from-lsc-rose/10 to-transparent dark:from-lsc-rose/5 rounded-xl p-4 border border-lsc-rose/20 dark:border-lsc-rose/10">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-lsc-rose/10 dark:bg-lsc-rose/20 rounded-lg">
          <Icon className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
        </div>
        <div>
          <div className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">{slot.mission}</div>
          <div className="text-xs text-earth-600 dark:text-earth-400">{slot.subtitle}</div>
        </div>
      </div>
    </div>
  )
}
