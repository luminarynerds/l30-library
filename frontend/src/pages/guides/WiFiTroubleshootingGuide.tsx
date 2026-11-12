/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo } from 'react'
import { ChevronLeft, Wifi, AlertCircle, WifiOff, Lock, Signal, Gauge } from 'lucide-react'
import { useTranslation } from '@/i18n'
import GuidedWalkthrough, { type WalkthroughStep } from '@/components/GuidedWalkthrough'
import PageContainer from '@/components/layout/PageContainer'

type TroubleshootingPath = 'no-network' | 'connection-fails' | 'keeps-disconnecting' | 'slow-speed' | null

interface ProblemConfig {
  name: string
  steps: WalkthroughStep[]
}

function buildPaths(t: (key: string, fallback?: string) => string): Record<NonNullable<TroubleshootingPath>, ProblemConfig> {
  return {
    'no-network': {
      name: t('wiFiTroubleshootingGuide.cantSeeTheWifiNetwork', "Can't See the WiFi Network"),
      steps: [
        {
          id: 'no-network-enable-wifi',
          title: t('wiFiTroubleshootingGuide.stepConfirmWifiIsEnabled'),
          content: t('wiFiTroubleshootingGuide.stepConfirmWifiIsEnabledContent', `Make sure your device's WiFi is turned on:

Windows or Laptop:
• Look for a WiFi icon in the bottom right corner
• It should show a WiFi symbol (looks like curved lines)
• If grayed out, click it to turn WiFi ON

iPhone or iPad:
• Swipe down from top-right corner to open Control Center
• Look for the WiFi icon (looks like curved lines)
• If it's not filled in, tap it to turn WiFi ON

Android Phone:
• Swipe down twice to open full Quick Settings
• Find "WiFi" button
• Tap it if it's off (should turn blue when on)

Try these solutions:
• Turn WiFi off and back on (wait 10 seconds)
• Restart your device completely
• Check if airplane mode is ON - turn it OFF`),
          tips: [
            t('wiFiTroubleshootingGuide.stepConfirmWifiIsEnabledTip1', 'WiFi symbols are the same on all devices - curved lines'),
            t('wiFiTroubleshootingGuide.stepConfirmWifiIsEnabledTip2', 'Airplane mode blocks all wireless - disable it first'),
          ],
          hasCheckpoint: true,
        },
        {
          id: 'no-network-right-place',
          title: t('wiFiTroubleshootingGuide.stepConfirmLookingInRightPlace', "Step 2: Confirm You're Looking in the Right Place"),
          content: t('wiFiTroubleshootingGuide.stepConfirmLookingInRightPlaceContent', `WiFi networks appear in a list. Make sure you're looking at the complete list:

Windows:
• Click the WiFi icon in the bottom right
• A popup shows all available networks
• Scroll down if list is long
• Look for networks starting with "LSC_" or "Library"

iPhone/iPad:
• Go to Settings → WiFi
• Wait a few seconds for the full list to load
• Look for networks with "LSC_" or "Library" in the name

Android:
• Go to Settings → Network & Internet → WiFi
• Tap "See all" if you don't see many networks
• Look for networks starting with "LSC_" or "Library"

Try these solutions:
• Move closer to a library WiFi access point (near windows, public areas)
• Wait 30 seconds for the network list to fully load
• Scroll down in the network list - may be below other networks`),
          tips: [
            t('wiFiTroubleshootingGuide.stepConfirmLookingInRightPlaceTip1', 'The library has multiple access points - you might see LSC_1, LSC_2, LSC_3, etc.'),
            t('wiFiTroubleshootingGuide.stepConfirmLookingInRightPlaceTip2', 'Choose the one with the strongest signal (full bars)'),
          ],
        },
        {
          id: 'no-network-move-closer',
          title: t('wiFiTroubleshootingGuide.stepMoveCloserToThe'),
          content: t('wiFiTroubleshootingGuide.stepMoveCloserToTheContent', `WiFi has range limits - closer is better!

Where to try:
• Near the main desk area
• In the computer lab
• By the windows
• In the public seating areas

What to avoid:
• Restrooms (no WiFi coverage)
• Storage areas (signal blocked by materials)
• Outer walls (weaker signal outside)
• Basement areas (if signal doesn't reach there)

Try these solutions:
• Walk around the library finding areas with good reception
• Ask staff "Where has the strongest WiFi?" - they know!
• Look for other patrons on devices - usually good signal there`),
          tips: [
            t('wiFiTroubleshootingGuide.stepMoveCloserToTheTip1', 'Concrete, brick, and many books block WiFi signals'),
            t('wiFiTroubleshootingGuide.stepMoveCloserToTheTip2', 'Metal objects and microwaves can interfere with WiFi'),
          ],
        },
      ],
    },
    'connection-fails': {
      name: t('wiFiTroubleshootingGuide.wifiAsksForPasswordOrConnectionFails', 'WiFi Asks for Password or Connection Fails'),
      steps: [
        {
          id: 'connection-fails-get-password',
          title: t('wiFiTroubleshootingGuide.stepGetTheCorrectPassword'),
          content: t('wiFiTroubleshootingGuide.stepGetTheCorrectPasswordContent', `Our library WiFi might require a password. Here's how to get it:

Getting the Password:
• Ask any library staff member at the desk
• Password is usually posted at the front desk on a sign
• It may be on your library card receipt
• Staff can also provide it by phone

Common Password Hints:
• Usually includes the library name
• May have numbers
• Case-sensitive (UPPERCASE different from lowercase)
• No spaces typically

Try these solutions:
• Visit the front desk and ask for WiFi password
• Call the library and ask (staff will provide it)
• Check your library card receipt if you got one today`),
          tips: [
            t('wiFiTroubleshootingGuide.stepGetTheCorrectPasswordTip1', "Write down the password - you'll need it to reconnect"),
            t('wiFiTroubleshootingGuide.stepGetTheCorrectPasswordTip2', 'Different networks might have different passwords'),
          ],
          hasCheckpoint: true,
        },
        {
          id: 'connection-fails-enter-password',
          title: t('wiFiTroubleshootingGuide.stepEnterPasswordCorrectly'),
          content: t('wiFiTroubleshootingGuide.stepEnterPasswordCorrectlyContent', `When connecting, carefully enter the password:

iPhone/iPad:
• Select the WiFi network
• Tap "Connect"
• When asked for password, type it exactly
• Check CAPS LOCK - often the problem!
• Tap "Connect"

Android:
• Select the WiFi network
• Tap "Connect"
• Enter password in the "Password" field
• Check that CAPS LOCK is OFF
• Tap "Connect"

Windows/Laptop:
• Right-click WiFi icon → Select network
• Click "Connect" on your network
• Enter password exactly as written
• Check for CAPS LOCK
• Click "OK"

Try these solutions:
• Copy/paste the password if possible to avoid typos
• Clear the field and re-enter it slowly
• Check if CAPS LOCK key is on - turn it OFF
• Make sure you're on "LSC_Public" or the right network`),
          tips: [
            t('wiFiTroubleshootingGuide.stepEnterPasswordCorrectlyTip1', "One wrong character and it won't connect"),
            t('wiFiTroubleshootingGuide.stepEnterPasswordCorrectlyTip2', 'If unsure about capitals, ask staff to write it down'),
          ],
        },
        {
          id: 'connection-fails-forget-reconnect',
          title: t('wiFiTroubleshootingGuide.stepForgetAndReconnect', 'Step 3: "Forget" and Reconnect'),
          content: t('wiFiTroubleshootingGuide.stepForgetAndReconnectContent', `Sometimes your device "remembers" an incorrect password. Forget the network and try again:

iPhone/iPad:
• Go to Settings → WiFi
• Find "LSC_Public" (or your network)
• Tap the info button (a small letter i in a circle)
• Tap "Forget This Network"
• Then reconnect and enter password fresh

Android:
• Go to Settings → WiFi
• Long-press the network name
• Tap "Forget" or "Remove"
• Reconnect and enter password again

Windows:
• Right-click WiFi icon → Open Network settings
• Find "Manage known networks"
• Find your network and click "Forget"
• Reconnect and re-enter password`),
          troubleshooting: t('wiFiTroubleshootingGuide.stepForgetAndReconnectTroubleshooting', `Forgetting clears the "memory" of wrong passwords. Restart your device after forgetting and reconnecting. You can also try a different WiFi network as a test. Your device saves passwords - sometimes the old one is stuck. Forgetting fixes 60% of connection problems.`),
        },
      ],
    },
    'keeps-disconnecting': {
      name: t('wiFiTroubleshootingGuide.wifiKeepsDisconnecting', 'WiFi Keeps Disconnecting'),
      steps: [
        {
          id: 'disconnecting-check-distance',
          title: t('wiFiTroubleshootingGuide.stepCheckYourDistanceFrom'),
          content: t('wiFiTroubleshootingGuide.stepCheckYourDistanceFromContent', `WiFi strength weakens with distance. Your device might be too far away:

Signs You're Too Far:
• WiFi shows only 1-2 bars
• Other devices stay connected when you move
• Connection drops in certain parts of the library

What to do:
• Move closer to the library center
• Ask staff where the nearest access point is
• Try sitting in a different area
• Move away from walls and doors

Try these solutions:
• Relocate to a different area of the library
• Move closer to windows or public areas
• Move at least 10-15 feet away from outer walls`),
          tips: [
            t('wiFiTroubleshootingGuide.stepCheckYourDistanceFromTip1', 'WiFi range is usually 30-50 feet in open areas'),
            t('wiFiTroubleshootingGuide.stepCheckYourDistanceFromTip2', 'Walls cut range in half or more'),
          ],
          hasCheckpoint: true,
        },
        {
          id: 'disconnecting-interference',
          title: t('wiFiTroubleshootingGuide.stepReduceWifiInterference'),
          content: t('wiFiTroubleshootingGuide.stepReduceWifiInterferenceContent', `Other wireless devices can interfere with WiFi:

Common Interference Sources:
• Microwave ovens (very strong interference!)
• Bluetooth devices very close by
• Cordless phones
• Baby monitors
• Radio stations
• Many devices on same WiFi network

What to do:
• Move away from the library kitchen area
• Turn off Bluetooth if you're not using it
• Move away from other people using WiFi heavily
• Suggest to staff if a microwave is near computers

Try these solutions:
• Disable Bluetooth when not needed
• Move to a different room away from kitchen
• Ask staff if they can help identify interference
• Suggest that staff check WiFi channel settings (5GHz vs 2.4GHz)`),
          tips: [
            t('wiFiTroubleshootingGuide.stepReduceWifiInterferenceTip1', 'Microwaves are notorious for WiFi interference'),
            t('wiFiTroubleshootingGuide.stepReduceWifiInterferenceTip2', 'Bluetooth headphones/mice can interfere if too close'),
          ],
        },
        {
          id: 'disconnecting-update-device',
          title: t('wiFiTroubleshootingGuide.stepUpdateYourDevice'),
          content: t('wiFiTroubleshootingGuide.stepUpdateYourDeviceContent', `Outdated software can cause WiFi problems:

Check for Updates:

iPhone/iPad:
• Go to Settings → General → Software Update
• If an update is available, tap "Download and Install"
• Keep device plugged in during update

Android:
• Go to Settings → System → System Update
• Tap "Check for updates"
• If available, tap "Download and install"

Windows/Laptop:
• Click Start → Settings → Update & Security
• Click "Check for updates"
• Install any available updates

Try these solutions:
• Install the latest software updates
• Restart your device after updating
• Once updated, "forget" and reconnect to WiFi`),
          tips: [
            t('wiFiTroubleshootingGuide.stepUpdateYourDeviceTip1', 'Updates often fix WiFi stability problems'),
            t('wiFiTroubleshootingGuide.stepUpdateYourDeviceTip2', 'Set updates to automatic if possible'),
          ],
        },
        {
          id: 'disconnecting-reset-network',
          title: t('wiFiTroubleshootingGuide.stepResetNetworkSettingsLast'),
          content: t('wiFiTroubleshootingGuide.stepResetNetworkSettingsLastContent', `If nothing else works, reset your WiFi settings:

iPhone/iPad:
• Go to Settings → General → Reset
• Tap "Reset Network Settings"
• Your device will restart
• Reconnect to WiFi (you'll need the password)

Android:
• Go to Settings → System → Reset
• Tap "Reset WiFi, mobile & Bluetooth"
• Confirm when asked
• Reconnect to WiFi

Windows:
• Right-click WiFi icon → Open Network settings
• Scroll down to "Advanced network settings"
• Click "Network reset"
• Restart your device
• Reconnect to WiFi`),
          troubleshooting: t('wiFiTroubleshootingGuide.stepResetNetworkSettingsLastTroubleshooting', `This removes all saved WiFi networks and resets settings. You'll need to re-enter passwords for all networks. Only do this if other steps don't work - you'll need all your WiFi passwords handy after doing this.`),
          tips: [
            t('wiFiTroubleshootingGuide.stepResetNetworkSettingsLastTip1', "Only do this if other steps don't work"),
            t('wiFiTroubleshootingGuide.stepResetNetworkSettingsLastTip2', "You'll need all your WiFi passwords handy after doing this"),
          ],
        },
      ],
    },
    'slow-speed': {
      name: t('wiFiTroubleshootingGuide.wifiIsVerySlow', 'WiFi is Very Slow'),
      steps: [
        {
          id: 'slow-speed-check',
          title: t('wiFiTroubleshootingGuide.stepCheckYourConnectionSpeed'),
          content: t('wiFiTroubleshootingGuide.stepCheckYourConnectionSpeedContent', `First, confirm the WiFi is actually slow:

Quick Speed Test (requires already connected):
• Open your browser on the library computers
• Visit: speedtest.net
• Click "GO"
• Wait for results

What's "normal" library WiFi:
• Download: 5-25 Mbps (reasonable for library)
• Upload: 1-5 Mbps
• Below 5 Mbps = slow

If slow:
• Note the speed number
• Tell library staff (helps them troubleshoot)
• May indicate a network issue, not your device

Try these solutions:
• Check peak vs. off-peak times (mornings usually faster)
• Report speeds below 2 Mbps to staff
• Use library computers for critical tasks`),
          tips: [
            t('wiFiTroubleshootingGuide.stepCheckYourConnectionSpeedTip1', 'Speed varies based on how many people are online'),
            t('wiFiTroubleshootingGuide.stepCheckYourConnectionSpeedTip2', 'Video streaming needs at least 2-3 Mbps'),
          ],
          hasCheckpoint: true,
        },
        {
          id: 'slow-speed-close-apps',
          title: t('wiFiTroubleshootingGuide.stepCheckWhatYoureRunning', "Step 2: Check What You're Running"),
          content: t('wiFiTroubleshootingGuide.stepCheckWhatYoureRunningContent', `Other apps using WiFi can slow everything down:

Close Unnecessary Apps:

iPhone/iPad:
• Look for apps using WiFi in the background
• Swipe up from bottom to close apps
• Especially: Video apps, cloud sync, social media

Android:
• Open Settings → Apps
• Check which apps use WiFi background data
• Go back and force-close heavy apps

Windows/Laptop:
• Look at taskbar for heavy apps
• Close web browsers with many tabs
• Pause cloud backup (OneDrive, Google Drive, iCloud)
• Close video/streaming apps

Try these solutions:
• Close web browser tabs you're not using
• Pause cloud backup during your visit
• Turn off video autoplay in social media
• Close background apps`),
          tips: [
            t('wiFiTroubleshootingGuide.stepCheckWhatYoureRunningTip1', 'One streaming video uses as much bandwidth as 50 people browsing'),
            t('wiFiTroubleshootingGuide.stepCheckWhatYoureRunningTip2', 'Cloud sync (OneDrive, iCloud) runs in background'),
          ],
        },
        {
          id: 'slow-speed-move-closer',
          title: t('wiFiTroubleshootingGuide.stepMoveCloserOrSwitch'),
          content: t('wiFiTroubleshootingGuide.stepMoveCloserOrSwitchContent', `WiFi strength affects speed:

If Connection is Weak:
• Move closer to the library center
• Find an area with 4-5 WiFi bars showing
• Move away from walls
• Try a different area entirely

Check Network Quality:

iPhone/iPad:
• Settings → WiFi
• Look at the number of bars next to the network name
• 4-5 bars = good speed
• 1-2 bars = slow

Android:
• Settings → WiFi
• Same - more bars = faster

Strength matters:
• At 1-2 bars: expect slow speeds
• At 4-5 bars: should be much faster

Try these solutions:
• Relocate to a stronger signal area
• Ask staff for the best spot to sit
• Try again during less busy hours`),
          tips: [
            t('wiFiTroubleshootingGuide.stepMoveCloserOrSwitchTip1', "Just because you're connected doesn't mean you have good signal"),
            t('wiFiTroubleshootingGuide.stepMoveCloserOrSwitchTip2', 'Moving 10 feet can make a huge difference'),
          ],
        },
        {
          id: 'slow-speed-ask-help',
          title: t('wiFiTroubleshootingGuide.stepWhenToAskFor'),
          content: t('wiFiTroubleshootingGuide.stepWhenToAskForContent', `If speed is still poor after these steps:

Tell staff:
• "I'm getting 2-3 Mbps on the WiFi"
• Or "My WiFi keeps dropping when I move around"
• Or "WiFi works but videos won't play"

What staff can check:
• Network load (how many people are online)
• WiFi channel interference
• Your device's compatibility
• Whether it's a device problem or network problem

Next steps might be:
• Use a library computer instead
• Come back during quieter hours
• Get help with specific tasks`),
          troubleshooting: t('wiFiTroubleshootingGuide.stepWhenToAskForTroubleshooting', `Staff can identify if it's a device or network issue. They may suggest using library computers instead. They can also escalate to IT if the network is actually down. Describing the problem clearly helps staff solve it faster. Speed varies throughout the day - early morning is usually fastest.`),
          tips: [
            t('wiFiTroubleshootingGuide.stepWhenToAskForTip1', 'Describing the problem clearly helps staff solve it faster'),
            t('wiFiTroubleshootingGuide.stepWhenToAskForTip2', 'Speed varies throughout the day - early morning usually fastest'),
          ],
        },
      ],
    },
  }
}

