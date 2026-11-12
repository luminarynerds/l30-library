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
    title: t('emailAccountGuide.creatingYourEmailAccount'),
    content: t('emailAccountGuide.introContent', `An email account allows you to send and receive messages online. This guide will help you create a free email address using Gmail, which is one of the most popular email services.

Before you start, you will need:
• A device with internet access
• A phone number (for account verification)
• About 10 minutes

By the end of this guide, you'll have:
✓ Your own email address
✓ Knowledge of how to send and receive emails
✓ Ability to use email for library communications`),
    tips: [
      t('emailAccountGuide.introTip1', 'Email is completely free with Gmail'),
      t('emailAccountGuide.introTip2', 'You can use email on any device with internet'),
      t('emailAccountGuide.introTip3', 'Keep your password safe and secret'),
    ],
  },
  {
    id: 'choose-service',
    title: t('emailAccountGuide.stepChooseYourEmailService'),
    content: t('emailAccountGuide.chooseServiceContent', `There are several free email options available. We recommend:

Gmail (Google):
• Very popular and easy to use
• Excellent spam protection
• Works on all devices
• Visit: gmail.com

Outlook (Microsoft):
• Good alternative to Gmail
• Integrates with Microsoft Office
• Works on all devices
• Visit: outlook.com

Yahoo Mail:
• Another popular option
• Easy recovery options
• Works on all devices
• Visit: mail.yahoo.com

For this guide, we'll use Gmail. You can always create multiple accounts!`),
    tips: [
      t('emailAccountGuide.chooseServiceTip1', 'Gmail is widely used and recommended for beginners'),
      t('emailAccountGuide.chooseServiceTip2', 'You can switch between services later if you want'),
      t('emailAccountGuide.chooseServiceTip3', 'The steps are similar for most email providers'),
    ],
  },
  {
    id: 'open-gmail',
    title: t('emailAccountGuide.stepOpenGmail', 'Step 2: Open Gmail'),
    content: t('emailAccountGuide.openGmailContent', `Now let's go to Gmail:

1. Open your web browser (Chrome, Firefox, Safari, or Edge)
2. In the address bar, type: gmail.com
3. Press Enter on your keyboard
4. You should see the Gmail sign-up page
5. Look for the link that says "Create account" or "Sign up"
6. Click on it

The Gmail sign-up page will appear with a form asking for your information.`),
    tips: [
      t('emailAccountGuide.openGmailTip1', "Make sure you're on the official Gmail website (gmail.com)"),
      t('emailAccountGuide.openGmailTip2', 'If you already have a Google account, you can use it'),
      t('emailAccountGuide.openGmailTip3', "The page should look professional with Google's logo at the top"),
    ],
    troubleshooting: t('emailAccountGuide.openGmailTroubleshooting', `If the page won't load: 1) Check your internet connection, 2) Try a different browser, 3) Clear your browser cache and refresh`),
    hasCheckpoint: true,
  },
  {
    id: 'fill-form',
    title: t('emailAccountGuide.stepFillOutTheSign'),
    content: t('emailAccountGuide.fillFormContent', `The form will ask for these details. Take your time filling it out:

First Name:
• Enter your first name

Last Name:
• Enter your last name

Username (Your Email Address):
• Choose something simple like: john.smith or jsmith123
• Gmail will add "@gmail.com" automatically
• If your choice is taken, Gmail suggests alternatives
• Avoid using special characters or spaces

Password:
• Create a strong password with:
  - At least 8 characters
  - Mix of uppercase and lowercase letters
  - At least one number
  - At least one special character (!@#$%^&*)
• Example: PurpleFrog-Reads-Books42

Confirm Password:
• Type your password again exactly as you entered it`),
    tips: [
      t('emailAccountGuide.fillFormTip1', "Choose a username you'll remember easily"),
      t('emailAccountGuide.fillFormTip2', "Don't include personal information like your birthday or address"),
      t('emailAccountGuide.fillFormTip3', 'Write down your password somewhere safe at first (not on a sticky note)'),
      t('emailAccountGuide.fillFormTip4', "Make passwords unique - don't use the same one for other accounts"),
    ],
    troubleshooting: t('emailAccountGuide.fillFormTroubleshooting', `If your username is taken: Gmail suggests alternatives - choose one that looks good to you. If the password is too weak, add more numbers or special characters.`),
  },
  {
    id: 'personal-info',
    title: t('emailAccountGuide.stepEnterPersonalInformation'),
    content: t('emailAccountGuide.personalInfoContent', `Next, Gmail asks for more details:

Phone Number (Optional but recommended):
• Enter your phone number for account recovery
• This helps you regain access if you forget your password
• Gmail will send you a verification code via text message
• You'll enter the code to confirm

Recovery Email (Optional):
• You can add another email address you already have
• This also helps with account recovery

Birth Date:
• Choose your birth month, day, and year
• Used for account security and age verification

Gender:
• Select your gender from the options provided

After filling these in, click "Next" or "Continue"`),
    tips: [
      t('emailAccountGuide.personalInfoTip1', 'Adding a phone number makes your account more secure'),
      t('emailAccountGuide.personalInfoTip2', 'Recovery email is helpful if you forget your password'),
      t('emailAccountGuide.personalInfoTip3', "You're not required to provide all information, but it's recommended"),
    ],
    hasCheckpoint: true,
  },
  {
    id: 'terms-privacy',
    title: t('emailAccountGuide.stepReviewTermsAndPrivacy'),
    content: t('emailAccountGuide.termsPrivacyContent', `Google will show you their terms of service and privacy policy:

You'll see:
• Google's Terms of Service
• Privacy policy information
• A checkbox to accept the terms

What you need to do:
1. Review the information (it's okay to skip reading the full text at first)
2. Check the box that says "I agree to the Terms of Service and Privacy Policy"
3. Click the "Create Account" button

Don't worry - these are standard agreements that every free email service uses. They explain how Google protects your information.`),
    tips: [
      t('emailAccountGuide.termsPrivacyTip1', "You're agreeing to Google's standard terms"),
      t('emailAccountGuide.termsPrivacyTip2', 'Your email address and settings are private'),
      t('emailAccountGuide.termsPrivacyTip3', 'You can change privacy settings anytime after creating the account'),
    ],
  },
  {
    id: 'verify-account',
    title: t('emailAccountGuide.stepVerifyYourAccount'),
    content: t('emailAccountGuide.verifyAccountContent', `Google sends a verification code to confirm you're real:

If you provided a phone number:
1. Google will send you a text message with a verification code
2. Enter the code in the field shown
3. Click "Verify"

If you provided a recovery email:
1. Check that email for a message from Google
2. Click the verification link in the email
3. Or enter the code from the email

This step takes just a few minutes. Once verified, you'll have your own email account!`),
    tips: [
      t('emailAccountGuide.verifyAccountTip1', 'Check your text messages or email quickly - codes expire in a few minutes'),
      t('emailAccountGuide.verifyAccountTip2', 'If you didn\'t get a code, click "Send code again"'),
      t('emailAccountGuide.verifyAccountTip3', 'You might need to check your spam folder for the email'),
    ],
    troubleshooting: t('emailAccountGuide.verifyAccountTroubleshooting', `If you didn't get a code: 1) Click "Resend code", 2) Check your spam folder, 3) Make sure your phone number or email is correct`),
  },
  {
    id: 'first-look',
    title: t('emailAccountGuide.stepYourNewInbox'),
    content: t('emailAccountGuide.newInboxContent', `Your email account is ready.

You'll see:
• A welcome message from Google
• Your inbox (where incoming emails appear)
• Folders on the left (Starred, Important, Drafts, etc.)
• A compose button to write new emails

Your email address is now:
[your-username]@gmail.com

Take a moment to explore:
1. Click "Compose" to see how to write an email
2. Look at the folders on the left side
3. Check out the settings (gear icon)`),
    tips: [
      t('emailAccountGuide.newInboxTip1', 'Your Gmail is accessible from any device'),
      t('emailAccountGuide.newInboxTip2', 'You can check email on your computer, phone, or tablet'),
      t('emailAccountGuide.newInboxTip3', 'Gmail automatically saves your emails'),
    ],
  },
  {
    id: 'send-email',
    title: t('emailAccountGuide.stepSendYourFirstEmail'),
    content: t('emailAccountGuide.sendFirstEmailContent', `Let's send a test email to make sure everything works:

1. Click the "Compose" button (usually in the top left)
2. A new message window opens

To: [someone's email address]
• Enter an email address of someone you know
• Or you can send it to yourself to test
• Your own email: [your-username]@gmail.com

Subject:
• Type a short title for your email
• Example: "Test Email" or "Hello from my new email!"

Message:
• Click in the body area and type your message
• Say something like: "This is my first email!"

Sending:
1. Look for a "Send" button (usually at the bottom)
2. Click "Send"
3. You'll see a confirmation message

That's it! Your email has been sent.`),
    tips: [
      t('emailAccountGuide.sendFirstEmailTip1', 'Always double-check the recipient email address'),
      t('emailAccountGuide.sendFirstEmailTip2', 'Emails arrive within seconds (or minutes on slower connections)'),
      t('emailAccountGuide.sendFirstEmailTip3', 'You can add attachments (photos, documents) before sending'),
    ],
    hasCheckpoint: true,
  },
  {
    id: 'security',
    title: t('emailAccountGuide.stepKeepYourEmailSafe'),
    content: t('emailAccountGuide.keepEmailSafeContent', `Now that you have an email account, protect it:

Strong Password Reminder:
• Never use your birth date or name
• Don't share your password with anyone
• Use different passwords for different accounts
• If someone asks for your password, it's a scam

Security Tips:
1. Log out when done, especially on shared computers
2. Never click suspicious links in emails
3. Be careful with attachments from people you don't know
4. Enable 2-Factor Authentication (extra security layer)

Setting Up 2-Factor Authentication:
1. Go to Google Account (myaccount.google.com)
2. Click "Security" on the left
3. Under "How you sign in," enable "2-Step Verification"
4. Follow the prompts to confirm with your phone

This makes your account much safer!`),
    tips: [
      t('emailAccountGuide.keepEmailSafeTip1', 'Library staff can help you set up 2-Factor Authentication'),
      t('emailAccountGuide.keepEmailSafeTip2', 'It only takes a few extra seconds when you log in'),
      t('emailAccountGuide.keepEmailSafeTip3', 'This is worth doing immediately'),
    ],
  },
  {
    id: 'next-steps',
    title: t('emailAccountGuide.nextStepsAndResources'),
    content: t('emailAccountGuide.nextStepsContent', `You now have an email account! Here's what you can do next:

Access Your Email:
• Computer: Gmail.com (bookmark it!)
• Phone: Download the Gmail app from your app store
• Works offline on phones

Using Email for:
• Contacting the library
• Signing up for services online
• Staying in touch with friends and family
• Receiving confirmations and receipts

Getting Help:
• Contact us at the library tech desk
• Ask staff to help with any questions
• Take our "Email Essentials" class (details at tech desk)
• Visit our tech support page for more guides

You're all set! Your new email address is ready to use.`),
    tips: [
      t('emailAccountGuide.nextStepsTip1', 'The library offers free email classes for beginners'),
      t('emailAccountGuide.nextStepsTip2', 'You can always change your recovery options later'),
      t('emailAccountGuide.nextStepsTip3', 'Gmail is secure and reliable'),
    ],
  },
]

export default function EmailAccountGuide(): React.ReactElement {
  const { t } = useTranslation()
  const steps = useMemo(() => _buildSteps(t), [t])
  return (
    <GuidedWalkthrough
      guideId="email-setup"
      title={t('emailAccountGuide.creatingAnEmailAccount')}
      description={t('emailAccountGuide.pageDescription', 'Learn how to create your own free email address with Gmail')}
      steps={steps}
      onComplete={() => {
      }}
    />
  )
}
