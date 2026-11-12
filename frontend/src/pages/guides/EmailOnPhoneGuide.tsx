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
    title: t('emailOnPhoneGuide.checkYourEmailOnYour'),
    content: t('emailOnPhoneGuide.introContent', `Want to check your email anywhere? This guide shows you how to set up Gmail, Outlook, or Yahoo Mail on your phone.

You'll learn:
✓ Download the email app
✓ Add your email account
✓ Check and send email from your phone
✓ Fix common problems`),
    tips: [
      t('emailOnPhoneGuide.introTip1', 'You can check multiple email accounts on one phone'),
      t('emailOnPhoneGuide.introTip2', 'Works on iPhone, Android, and most devices'),
      t('emailOnPhoneGuide.introTip3', 'Takes about 5-10 minutes to set up'),
    ],
  },
  {
    id: 'before-start',
    title: t('emailOnPhoneGuide.beforeYouStart', 'Before You Start'),
    content: t('emailOnPhoneGuide.beforeStartContent', `Make sure you have:

✓ Your email address
✓ Your email password (the one you log in with)
✓ Your phone charged
✓ WiFi or internet connection
✓ Your phone unlocked

If you don't remember your password:
→ Follow the "Reset a Forgotten Password" guide first
→ Come back here when you have it`),
    tips: [
      t('emailOnPhoneGuide.beforeStartTip1', 'You need the correct password - if unsure, reset it first'),
      t('emailOnPhoneGuide.beforeStartTip2', 'Internet required to download apps'),
      t('emailOnPhoneGuide.beforeStartTip3', 'Library WiFi works great for this'),
    ],
  },
  {
    id: 'download-app-iphone',
    title: t('emailOnPhoneGuide.stepDownloadEmailAppIphone'),
    content: t('emailOnPhoneGuide.downloadIphoneContent', `iPhone comes with Mail app built-in, but you can also use Gmail or Outlook apps:

Using Built-in Mail App:
1. Tap "Settings" on your home screen
2. Scroll down and tap "Mail"
3. Tap "Accounts"
4. Tap "Add Account"
5. Follow steps in next section

Or Download Email Apps:

Gmail App:
1. Open "App Store" (white icon with blue bag)
2. Tap "Search" at bottom
3. Search: "Gmail"
4. Tap blue "GET" button
5. Use Face ID or Apple ID to confirm
6. Tap "open" when done

Outlook App:
1. Open "App Store"
2. Tap "Search" at bottom
3. Search: "Outlook"
4. Tap blue "GET"
5. Confirm with Face ID or Apple ID
6. Tap "open"

Yahoo Mail App:
1. Open "App Store"
2. Search: "Yahoo Mail"
3. Tap "GET"
4. Confirm and wait for download`),
    tips: [
      t('emailOnPhoneGuide.downloadIphoneTip1', 'All apps are free'),
      t('emailOnPhoneGuide.downloadIphoneTip2', 'Gmail or Outlook apps are easiest for beginners'),
      t('emailOnPhoneGuide.downloadIphoneTip3', 'Apple ID needed to download - use yours or ask staff'),
    ],
    hasCheckpoint: true,
  },
  {
    id: 'download-app-android',
    title: t('emailOnPhoneGuide.stepDownloadEmailAppAndroid'),
    content: t('emailOnPhoneGuide.downloadAndroidContent', `Android phones can use Gmail, Outlook, or Yahoo Mail apps:

Gmail App (Easiest for Gmail accounts):
1. Open "Play Store" (white triangle icon)
2. Tap "Search" (magnifying glass)
3. Type: "Gmail"
4. Tap the official Gmail app
5. Tap blue "Install" button
6. Wait for it to download
7. Tap "Open"

Outlook App (Good for any email):
1. Open "Play Store"
2. Tap "Search"
3. Type: "Outlook"
4. Find "Microsoft Outlook"
5. Tap "Install"
6. Wait and tap "Open"

Yahoo Mail App:
1. Open "Play Store"
2. Search: "Yahoo Mail"
3. Tap "Install"
4. Wait for download
5. Tap "Open"

Note:
• Most Android phones already have Gmail built-in
• You might already have an email app - check your apps`),
    tips: [
      t('emailOnPhoneGuide.downloadAndroidTip1', 'All apps are completely free'),
      t('emailOnPhoneGuide.downloadAndroidTip2', 'Gmail app is easiest for most people'),
      t('emailOnPhoneGuide.downloadAndroidTip3', 'You may need Google account to install apps'),
    ],
    hasCheckpoint: true,
  },
  {
    id: 'add-gmail-iphone',
    title: t('emailOnPhoneGuide.stepAddGmailAccountIphone'),
    content: t('emailOnPhoneGuide.addGmailIphoneContent', `Now let's add your Gmail to your phone:

Option A: Using Gmail App
1. Open the Gmail app you downloaded
2. Tap your profile picture (top right)
3. Tap "Add another account"
4. Select "Google"
5. Type your Gmail address
6. Tap "Next"
7. Type your Gmail password
8. Tap "Next"
9. You might see security screens - follow them
10. Tap "Allow" if asked for permissions
11. Done! Your Gmail is now on your phone

Option B: Using iPhone Mail App
1. Go to Settings → Mail
2. Tap "Accounts" → "Add Account"
3. Tap "Google"
4. Type your Gmail address
5. Tap "Next"
6. Type your password
7. Tap "Next"
8. Allow permissions
9. Tap "Save"

Both methods work!`),
    tips: [
      t('emailOnPhoneGuide.addGmailIphoneTip1', 'Use Gmail app if you mostly use Gmail'),
      t('emailOnPhoneGuide.addGmailIphoneTip2', 'Use Mail app if you have multiple email accounts'),
      t('emailOnPhoneGuide.addGmailIphoneTip3', 'Your password is secure - sent directly to Google'),
      t('emailOnPhoneGuide.addGmailIphoneTip4', "Don't share your password with anyone"),
    ],
    hasCheckpoint: true,
  },
  {
    id: 'add-gmail-android',
    title: t('emailOnPhoneGuide.stepAddGmailAccountAndroid'),
    content: t('emailOnPhoneGuide.addGmailAndroidContent', `Adding Gmail on Android:

Option A: Using Gmail App
1. Open the Gmail app
2. Tap your profile picture (top right)
3. Tap "Add another account"
4. Select "Google"
5. Type your Gmail address
6. Tap "Next"
7. Type your Gmail password
8. Tap "Next"
9. Follow any security screens
10. Allow permissions
11. Your Gmail is added!

Option B: Using Android Settings
1. Go to "Settings"
2. Find "Accounts" or "Accounts & sync"
3. Tap "Add account"
4. Select "Google"
5. Type your Gmail address
6. Tap "Next"
7. Enter your password
8. Tap "Next"
9. Allow permissions
10. Done!

Note:
• If you created a Google account when setting up your phone, you already have Gmail set up!
• You can add multiple Gmail accounts`),
    tips: [
      t('emailOnPhoneGuide.addGmailAndroidTip1', 'Gmail app is easiest for Gmail accounts'),
      t('emailOnPhoneGuide.addGmailAndroidTip2', 'Your Android phone may already have Gmail configured'),
      t('emailOnPhoneGuide.addGmailAndroidTip3', 'Password is encrypted and secure'),
    ],
    hasCheckpoint: true,
  },
  {
    id: 'add-outlook-phone',
    title: t('emailOnPhoneGuide.stepAddOutlookEmailIphone'),
    content: t('emailOnPhoneGuide.addOutlookContent', `For Outlook.com or other email accounts using Outlook app:

iPhone:
1. Open the Outlook app
2. Tap "Settings" (gear icon, usually bottom right)
3. Tap "Add Account"
4. Enter your email address
5. Tap "Continue"
6. Enter your password
7. Tap "Sign In"
8. Allow permissions
9. Your account is added!

Android:
1. Open the Outlook app
2. Tap the menu (three lines, top left)
3. Tap "Settings"
4. Tap "Add Account"
5. Tap "Outlook.com"
6. Enter your email address
7. Tap "Next"
8. Enter your password
9. Tap "Sign In"
10. Allow permissions
11. Done!

For Yahoo or Other Email:
1. Open Outlook app
2. Go to Settings
3. Tap "Add Account"
4. Tap "Other Email Account"
5. Type your email address
6. Tap "Continue"
7. Enter your password
8. Outlook figures out the settings
9. Tap "Done"

The app handles everything!`),
    tips: [
      t('emailOnPhoneGuide.addOutlookTip1', 'Outlook app works with any email address'),
      t('emailOnPhoneGuide.addOutlookTip2', 'Yahoo Mail also works in Outlook app'),
      t('emailOnPhoneGuide.addOutlookTip3', 'Easier than setting up in Settings on some phones'),
    ],
    hasCheckpoint: true,
  },
  {
    id: 'first-use',
    title: t('emailOnPhoneGuide.stepYourFirstEmail'),
    content: t('emailOnPhoneGuide.firstUseContent', `Now that your email is set up, let's use it:

Checking Email:

iPhone:
1. Open Mail or Gmail app
2. You should see your emails
3. Tap any email to read it
4. New emails appear automatically

Android:
1. Open your email app
2. You'll see your inbox
3. Tap emails to read them
4. App refreshes automatically

Sending Email:

iPhone Mail:
1. Tap "Compose" (pencil icon, bottom right)
2. Tap "To:" and enter email address
3. Tap "Subject:" and write a subject
4. Write your message
5. Tap "Send" (top right)

iPhone Gmail:
1. Tap "Compose" (pencil, bottom right)
2. Enter recipient email
3. Add subject
4. Type message
5. Tap send arrow

Android Mail:
1. Tap "Compose" (usually pencil icon)
2. Enter "To" email
3. Add subject
4. Type your message
5. Tap "Send"

Android Gmail:
1. Tap "+" or "Compose"
2. Add recipient
3. Write subject
4. Type message
5. Tap send

Replying to Email:
1. Open the email
2. Look for "Reply" button
3. Type your message
4. Tap "Send"`),
    tips: [
      t('emailOnPhoneGuide.firstUseTip1', "Email updates automatically - you don't refresh manually"),
      t('emailOnPhoneGuide.firstUseTip2', 'You can draft emails and send later'),
      t('emailOnPhoneGuide.firstUseTip3', 'Your phone stores all your emails'),
      t('emailOnPhoneGuide.firstUseTip4', 'Check email anytime you have internet'),
    ],
    hasCheckpoint: true,
  },
  {
    id: 'notifications',
    title: t('emailOnPhoneGuide.stepGetNotifiedOfNew'),
    content: t('emailOnPhoneGuide.notificationsContent', `Want your phone to alert you when new emails arrive?

iPhone Mail:
1. Go to Settings → Notifications
2. Scroll down and find "Mail"
3. Tap it
4. Turn on "Allow Notifications"
5. Select notification style (banner, sound, etc.)
6. You'll now see alerts for new emails!

iPhone Gmail:
1. Open Gmail app
2. Tap your profile → Settings
3. Tap your email account
4. Scroll down to "Notifications"
5. Turn on notifications for your account
6. Choose alert style

Android Mail:
1. Open your email app
2. Tap menu → Settings
3. Find "Notifications"
4. Turn on notifications
5. Choose sound/vibration

Android Gmail:
1. Open Gmail
2. Tap menu (three lines)
3. Tap "Settings"
4. Tap your account
5. Tap "Notifications"
6. Turn on notifications

Turning Off Notifications:

If you get too many alerts:
• Reverse the steps above
• Turn OFF notifications
• You can always check manually

Customizing:

Different alerts for different:
• Senders
• Labels/folders
• Importance levels

Explore Settings to customize!`),
    tips: [
      t('emailOnPhoneGuide.notificationsTip1', 'Notifications help you stay on top of emails'),
      t('emailOnPhoneGuide.notificationsTip2', 'Can be overwhelming - adjust in settings'),
      t('emailOnPhoneGuide.notificationsTip3', 'You can turn on/off anytime'),
      t('emailOnPhoneGuide.notificationsTip4', 'VIP/Important emails can have special alerts'),
    ],
  },
  {
    id: 'multiple-accounts',
    title: t('emailOnPhoneGuide.managingMultipleAccounts', 'Managing Multiple Accounts'),
    content: t('emailOnPhoneGuide.multipleAccountsContent', `You can check more than one email account on the same phone:

iPhone:
• You can add multiple accounts
• Mail app shows all of them
• Tap account name to switch
• Some apps let you choose which to use

Android:
• Add as many accounts as you want
• Switch between them in the app
• Gmail app shows all at once

To add another account, follow the same steps you used to set up your first one.`),
    tips: [
      t('emailOnPhoneGuide.multipleAccountsTip1', 'Multiple accounts are very useful'),
      t('emailOnPhoneGuide.multipleAccountsTip2', 'Each account keeps its own inbox'),
    ],
  },
  {
    id: 'organizing-email',
    title: t('emailOnPhoneGuide.organizingYourEmail', 'Organizing Your Email'),
    content: t('emailOnPhoneGuide.organizingEmailContent', `Keep your inbox tidy with labels, folders, and search:

Labels (Gmail):
• Create folders for important emails
• Archive old emails
• Star important ones for quick access

Folders (Outlook):
• Create custom folders
• Move emails to organize
• Archive when done

Searching:

iPhone:
• Swipe down at top of inbox
• Type what you're looking for
• Find old emails quickly

Android:
• Tap search icon (magnifying glass)
• Type keywords
• Find emails by sender, subject, date

Backup:
• Your email is saved in the cloud
• Even if you lose your phone, your email is safe
• When you get a new phone, just add your account again
• All your emails will appear`),
    tips: [
      t('emailOnPhoneGuide.organizingEmailTip1', 'Create labels/folders to stay organized'),
      t('emailOnPhoneGuide.organizingEmailTip2', 'Search is powerful - use it to find old emails fast'),
    ],
  },
  {
    id: 'staying-secure',
    title: t('emailOnPhoneGuide.stayingSecure', 'Staying Secure'),
    content: t('emailOnPhoneGuide.stayingSecureContent', `A few safety habits to protect your email:

✓ Never reply to suspicious emails asking for passwords
✓ Don't open attachments from people you don't know
✓ If email asks to "confirm information" - it's probably a scam
✓ Never share your password
✓ Log out on shared devices

If You Get a Suspicious Email:
• Don't click any links
• Don't download any attachments
• Mark it as spam or junk
• Delete it
• If unsure, ask library staff`),
    tips: [
      t('emailOnPhoneGuide.stayingSecureTip1', 'Be cautious with suspicious emails'),
      t('emailOnPhoneGuide.stayingSecureTip2', 'When in doubt, do not click - ask someone first'),
    ],
  },
  {
    id: 'troubleshooting-login',
    title: t('emailOnPhoneGuide.fixingLoginProblems', 'Fixing Login Problems'),
    content: t('emailOnPhoneGuide.troubleshootingLoginContent', `If you can't log in or your app keeps crashing:

Password Wrong Error:

Even though you're sure it's correct:
1. You might have CAPS LOCK on
2. Password might have expired
3. Account might be locked for security
4. Try on a computer first to test password
5. Reset password if needed (see other guide)

App Keeps Crashing:

iPhone:
• Update app (App Store)
• Delete and reinstall app
• Restart phone
• Check storage isn't full

Android:
• Update app (Play Store)
• Delete and reinstall
• Restart phone
• Clear app cache (Settings → Apps)

Still Stuck?
• Ask library staff - we can help with this
• Come in and we'll set it up together
• Or call for phone support`),
    tips: [
      t('emailOnPhoneGuide.troubleshootingLoginTip1', 'Passwords expire sometimes - reset if needed'),
      t('emailOnPhoneGuide.troubleshootingLoginTip2', 'Restarting phone fixes most issues'),
      t('emailOnPhoneGuide.troubleshootingLoginTip3', 'Library staff can help in person'),
    ],
  },
  {
    id: 'troubleshooting-sync',
    title: t('emailOnPhoneGuide.fixingSyncAndNotification', 'Fixing Sync and Notification Issues'),
    content: t('emailOnPhoneGuide.troubleshootingSyncContent', `If emails won't load or you're not getting notifications:

Emails Won't Download:

iPhone/Android:
1. Check internet connection (WiFi or data)
2. Force-close the app (swipe away)
3. Open app again
4. Wait a few seconds for emails to load
5. If still not working, restart your phone

Stuck on "Loading":
1. Close the app completely
2. Wait 10 seconds
3. Open again
4. Try refreshing/pulling down
5. Check internet connection

Not Getting Notifications:
• Check notifications are ON in settings
• Check notifications aren't muted
• Restart phone
• Delete and reinstall app

Sending Emails Not Working:
1. Check internet is on
2. Tap "Send" again
3. Check email password is correct
4. Delete and reinstall app
5. Try on library computer to test`),
    tips: [
      t('emailOnPhoneGuide.troubleshootingSyncTip1', 'Internet connection is required for email'),
      t('emailOnPhoneGuide.troubleshootingSyncTip2', 'Restarting the phone fixes most sync issues'),
      t('emailOnPhoneGuide.troubleshootingSyncTip3', 'Library WiFi works great for troubleshooting'),
    ],
  },
  {
    id: 'complete',
    title: t('emailOnPhoneGuide.congratulations', 'Congratulations!'),
    content: t('emailOnPhoneGuide.completeContent', `You now have email on your phone!

What You Can Do:
✓ Check email anytime, anywhere
✓ Send emails from your phone
✓ Get notifications of new messages
✓ Organize multiple accounts
✓ Stay connected

Next Steps:
• Save important contacts
• Create labels/folders for organization
• Set up notifications the way you like
• Explore the app's features
• Ask staff about features you're curious about

Remember:
• Keep your password safe
• Don't open suspicious attachments
• Logout on shared devices
• Your email is always accessible
• Library staff can help anytime!

You're set up to use email on the go.`),
    tips: [
      t('emailOnPhoneGuide.completeTip1', 'Check your email regularly'),
      t('emailOnPhoneGuide.completeTip2', "Set up notifications so you don't miss messages"),
      t('emailOnPhoneGuide.completeTip3', 'Use labels/folders to stay organized'),
      t('emailOnPhoneGuide.completeTip4', 'Staff is here if you have questions'),
    ],
  },
]

export default function EmailOnPhoneGuide(): React.ReactElement {
  const { t } = useTranslation()
  const steps = useMemo(() => _buildSteps(t), [t])
  return (
    <GuidedWalkthrough
      guideId="email-on-phone"
      title={t('emailOnPhoneGuide.checkEmailOnYourPhone')}
      description={t('emailOnPhoneGuide.pageDescription', 'Set up Gmail, Outlook, or Yahoo Mail on iPhone or Android')}
      steps={steps}
      onComplete={() => {
      }}
    />
  )
}
