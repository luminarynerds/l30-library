/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo } from 'react'
import GuidedWalkthrough, { type WalkthroughStep } from '@/components/GuidedWalkthrough'
import { useTranslation } from '@/i18n'

const _buildSteps = (t: (key: string, fallback?: string) => string): WalkthroughStep[] => [
  {
    id: 'intro',
    title: t('libraryCardGuide.getYourLibraryCard'),
    content: t('libraryCardGuide.introContent', `A library card unlocks access to everything at our library:
✓ Borrow books, movies, and music
✓ Use computers and WiFi
✓ Access online resources
✓ Print documents
✓ Attend events and classes
✓ Get tech support

Library cards are free.

This guide shows you how to apply for your card.`),
    tips: [
      t('libraryCardGuide.introTip1', 'Takes about 5-10 minutes to apply'),
      t('libraryCardGuide.introTip2', 'You\'ll get your card number immediately'),
      t('libraryCardGuide.introTip3', 'Bring ID and proof of address'),
      t('libraryCardGuide.introTip4', 'Cards never expire'),
    ],
  },
  {
    id: 'online-apply',
    title: t('libraryCardGuide.optionApplyOnlineFastest'),
    content: t('libraryCardGuide.onlineApplyContent', `Want your card right now? Apply online:

1. Go to our library website
2. Look for "Get a Library Card" or "Apply Online"
3. Fill in the form:
   - Full name
   - Date of birth
   - Email address
   - Phone number
   - Home address

4. Agree to the terms
5. Click "Submit"

You'll get:
• Instant library card number
• Email confirmation with your number
• Instructions to pick up your physical card

Then:
• Come to the library with ID
• Show your confirmation email
• Get your plastic library card
• You're done.

Most people complete this in 5 minutes online.`),
    tips: [
      t('libraryCardGuide.onlineApplyTip1', 'You can start borrowing immediately with your number'),
      t('libraryCardGuide.onlineApplyTip2', 'Physical card comes when you pick it up'),
      t('libraryCardGuide.onlineApplyTip3', 'Keep your confirmation email'),
      t('libraryCardGuide.onlineApplyTip4', 'Bring valid ID when you visit'),
    ],
    hasCheckpoint: true,
  },
  {
    id: 'in-person-apply',
    title: t('libraryCardGuide.optionApplyInPerson'),
    content: t('libraryCardGuide.inPersonApplyContent', `Prefer to apply at the library? Here's how:

What to Bring:
Required:
✓ Valid photo ID (driver's license, passport, etc.)
✓ Proof of current address (utility bill, lease, bank statement)

Helpful (but not required):
✓ Library card number if you had one before
✓ Any ID you might have

At the Library:
1. Go to the front desk
2. Tell staff: "I'd like to get a library card"
3. Staff will:
   - Check your ID
   - Ask you a few questions
   - Create your account on the computer
   - Scan your ID and proof of address
   - Print your library card

You'll walk out with:
• Plastic library card in your hand
• Your library card number
• Ability to borrow, print, and use computers immediately

Time needed: About 10 minutes

Location:
• Main desk (ask any staff member)
• Open during library hours`),
    tips: [
      t('libraryCardGuide.inPersonApplyTip1', 'Bring both forms of ID to avoid any delays'),
      t('libraryCardGuide.inPersonApplyTip2', 'Staff can answer questions about your account'),
      t('libraryCardGuide.inPersonApplyTip3', 'Get your physical card same day'),
      t('libraryCardGuide.inPersonApplyTip4', 'Ask about getting your kids cards too'),
    ],
  },
  {
    id: 'what-next',
    title: t('libraryCardGuide.gotYourCardWhatNow', 'You\'ve Got Your Card - What Now?'),
    content: t('libraryCardGuide.whatNextContent', `Congratulations! Now you can use everything at the library:

Borrowing Materials:
• Check out books at self-checkout or desk
• Most items: 3-4 weeks to borrow
• Movies and CDs: usually 1 week
• You can have 50+ items at a time
• Renew items online or by phone

Using Computers:
• Log in with your library card number
• Browse the internet
• Work on documents
• Use Microsoft Office (Word, Excel, etc.)
• Print documents for $0.10/page (B&W)

Accessing Online:
• Log into your account online
• Search the catalog from home
• Renew items anytime
• Place holds on books
• Manage your account

Attending Programs:
• Many programs are free
• Some require registration
• Look for classes, events, workshops
• Ask staff what's available

Getting Support:
• Ask staff any questions
• Visit our tech support area
• Get help with devices and WiFi
• Attend classes and training

Your PIN:
• Staff gave you a 4-digit PIN
• Write it down and keep it safe
• Use it at self-checkout machines
• Use it for phone renewals
• You can change it anytime`),
    tips: [
      t('libraryCardGuide.whatNextTip1', 'Your library card works anywhere in the system'),
      t('libraryCardGuide.whatNextTip2', 'Download the library app for quick access'),
      t('libraryCardGuide.whatNextTip3', 'Follow the library on social media for news'),
      t('libraryCardGuide.whatNextTip4', 'Ask about library programs and events'),
    ],
  },
  {
    id: 'lost-card',
    title: t('libraryCardGuide.lostOrDamagedCard'),
    content: t('libraryCardGuide.lostCardContent', `No problem. This is common.

If Your Card is Lost:
1. Tell library staff immediately
2. They'll deactivate it (so no one else uses it)
3. They'll issue you a new one (small fee)
4. You can keep using your library number right away

If Your Card is Damaged:
1. Bring it to the library desk
2. Staff will see if it can be read
3. If not, they'll issue a new one
4. Usually no charge if we damaged it

You can always:
• Call the library to report a lost card
• Use your library number without the card
• Renew items by phone using your number
• Come in anytime to get a replacement

Tip:
• Take a photo of your card and store it on your phone
• Write down your card number somewhere safe
• You don't always need the physical card`),
    tips: [
      t('libraryCardGuide.lostCardTip1', 'Call right away if your card is lost - faster service'),
      t('libraryCardGuide.lostCardTip2', 'Your library number stays the same forever'),
      t('libraryCardGuide.lostCardTip3', 'You can use your number without the physical card'),
      t('libraryCardGuide.lostCardTip4', 'Replacement cards usually cost $1-2'),
    ],
  },
  {
    id: 'faq',
    title: t('libraryCardGuide.commonQuestions', 'Common Questions'),
    content: (
      <div className="space-y-2">
        <p className="text-sm text-lsc-dark/85 dark:text-lsc-cream/85 mb-4">{t('libraryCardGuide.faqIntro', 'Common questions about library cards:')}</p>
        <details className="group rounded-lg border border-lsc-border dark:border-earth-700">
          <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 motion-safe:transition-colors">
            {t('libraryCardGuide.faqResidentQuestion', 'Do I need to be a resident?')}
          </summary>
          <div className="px-4 pb-3 text-sm text-lsc-dark/75 dark:text-lsc-cream/80">
            {t('libraryCardGuide.faqResidentAnswer', 'Some areas require local address. Ask staff or check the website.')}
          </div>
        </details>
        <details className="group rounded-lg border border-lsc-border dark:border-earth-700">
          <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 motion-safe:transition-colors">
            {t('libraryCardGuide.faqKidsQuestion', 'Can kids get cards?')}
          </summary>
          <div className="px-4 pb-3 text-sm text-lsc-dark/75 dark:text-lsc-cream/80">
            {t('libraryCardGuide.faqKidsAnswer', 'Yes! Children, teens, and adults all get cards. Parents sign for children under 18.')}
          </div>
        </details>
        <details className="group rounded-lg border border-lsc-border dark:border-earth-700">
          <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 motion-safe:transition-colors">
            {t('libraryCardGuide.faqVisitQuestion', 'Do I need a card to visit?')}
          </summary>
          <div className="px-4 pb-3 text-sm text-lsc-dark/75 dark:text-lsc-cream/80">
            {t('libraryCardGuide.faqVisitAnswer', 'No! Anyone can visit, use computers, and attend events. Card is for borrowing.')}
          </div>
        </details>
        <details className="group rounded-lg border border-lsc-border dark:border-earth-700">
          <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 motion-safe:transition-colors">
            {t('libraryCardGuide.faqDurationQuestion', 'How long do cards last?')}
          </summary>
          <div className="px-4 pb-3 text-sm text-lsc-dark/75 dark:text-lsc-cream/80">
            {t('libraryCardGuide.faqDurationAnswer', "Forever! Your card doesn't expire as long as you use it.")}
          </div>
        </details>
        <details className="group rounded-lg border border-lsc-border dark:border-earth-700">
          <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 motion-safe:transition-colors">
            {t('libraryCardGuide.faqMultipleQuestion', 'Can I have multiple cards?')}
          </summary>
          <div className="px-4 pb-3 text-sm text-lsc-dark/75 dark:text-lsc-cream/80">
            {t('libraryCardGuide.faqMultipleAnswer', "One per person. You can't transfer your card to someone else.")}
          </div>
        </details>
        <details className="group rounded-lg border border-lsc-border dark:border-earth-700">
          <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 motion-safe:transition-colors">
            {t('libraryCardGuide.faqPinQuestion', 'Can I change my PIN?')}
          </summary>
          <div className="px-4 pb-3 text-sm text-lsc-dark/75 dark:text-lsc-cream/80">
            {t('libraryCardGuide.faqPinAnswer', 'Yes! Ask any staff member anytime.')}
          </div>
        </details>
        <details className="group rounded-lg border border-lsc-border dark:border-earth-700">
          <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 motion-safe:transition-colors">
            {t('libraryCardGuide.faqMoveQuestion', 'What if I move?')}
          </summary>
          <div className="px-4 pb-3 text-sm text-lsc-dark/75 dark:text-lsc-cream/80">
            <p>{t('libraryCardGuide.faqMoveIntro', 'Update your address:')}</p>
            <ul className="list-disc list-inside mt-1 space-y-0.5">
              <li>{t('libraryCardGuide.faqMoveItem1', 'Online through your account')}</li>
              <li>{t('libraryCardGuide.faqMoveItem2', 'By calling the library')}</li>
              <li>{t('libraryCardGuide.faqMoveItem3', 'By visiting in person')}</li>
              <li>{t('libraryCardGuide.faqMoveItem4', 'Your card number stays the same')}</li>
            </ul>
          </div>
        </details>
        <details className="group rounded-lg border border-lsc-border dark:border-earth-700">
          <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 motion-safe:transition-colors">
            {t('libraryCardGuide.faqFinesQuestion', 'What if I owe fines?')}
          </summary>
          <div className="px-4 pb-3 text-sm text-lsc-dark/75 dark:text-lsc-cream/80">
            <ul className="list-disc list-inside space-y-0.5">
              <li>{t('libraryCardGuide.faqFinesItem1', 'You can still visit and use computers')}</li>
              <li>{t('libraryCardGuide.faqFinesItem2', "You won't be able to borrow until paid")}</li>
              <li>{t('libraryCardGuide.faqFinesItem3', 'Ask about fine amnesty programs')}</li>
              <li>{t('libraryCardGuide.faqFinesItem4', 'Staff can work with you on payment plans')}</li>
            </ul>
          </div>
        </details>
        <details className="group rounded-lg border border-lsc-border dark:border-earth-700">
          <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 motion-safe:transition-colors">
            {t('libraryCardGuide.faqShareQuestion', "Can I use someone else's card?")}
          </summary>
          <div className="px-4 pb-3 text-sm text-lsc-dark/75 dark:text-lsc-cream/80">
            {t('libraryCardGuide.faqShareAnswer', 'No - library cards are personal. But they can get their own for free!')}
          </div>
        </details>
        <details className="group rounded-lg border border-lsc-border dark:border-earth-700">
          <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 motion-safe:transition-colors">
            {t('libraryCardGuide.faqInactiveQuestion', "What if I haven't visited in years?")}
          </summary>
          <div className="px-4 pb-3 text-sm text-lsc-dark/75 dark:text-lsc-cream/80">
            <p>{t('libraryCardGuide.faqInactiveIntro', 'Your card might be inactive, but:')}</p>
            <ul className="list-disc list-inside mt-1 space-y-0.5">
              <li>{t('libraryCardGuide.faqInactiveItem1', 'Come visit and reactivate it')}</li>
              <li>{t('libraryCardGuide.faqInactiveItem2', 'Staff can help you get started again')}</li>
              <li>{t('libraryCardGuide.faqInactiveItem3', 'Your account history is still there')}</li>
            </ul>
          </div>
        </details>
      </div>
    ),
    tips: [
      t('libraryCardGuide.faqTip1', 'Ask staff about programs available to cardholders'),
      t('libraryCardGuide.faqTip2', 'Library cards are invaluable - keep yours safe'),
      t('libraryCardGuide.faqTip3', 'Get friends and family cards too'),
      t('libraryCardGuide.faqTip4', "Visit the library - we're here for you!"),
    ],
  },
  {
    id: 'complete',
    title: t('libraryCardGuide.welcomeToTheLibrary'),
    content: t('libraryCardGuide.completeContent', `You're ready to use everything our library offers!

Your Next Steps:
✓ Pick up or use your card number
✓ Explore the catalog online
✓ Come in and browse in person
✓ Ask staff about programs
✓ Download the library app
✓ Set up your online account

Remember:
• Library staff are here to help
• No question is too small
• We have resources for everyone
• Come visit anytime during our hours

Contact Info:
Hours: Mon-Fri 9am-8pm, Sat 10am-5pm, Sun 1pm-5pm
Website: Check your confirmation email

Welcome to your library.`),
    tips: [
      t('libraryCardGuide.completeTip1', 'Your card is your key to lifelong learning'),
      t('libraryCardGuide.completeTip2', 'Library staff love helping patrons'),
      t('libraryCardGuide.completeTip3', 'Explore everything available to you'),
      t('libraryCardGuide.completeTip4', 'Tell friends and family they can get one too.'),
    ],
  },
]

export default function LibraryCardGuide(): React.ReactElement {
  const { t } = useTranslation()
  const steps = useMemo(() => _buildSteps(t), [t])
  return (
    <GuidedWalkthrough
      guideId="library-card"
      title={t('libraryCardGuide.getYourLibraryCard2')}
      description={t('libraryCardGuide.pageDescription', 'Easy step-by-step guide to apply for your free library card')}
      steps={steps}
      onComplete={() => undefined}
    />
  )
}
