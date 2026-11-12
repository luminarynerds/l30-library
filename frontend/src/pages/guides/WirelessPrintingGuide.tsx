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
    title: t('wirelessPrintingGuide.gettingStartedWithWirelessPrinting'),
    content: t('wirelessPrintingGuide.introContent', `Wireless printing allows you to print documents from your device without needing cables. This guide will walk you through connecting to our library's wireless printers.

Before you start, you will need:
• A charged device (phone, tablet, or laptop)
• The document or webpage you want to print
• Connection to the library WiFi network`),
    tips: [
      t('wirelessPrintingGuide.introTip1', 'Make sure your device is charged before starting'),
      t('wirelessPrintingGuide.introTip2', 'You\'ll need to be connected to the library WiFi network'),
      t('wirelessPrintingGuide.introTip3', 'Printers are available in the computer lab and reference areas'),
    ],
  },
  {
    id: 'connect-wifi',
    title: t('wirelessPrintingGuide.stepConnectToLibraryWifi'),
    content: t('wirelessPrintingGuide.stepConnectToLibraryWifiContent', `First, connect your device to the library WiFi network:

1. Open your device's WiFi settings
2. Look for network names starting with "LSC_" or "Library"
3. Select "LSC_Public" or the available library network
4. If prompted, enter the password posted at the library desk
5. Wait for a "Connected" confirmation`),
    tips: [
      t('wirelessPrintingGuide.stepConnectToLibraryWifiTip1', 'WiFi networks are available throughout the building'),
      t('wirelessPrintingGuide.stepConnectToLibraryWifiTip2', 'You may see multiple library networks - choose the strongest signal'),
      t('wirelessPrintingGuide.stepConnectToLibraryWifiTip3', 'Connection usually takes 10-30 seconds'),
    ],
    troubleshooting: t('wirelessPrintingGuide.stepConnectToLibraryWifiTroubleshooting', `If you can't connect: 1) Restart your device's WiFi, 2) Move closer to a WiFi access point, 3) Ask staff for the current WiFi password`),
    hasCheckpoint: true,
  },
  {
    id: 'find-printer',
    title: t('wirelessPrintingGuide.stepLocateAndSelectA'),
    content: t('wirelessPrintingGuide.stepLocateAndSelectAContent', `Now you'll add the printer to your device:

For Windows:
1. Open Settings → Devices → Printers & Scanners
2. Click "Add a printer or scanner"
3. Wait for the library printers to appear
4. Select "LSC_Library_Printer_Main" from the list
5. Click "Add device"

For Mac:
1. Click the Apple menu → System Settings → Printers & Scanners
2. Click the "+" button
3. Select the "Windows/Samba" printer option
4. Enter: smb://LSC_Library_Printer_Main
5. Click "Add"

For Mobile Devices:
1. Open Settings → Bluetooth & Device Connection → Printers
2. Select "LSC_Library_Printer_Mobile"
3. Follow the pairing prompts`),
    tips: [
      t('wirelessPrintingGuide.stepLocateAndSelectATip1', 'Printer names usually indicate their location (Main, Lab, Front Desk)'),
      t('wirelessPrintingGuide.stepLocateAndSelectATip2', 'Make sure you select the printer that\'s closest to you'),
      t('wirelessPrintingGuide.stepLocateAndSelectATip3', 'Installation usually takes 1-2 minutes'),
    ],
    troubleshooting: t('wirelessPrintingGuide.stepLocateAndSelectATroubleshooting', `If printer doesn't appear: 1) Ensure WiFi is connected, 2) Restart your device, 3) Forget and reconnect to WiFi`),
  },
  {
    id: 'print-test',
    title: t('wirelessPrintingGuide.stepPrintATestDocument'),
    content: t('wirelessPrintingGuide.stepPrintATestDocumentContent', `Let's print a test page to confirm everything works:

1. Open any document or photo on your device
2. Look for a "Share" or "Print" button (usually in the File menu)
3. Select your printer from the list
4. Choose:
   - Copies: 1
   - Color: Black & White (saves money!)
   - Paper size: Letter (8.5" x 11")
5. Tap or click "Print"
6. Your document should print within 30 seconds`),
    tips: [
      t('wirelessPrintingGuide.stepPrintATestDocumentTip1', 'Black & white printing costs $0.10 per page'),
      t('wirelessPrintingGuide.stepPrintATestDocumentTip2', 'Color printing is available but costs more'),
      t('wirelessPrintingGuide.stepPrintATestDocumentTip3', 'Check that you\'re printing to the right printer before confirming'),
    ],
    troubleshooting: t('wirelessPrintingGuide.stepPrintATestDocumentTroubleshooting', `If nothing prints: 1) Check the printer display to see if there's an error, 2) Ask staff to help troubleshoot, 3) Try printing from a different application`),
    hasCheckpoint: true,
  },
  {
    id: 'collect',
    title: t('wirelessPrintingGuide.stepCollectYourPrintout'),
    content: t('wirelessPrintingGuide.stepCollectYourPrintoutContent', `Your document is ready!

1. Head to the printer location (check the printer name for location)
2. Look for your document in the output tray
3. If using paid printing, your page may be held at the desk
4. Pay the cashier if you haven't already set up an account

That's it! You've successfully printed wirelessly.`),
    tips: [
      t('wirelessPrintingGuide.stepCollectYourPrintoutTip1', 'Keep printouts organized - staff will discard unclaimed prints after 2 weeks'),
      t('wirelessPrintingGuide.stepCollectYourPrintoutTip2', 'If you print multiple jobs, check all output trays'),
      t('wirelessPrintingGuide.stepCollectYourPrintoutTip3', 'Ask staff if you need help finding your document'),
    ],
  },
  {
    id: 'advanced',
    title: t('wirelessPrintingGuide.advancedPrintingFromCloudServices'),
    content: t('wirelessPrintingGuide.advancedPrintingFromCloudServicesContent', `You can also print documents stored online:

From Google Drive:
1. Open your document in Google Drive
2. Click File → Print
3. Select your library printer
4. Click Print

From OneDrive/Office:
1. Open your document in Office Online
2. Click File → Print
3. Select your library printer
4. Click Print

From Email Attachments:
1. Open the attachment in your email
2. Tap the Share/Print icon
3. Select your library printer
4. Confirm and print`),
    tips: [
      t('wirelessPrintingGuide.advancedPrintingFromCloudServicesTip1', 'You can print from any cloud service that supports printing'),
      t('wirelessPrintingGuide.advancedPrintingFromCloudServicesTip2', 'Keep passwords private - don\'t let others access your cloud accounts at library computers'),
      t('wirelessPrintingGuide.advancedPrintingFromCloudServicesTip3', 'Larger files may take a few extra seconds to process'),
    ],
  },
  {
    id: 'complete',
    title: t('wirelessPrintingGuide.youreAllSet', 'You\'re All Set!'),
    content: t('wirelessPrintingGuide.youreAllSetContent', `All done. You now know how to use wireless printing at the library.

Quick Reference:
• WiFi Network: LSC_Public
• Main Printer: LSC_Library_Printer_Main
• Black & White: $0.10 per page
• Ask for help: Reference Desk or Tech Help Area

Come back anytime if you need help!`),
    tips: [
      t('wirelessPrintingGuide.youreAllSetTip1', 'Bookmark this guide for future reference'),
      t('wirelessPrintingGuide.youreAllSetTip2', 'Printers are available during all library hours'),
      t('wirelessPrintingGuide.youreAllSetTip3', 'Staff members are always available to help'),
    ],
  },
]

export default function WirelessPrintingGuide(): React.ReactElement {
  const { t } = useTranslation()
  const steps = useMemo(() => _buildSteps(t), [t])
  return (
    <GuidedWalkthrough
      guideId="wireless-printing"
      title={t('wirelessPrintingGuide.wirelessPrintingAtTheLibrary')}
      description={t('wirelessPrintingGuide.description', 'Learn how to print from your device using our wireless printing service')}
      steps={steps}
      onComplete={() => {
      }}
    />
  )
}
