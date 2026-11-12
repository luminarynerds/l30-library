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
    title: t('checkPrintJobsGuide.checkYourPrintJobStatus', 'Check Your Print Job Status'),
    content: t('checkPrintJobsGuide.introContent', `Need to know if your print job is printing, waiting, or ready to pick up?

Before you start, you will need:
• Your library card number
• Your library account password or PIN
• A device with internet access (to check online)

This guide covers:
✓ Where to check if your job is queued (waiting to print)
✓ How to see if your job is currently printing
✓ Where to pick up your printed documents
✓ What to do if your job didn't print`),
    tips: [
      t('checkPrintJobsGuide.introTip1', 'Most print jobs start within a few minutes'),
      t('checkPrintJobsGuide.introTip2', 'Jobs are typically printed in order received'),
      t('checkPrintJobsGuide.introTip3', 'If you just sent the job, it may still be processing'),
    ],
  },
  {
    id: 'check-library-account',
    title: t('checkPrintJobsGuide.checkStatusInYourLibrary', 'Check Status in Your Library Account'),
    content: t('checkPrintJobsGuide.checkLibraryAccountContent', `The quickest way to check your print job status:

Step 1: Log Into Your Account
1. Go to the library website
2. Click "Log In" or "My Account"
3. Enter your library card number
4. Enter your password or PIN
5. Click "Sign In"

Step 2: Find Print Jobs
1. Once logged in, look for:
   - "Account" section
   - "My Prints" or "Print Jobs" tab
   - "Documents" or "Files" area
2. You should see a list of your recent print jobs

Step 3: Check Status
Look for one of these statuses:

[QUEUED] Waiting
• Your job is in line to print
• Will start printing soon
• Usually starts within 5 minutes

[PRINTING] In Progress
• Your job is currently printing
• Will be done in a few minutes
• Check back shortly

[READY] Complete
• Your job has finished printing.
• Go to the print station to pick it up
• You may need to pay at the desk

[FAILED] Error
• Your job didn't print
• Reason usually shown (low ink, paper jam, etc.)
• Try printing again from your device

Step 4: Find Your Documents
1. When status shows "READY"
2. Go to the print station in the library
3. Tell staff: "I have a print job ready"
4. They'll get your documents
5. Pay if needed ($0.10/page B&W)`),
    tips: [
      t('checkPrintJobsGuide.checkLibraryAccountTip1', 'Check your account first - quickest way to get status'),
      t('checkPrintJobsGuide.checkLibraryAccountTip2', 'Print jobs usually start within 5 minutes of sending'),
      t('checkPrintJobsGuide.checkLibraryAccountTip3', 'If your job says FAILED, try printing again'),
      t('checkPrintJobsGuide.checkLibraryAccountTip4', 'Staff can help locate your documents if unsure'),
    ],
  },
  {
    id: 'check-at-desk',
    title: t('checkPrintJobsGuide.checkStatusInPersonAt', 'Check Status In Person at the Library'),
    content: t('checkPrintJobsGuide.checkAtDeskContent', `If you can't check online, ask library staff:

What to Do:
1. Go to the main circulation desk
2. Tell staff: "I sent a print job. Can you check the status?"
3. Provide:
   • Your library card number, OR
   • Your name and birthdate
4. Staff will look it up in the system
5. They'll tell you:
   • If it's printed and ready
   • If it's still in the queue
   • If there was a problem

What If It's Ready?
1. Staff will fetch your documents
2. They'll show you what was printed
3. They'll tell you the cost (if any)
4. You can pay with cash or card
5. Take your documents and you're done!

What If It's Still Printing?
1. Staff will tell you approximately how long
2. You can:
   • Wait and check back
   • Ask them to hold it
   • Check online later
   • Come back another time (they'll keep it safe)`),
    tips: [
      t('checkPrintJobsGuide.checkAtDeskTip1', 'Staff usually have your job found within 2 minutes'),
      t('checkPrintJobsGuide.checkAtDeskTip2', 'Bring your library card for fastest service'),
      t('checkPrintJobsGuide.checkAtDeskTip3', 'Staff are used to this question - ask anytime.'),
      t('checkPrintJobsGuide.checkAtDeskTip4', 'Your documents are kept safely at the desk'),
    ],
  },
  {
    id: 'troubleshooting-failed',
    title: t('checkPrintJobsGuide.problemJobShowsFailed', 'Problem: Job Shows FAILED'),
    content: t('checkPrintJobsGuide.troubleshootingFailedContent', `If your status shows FAILED or your job doesn't appear:

Status Shows "FAILED":
What happened:
• Printer ran out of paper
• Printer ran out of ink
• Paper jam in the printer
• Printer was offline

Solution:
1. Log back into your account
2. Find the failed job
3. Click "Retry" or "Print Again"
4. Job gets sent back to the printer
5. It will print now that problem is fixed

Job Doesn't Appear in Account:
What happened:
• Job may still be processing (takes a minute)
• Job may have gone to wrong printer
• Job sent but account didn't save it

Solution:
1. Wait a few minutes and refresh
2. Try printing again (send it a second time)
3. Go to desk and ask staff to search by:
   • Your name
   • Library card number
   • Time you sent the job
4. Staff can see all recent jobs in the system`),
    tips: [
      t('checkPrintJobsGuide.troubleshootingFailedTip1', 'FAILED just means retry - not a big deal'),
      t('checkPrintJobsGuide.troubleshootingFailedTip2', 'Printer problems are usually fixed within minutes'),
      t('checkPrintJobsGuide.troubleshootingFailedTip3', 'Staff can see all recent jobs in the system'),
    ],
  },
  {
    id: 'troubleshooting-wrong',
    title: t('checkPrintJobsGuide.problemJobPrintedWrong', 'Problem: Job Printed Wrong'),
    content: t('checkPrintJobsGuide.troubleshootingWrongContent', `If your job printed but the documents are missing or wrong:

What happened:
• You picked up wrong job (similar name?)
• Documents already discarded (kept 30 days)
• Print job went to different branch

Solution:
1. Ask staff: "I sent a job on [date/time], but I don't have it"
2. Staff will check their lost & found
3. Describe what the job was (how many pages, what topic)
4. They may find it or be able to reprint
5. If over 30 days old, it has been removed for privacy`),
    tips: [
      t('checkPrintJobsGuide.troubleshootingWrongTip1', 'Staff have seen every issue - never embarrassing to ask'),
      t('checkPrintJobsGuide.troubleshootingWrongTip2', 'Preview your document before sending 10-page jobs'),
    ],
  },
  {
    id: 'troubleshooting-cost',
    title: t('checkPrintJobsGuide.problemCostWasHigher', 'Problem: Cost Was Higher Than Expected'),
    content: t('checkPrintJobsGuide.troubleshootingCostContent', `If your print job cost more than you expected:

What happened:
• Color pages cost more than B&W
• Large file used more pages
• Multiple jobs combined onto bill

Solution:
1. Ask staff to itemize the charges
2. They can show what printed
3. Clarify pricing if different than expected
4. For future: preview your document before printing
5. Ask staff about volume discounts if regular user`),
    tips: [
      t('checkPrintJobsGuide.troubleshootingCostTip1', 'If unsure about cost, ask staff BEFORE printing'),
      t('checkPrintJobsGuide.troubleshootingCostTip2', 'B&W is usually $0.10/page - color costs more'),
    ],
  },
  {
    id: 'before-you-print',
    title: t('checkPrintJobsGuide.beforeYouPrint', 'Before You Print'),
    content: t('checkPrintJobsGuide.beforeYouPrintContent', `A few checks before you hit "Print" can save time and money:

1. Preview Your Document
   • Open the file you want to print
   • Check that it looks right
   • Make sure it's not 500 pages by accident!
   • See how many pages it will be
   • Close if not ready to print

2. Check Your Settings
   Computer Windows:
   • Go to Print (Ctrl+P)
   • Before clicking "Print":
     ✓ Check printer name
     ✓ Check # of pages
     ✓ Check color vs B&W
     ✓ Check paper size
   • Then click "Print"

   Mac:
   • Go to File → Print (Command+P)
   • Before clicking "Print":
     ✓ Check printer name (should be library printer)
     ✓ Check # of pages
     ✓ Check color vs B&W
   • Then click "Print"

3. If Cost Matters
   • Ask staff the price for your number of pages
   • Color printing = more expensive
   • B&W = $0.10/page (usual rate)
   • Calculate before sending

4. Check File Format
   • PDFs print best (most reliable)
   • Word documents (.docx) usually fine
   • Google Docs might print differently than expected
   • Images may come out different sizes`),
    tips: [
      t('checkPrintJobsGuide.beforeYouPrintTip1', 'Preview = fewer problems and happier printing'),
      t('checkPrintJobsGuide.beforeYouPrintTip2', 'Ask questions BEFORE printing if worried about cost'),
      t('checkPrintJobsGuide.beforeYouPrintTip3', 'Staff can help you preview if unsure how'),
    ],
  },
  {
    id: 'while-printing',
    title: t('checkPrintJobsGuide.whilePrinting', 'While Printing'),
    content: t('checkPrintJobsGuide.whilePrintingContent', `What to do at the library computer when you're ready to print:

1. Look at "Print Preview"
   • On Windows: Ctrl+P usually shows preview
   • On Mac: Command+P usually shows preview
   • Make sure it looks right before printing
   • Cancel if it doesn't look correct

2. Send to Correct Printer
   • Make sure you select library printer name
   • Don't send to "Microsoft Print to PDF"
   • Don't send to "Default Printer" unless you're sure

3. Wait for Confirmation
   • After you hit "Print"
   • Look for a message: "Print job sent"
   • Or on library computer: "Document printing"
   • Don't close the dialog right away
   • Wait for the job to process`),
    tips: [
      t('checkPrintJobsGuide.whilePrintingTip1', 'Double-check the printer name before clicking Print'),
      t('checkPrintJobsGuide.whilePrintingTip2', 'Most printing issues are fixed before you leave'),
    ],
  },
  {
    id: 'after-printing',
    title: t('checkPrintJobsGuide.afterPrinting', 'After Printing'),
    content: t('checkPrintJobsGuide.afterPrintingContent', `Once you've sent the job, here's what to do:

1. Check Your Account Immediately
   • Log into library account right away
   • Confirm your job shows in the system
   • Check the status
   • Better to know right away if something failed

2. Wait Patiently
   • Jobs usually start within 5 minutes
   • Don't think it failed if you don't see it immediately
   • Give it time to queue

3. Pick Up Promptly
   • Once "READY", go get it soon
   • Documents are kept for about 30 days
   • Going right away ensures you get correct job`),
    tips: [
      t('checkPrintJobsGuide.afterPrintingTip1', 'Check status right away so you know if something failed'),
      t('checkPrintJobsGuide.afterPrintingTip2', 'Documents are kept for about 30 days'),
    ],
  },
  {
    id: 'complete',
    title: t('checkPrintJobsGuide.readyToPrint', "You're Ready to Print!"),
    content: t('checkPrintJobsGuide.completeContent', `You now know how to check your print status!

Quick Summary:
✓ Log into your account to check status online (fastest)
✓ Ask staff at the desk to look it up (easiest if having trouble)
✓ Status shows: QUEUED, PRINTING, READY, or FAILED
✓ Pick up documents at the circulation desk when ready
✓ If FAILED, just try printing again

For Future Printing:
✓ Preview your document first
✓ Check print settings (B&W vs color, page count)
✓ Know the cost before printing big jobs
✓ Check your account right after printing
✓ Pick up promptly when READY

If You Get Stuck:
• Ask staff - they help with printing all day
• Come back to this guide for troubleshooting
• Staff can reprints from the original file if needed
• Printing problems are fixable.

Questions?
• Visit the print station
• Call the library
• Chat with staff at the desk
• We're here to help!`),
    tips: [
      t('checkPrintJobsGuide.completeTip1', 'Staff would rather help than have you wait unsure'),
      t('checkPrintJobsGuide.completeTip2', 'Printing is one of the most common help requests - very normal'),
      t('checkPrintJobsGuide.completeTip3', "Come back to this guide anytime you're unsure"),
    ],
  },
]

export default function CheckPrintJobsGuide(): React.ReactElement {
  const { t } = useTranslation()
  const steps = useMemo(() => _buildSteps(t), [t])
  return (
    <GuidedWalkthrough
      guideId="check-print-jobs"
      title={t('checkPrintJobsGuide.checkYourPrintJobStatus2')}
      description={t('checkPrintJobsGuide.pageDescription', 'Find out if your print job is queued, printing, or ready to pick up')}
      steps={steps}
      onComplete={() => {
      }}
    />
  )
}