export default function WiFiTroubleshootingGuide(): React.ReactElement {
  const { t } = useTranslation()
  const [selectedPath, setSelectedPath] = useState<TroubleshootingPath>(null)

  const troubleshootingPaths = useMemo(() => buildPaths(t), [t])

  if (selectedPath) {
    const path = troubleshootingPaths[selectedPath]
    return (
      <GuidedWalkthrough
        guideId={`wifi-troubleshooting-${selectedPath}`}
        title={path.name}
        description={t('wiFiTroubleshootingGuide.description', 'Step-by-step WiFi troubleshooting')}
        steps={path.steps}
        onComplete={() => setSelectedPath(null)}
      />
    )
  }

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark">
      <PageContainer width="read" className="py-8">
        {/* Header */}
        <button
          onClick={() => window.history.back()}
          className="flex items-center gap-2 text-lsc-rose dark:text-lsc-rose-light hover:underline mb-6"
        >
          <ChevronLeft className="w-4 h-4" />
          {t('wiFiTroubleshootingGuide.backButton', 'Back')}
        </button>

        <div className="mb-8">
          <div className="flex items-center gap-4 mb-4">
            <div className="p-3 bg-lsc-cream dark:bg-earth-800/30 rounded-xl">
              <Wifi className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <div>
              <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-earth-50">
                {t('wiFiTroubleshootingGuide.pageHeading', 'WiFi Troubleshooting')}
              </h1>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                {t('wiFiTroubleshootingGuide.pageSubtitle', "Can't connect or connection keeps dropping? Start here.")}
              </p>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2 text-sm">
                {t('wiFiTroubleshootingGuide.beforeYouStartChecklist', `Before you start, make sure:
• Your device is charged and turned on
• You are inside or near the library building
• You know your device type (phone, tablet, laptop)`)}
              </p>
            </div>
          </div>
        </div>

        {/* Problem Selection */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700 mb-8">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50 mb-6">
            {t('wiFiTroubleshootingGuide.whatsYourWifiProblem', "What's your WiFi problem?")}
          </h2>

          <div className="space-y-3">
            {[
              { key: 'no-network' as const, icon: <WifiOff aria-hidden="true" className="w-6 h-6 text-lsc-rose" />, label: t('wiFiTroubleshootingGuide.optionCantSeeWifiNetworkAtAll', "I can't see the WiFi network at all") },
              { key: 'connection-fails' as const, icon: <Lock aria-hidden="true" className="w-6 h-6 text-lsc-rose" />, label: t('wiFiTroubleshootingGuide.optionWifiAsksForPasswordOrWontConnect', "WiFi asks for password or won't connect") },
              { key: 'keeps-disconnecting' as const, icon: <Signal aria-hidden="true" className="w-6 h-6 text-lsc-rose" />, label: t('wiFiTroubleshootingGuide.wifiKeepsDisconnectingOrDropping') },
              { key: 'slow-speed' as const, icon: <Gauge aria-hidden="true" className="w-6 h-6 text-lsc-rose" />, label: t('wiFiTroubleshootingGuide.wifiIsConnectedButVery') },
            ].map((problem) => (
              <button
                key={problem.key}
                onClick={() => setSelectedPath(problem.key)}
                className="w-full text-left p-4 rounded-xl border-2 border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-earth-700/50 motion-safe:transition-all group"
              >
                <div className="flex items-center gap-3">
                  {problem.icon}
                  <div>
                    <p className="font-medium text-lsc-dark dark:text-earth-50 group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light">
                      {problem.label}
                    </p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Quick Tips */}
        <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-800/50 rounded-xl p-6">
          <h3 className="font-serif font-semibold text-earth-900 dark:text-earth-200 mb-3 flex items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            {t('wiFiTroubleshootingGuide.quickFixesToTryFirst', 'Quick Fixes to Try First')}
          </h3>
          <ul className="space-y-2 text-sm text-earth-800 dark:text-lsc-rose-light/80">
            <li>✓ {t('wiFiTroubleshootingGuide.quickFixTip1', 'Turn WiFi OFF and back ON (wait 10 seconds)')}</li>
            <li>✓ {t('wiFiTroubleshootingGuide.quickFixTip2', 'Restart your device completely')}</li>
            <li>✓ {t('wiFiTroubleshootingGuide.quickFixTip3', "Move closer to the library's main area")}</li>
            <li>✓ {t('wiFiTroubleshootingGuide.quickFixTip4', 'Ask staff for the WiFi network name and password')}</li>
            <li>✓ {t('wiFiTroubleshootingGuide.quickFixTip5', 'Check if airplane mode is turned OFF')}</li>
          </ul>
        </div>
      </PageContainer>
    </div>
  )
}
