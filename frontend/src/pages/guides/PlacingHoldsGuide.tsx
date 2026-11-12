/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo } from 'react'
import GuidedWalkthrough, { type WalkthroughStep } from '@/components/GuidedWalkthrough'
import { useTranslation } from '@/i18n'

const _buildSteps = (t: (key: string, fallback?: string) => string): WalkthroughStep[] => [
  {
    id: 'search-catalog',
    title: t('placingHoldsGuide.step1.title'),
    content: t('placingHoldsGuide.step1.content', `Ready to find something to read, watch, or listen to?

Before you start, you will need:
• Your library card number
• Your library account password or PIN

Here's how to search:

1. Go to the Catalog page (click "Catalog" in the top menu)
2. Type what you're looking for in the search bar
   - A book title, author name, or topic
   - Example: "mystery novels" or "Michelle Obama"
3. Press Enter or click Search

You'll see a list of matching items with:
• Title and author
• Format (book, DVD, audiobook, etc.)
• Availability at each branch

Use the filters on the left to narrow results by format, branch, or availability.`),
    tips: [
      t('placingHoldsGuide.step1.tip1', 'You don\'t need the exact title — partial matches work great'),
      t('placingHoldsGuide.step1.tip2', 'Use the format filter to find only audiobooks or DVDs'),
      t('placingHoldsGuide.step1.tip3', 'Sort by "Newest first" to see recently added items'),
      t('placingHoldsGuide.step1.tip4', 'You can search from the homepage search bar too'),
    ],
  },
  {
    id: 'find-item',
    title: t('placingHoldsGuide.step2.title'),
    content: t('placingHoldsGuide.step2.content', `Click on any item in the search results to see its detail page.

On the detail page you'll find:
• Full description and details
• Available formats (hardcover, paperback, large print, etc.)
• Which branches have copies
• Current availability status:
  - "Available" — on the shelf now
  - "Checked Out" — someone has it, but you can place a hold
  - "In Transit" — moving between branches
  - "On Hold" — reserved for someone

If the item shows "Available" at your branch, you can go pick it up right now!

If it's checked out or at another branch, placing a hold is the way to go.`),
    tips: [
      t('placingHoldsGuide.step2.tip1', 'Check multiple formats — the audiobook might be available even if the print book isn\'t'),
      t('placingHoldsGuide.step2.tip2', 'The detail page shows how many people are waiting if there\'s a hold queue'),
      t('placingHoldsGuide.step2.tip3', 'You can add items to a reading list to save them for later'),
    ],
  },
  {
    id: 'click-place-hold',
    title: t('placingHoldsGuide.step3.title'),
    content: t('placingHoldsGuide.step3.content', `On the item's detail page, look for the "Place Hold" button. It's usually a prominent orange button.

When you click it:
1. A confirmation dialog will appear
2. It shows the item title and format
3. You may see a format dropdown if multiple formats are available
   - Pick the one you want (hardcover, paperback, large print, etc.)

Note: You need to be logged in to place a hold. If you're not logged in, you'll be asked to sign in first.`),
    tips: [
      t('placingHoldsGuide.step3.tip1', 'You can place holds from search results too — look for the hold icon'),
      t('placingHoldsGuide.step3.tip2', 'If you\'re not logged in, clicking "Place Hold" will prompt you to sign in'),
      t('placingHoldsGuide.step3.tip3', 'You can hold up to 25 items at a time'),
    ],
    hasCheckpoint: true,
  },
  {
    id: 'choose-branch',
    title: t('placingHoldsGuide.step4.title'),
    content: t('placingHoldsGuide.step4.content', `After clicking "Place Hold," you'll be asked to select a pickup branch.

The dropdown shows all library branches:
• Your home branch is selected by default (if you set one during registration)
• Each branch shows its name and address
• Pick whichever branch is most convenient for you

The item will be sent to your chosen branch when it becomes available.

You can change your home branch anytime in your account settings.`),
    tips: [
      t('placingHoldsGuide.step4.tip1', 'Set a home branch in your account so it\'s always pre-selected'),
      t('placingHoldsGuide.step4.tip2', 'You can pick up at any branch — it doesn\'t have to be your home branch'),
      t('placingHoldsGuide.step4.tip3', 'Items from other branches usually arrive within 1-3 days'),
    ],
  },
  {
    id: 'confirm-hold',
    title: t('placingHoldsGuide.step5.title'),
    content: t('placingHoldsGuide.step5.content', `Click "Confirm" to finalize your hold.

You'll see:
• A success message: "Hold placed successfully!"
• The item now appears in your "My Holds" list

You'll be notified when the item is ready for pickup:
• Email notification (default)
• Text notification (if you opted in during registration)

Pickup window:
• You'll have 7 days to pick up the item once it's ready
• If you can't make it, the hold will be cancelled and the item goes to the next person in line`),
    tips: [
      t('placingHoldsGuide.step5.tip1', 'Check your email (including spam folder) for hold notifications'),
      t('placingHoldsGuide.step5.tip2', 'You can set up text notifications in your account preferences'),
      t('placingHoldsGuide.step5.tip3', 'If you need more time, call the branch — they may be able to extend your pickup window'),
    ],
    hasCheckpoint: true,
  },
  {
    id: 'track-hold',
    title: t('placingHoldsGuide.step6.title'),
    content: t('placingHoldsGuide.step6.content', `You can check on all your holds from your account:

1. Click your profile icon or go to "Account"
2. Click the "Holds" tab

Your holds list shows:
• Item title and format
• Pickup branch
• Status:
  - "Pending" — waiting for an available copy
  - "In Transit" — a copy is on its way to your branch
  - "Ready for Pickup" — it's waiting for you at the desk!
• Your position in the queue (e.g., "3rd in line")
• Estimated wait time

You can also:
• Cancel a hold you no longer want
• Change the pickup branch
• Pause a hold (useful if you're traveling)

That covers it. You now know how to place and manage holds.`),
    tips: [
      t('placingHoldsGuide.step6.tip1', 'The "My Holds" link on the homepage is a quick shortcut'),
      t('placingHoldsGuide.step6.tip2', 'Cancelling a hold frees up your hold slot for another item'),
      t('placingHoldsGuide.step6.tip3', 'You can pause and resume holds without losing your place in line'),
      t('placingHoldsGuide.step6.tip4', 'Popular items may have longer wait times — consider alternate formats'),
    ],
  },
]

export default function PlacingHoldsGuide(): React.ReactElement {
  const { t } = useTranslation()
  const steps = useMemo(() => _buildSteps(t), [t])
  return (
    <GuidedWalkthrough
      guideId="placing-holds"
      title={t('placingHoldsGuide.title')}
      description={t('placingHoldsGuide.description', 'Learn how to reserve books and other items for pickup at your preferred branch')}
      steps={steps}
      onComplete={() => {
      }}
    />
  )
}
