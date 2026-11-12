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
    title: t('passwordResetGuide.forgotYourPassword', 'Forgot Your Password?'),
    content: t('passwordResetGuide.introContent', `You can reset your password in a few minutes.

This guide covers:
✓ Resetting your email password (Gmail, Outlook, Yahoo)
✓ Resetting your library card PIN
✓ What to do if recovery options don't work`),
    tips: [
      t('passwordResetGuide.introTip1', "You'll need access to your email or phone number you used when creating the account"),
      t('passwordResetGuide.introTip2', 'Password resets usually take 5-10 minutes'),
      t('passwordResetGuide.introTip3', 'Your account is still secure during this process'),
    ],
  },
  {
    id: 'which-password',
    title: t('passwordResetGuide.whichPasswordDoYouNeed'),
    content: t('passwordResetGuide.whichPasswordContent', `There are different passwords for different accounts:

Email Password (Gmail, Outlook, Yahoo):
• This is what you use to log into your email
• Used when opening Gmail.com, Outlook.com, etc.
• If you forgot this, we help you reset it

Library Card PIN:
• 4-digit number you might use at the library
• Not your account password
• Different from your email password
• Ask staff at the desk if you forgot this

Social Media Passwords (Facebook, Instagram, etc.):
• Login to those websites directly
• Each has its own password reset system

Which one did you forget?`),
    tips: [
      t('passwordResetGuide.whichPasswordTip1', 'Most people need help with email passwords'),
      t('passwordResetGuide.whichPasswordTip2', 'Library card PINs are much shorter (just numbers)'),
      t('passwordResetGuide.whichPasswordTip3', 'Your password and PIN are completely separate'),
    ],
  },
  {
    id: 'gmail-start-reset',
    title: t('passwordResetGuide.resetGmailPasswordMostCommon'),
    content: t('passwordResetGuide.gmailStartResetContent', `Let's reset your Gmail password. First, start the process:

Step 1: Go to Gmail Login
1. Open your browser
2. Go to: gmail.com
3. You should see the login page
4. Look for "Can't access your account?" or "Forgot password?"

Step 2: Enter Your Email Address
1. When asked, type your full email address
2. Example: jane.smith@gmail.com
3. Click "Next"

Step 3: Enter Your Last Password
1. Gmail asks: "Enter the last password you remember"
2. If you remember ANY old password, enter it
3. If you can't remember any, click "Can't remember password"
4. Click "Next"`),
    tips: [
      t('passwordResetGuide.gmailStartResetTip1', 'Have your email address ready before starting'),
      t('passwordResetGuide.gmailStartResetTip2', 'Any old password you remember helps - even a guess'),
    ],
  },
  {
    id: 'gmail-verify-identity',
    title: t('passwordResetGuide.gmailVerifyIdentity', 'Gmail: Verify Your Identity'),
    content: t('passwordResetGuide.gmailVerifyIdentityContent', `Google will ask you to prove it's your account. You'll get ONE of these options:

A) Text Message (Best option!)
   • Select "Send code to your phone"
   • Enter your phone number
   • Get a text with a code
   • Type the code on the screen
   • Click "Verify"

B) Recovery Email
   • If you added a backup email when you created the account
   • Google sends a link to that email
   • Click the link in that email
   • You'll be able to reset your password

C) Security Questions
   • If you set security questions when creating account
   • Answer questions about yourself
   • Click "Next"

Use whichever option Google shows you. If one method doesn't work, click "Try another way" for more options.`),
    tips: [
      t('passwordResetGuide.gmailVerifyIdentityTip1', 'Using your phone number is fastest (text verification)'),
      t('passwordResetGuide.gmailVerifyIdentityTip2', 'Check your spam folder if you chose recovery email'),
      t('passwordResetGuide.gmailVerifyIdentityTip3', 'If nothing works, see the "Recovery Didn\'t Work" step later'),
    ],
    troubleshooting: t('passwordResetGuide.gmailVerifyIdentityTroubleshooting', `If you don't get a text or email: 1) Check your spam folder, 2) Try a different recovery method (phone vs email), 3) Ask library staff for help, 4) Try again tomorrow if accounts are locked`),
  },
  {
    id: 'gmail-new-password',
    title: t('passwordResetGuide.gmailCreateNewPassword', 'Gmail: Create Your New Password'),
    content: t('passwordResetGuide.gmailNewPasswordContent', `Once verified, Google shows a "Create new password" screen:

1. In the first box: Type a NEW password (not your old one!)
2. In the second box: Type the same password again
3. Your new password should have:
   - At least 8 letters
   - Mix of uppercase and lowercase
   - At least one number
   - At least one special character (!@#$%^&*)
   Example: MyNewPassword123!

4. Click "Change password"
5. You'll see "Password updated"
6. Your password is now reset!
7. You can now log in with your new password`),
    tips: [
      t('passwordResetGuide.gmailNewPasswordTip1', 'Save your new password somewhere safe'),
      t('passwordResetGuide.gmailNewPasswordTip2', 'You might need to log back into other apps with new password'),
      t('passwordResetGuide.gmailNewPasswordTip3', 'Write it down until you memorize it'),
    ],
    hasCheckpoint: true,
  },
  {
    id: 'email-password-outlook',
    title: t('passwordResetGuide.resetOutlookMicrosoftPassword'),
    content: t('passwordResetGuide.outlookContent', `For Outlook.com or Microsoft accounts:

Step 1: Go to Outlook
1. Visit: outlook.com
2. You should see "Sign in"
3. Look for "Can't access your account?" or "Forgot password?"
4. Click it

Step 2: Enter Email & Solve Puzzle
1. Type your full email address
2. Click "Next"
3. Solve a puzzle to prove you're human
4. Click "Next"

Step 3: How to Verify
Microsoft will ask you to verify. Choose one:

A) Text to Your Phone
   • Select "Text" option
   • Microsoft sends a code via text
   • Type the code they send
   • Click "Verify"

B) Email to Backup Address
   • If you added a backup email
   • Click the link in the recovery email
   • Creates new password

C) Answer Security Questions
   • Questions you set up before
   • Answer them

Step 4: Create New Password
1. Type your new password (at least 8 characters)
2. Mix uppercase, lowercase, numbers, special characters
3. Confirm by typing it again
4. Click "Next"

Step 5: Done!
1. Your password is reset
2. You can now log into Outlook.com
3. You might need to update password on your phone apps`),
    tips: [
      t('passwordResetGuide.outlookTip1', 'Outlook accounts work on Outlook.com and Windows'),
      t('passwordResetGuide.outlookTip2', 'You may also have OneDrive and other services linked'),
      t('passwordResetGuide.outlookTip3', 'Recovery phone is fastest method'),
    ],
    hasCheckpoint: true,
  },
  {
    id: 'email-password-yahoo',
    title: t('passwordResetGuide.resetYahooMailPassword'),
    content: t('passwordResetGuide.yahooContent', `For Yahoo.com email accounts:

Step 1: Go to Yahoo Login
1. Visit: yahoo.com
2. Click "Sign in"
3. Look for "Trouble signing in?" or "Forgot password?"

Step 2: Verify Your Account
1. Enter your Yahoo email address
2. Click "Next"
3. Yahoo asks you to verify it's really you

You'll be offered options:

A) Verify with Phone
   • Get text with security code
   • Type the code
   • Click "Verify"

B) Verify with Backup Email
   • Confirms using recovery email
   • Click link in that email

C) Account Key
   • If you set one up previously
   • Use that

Step 3: Create New Password
1. Enter your NEW password
2. Confirm it by typing again
3. Password needs: 8+ characters, mix of cases, numbers, special characters
4. Click "Save changes"

Step 4: Log In
1. Go to Yahoo.com
2. Use your new password to sign in
3. You're done!`),
    tips: [
      t('passwordResetGuide.yahooTip1', 'Yahoo has lots of security options - use whichever is easiest'),
      t('passwordResetGuide.yahooTip2', 'Your Yahoo account may have other services attached'),
      t('passwordResetGuide.yahooTip3', 'Keep your new password safe'),
    ],
    hasCheckpoint: true,
  },
  {
    id: 'library-pin',
    title: t('passwordResetGuide.resetYourLibraryCardPin'),
    content: t('passwordResetGuide.libraryPinContent', `Your library card PIN is a 4-digit number (just numbers, no letters):

What It's Used For:
• Checking out items at self-checkout machines
• Phone renewals of books
• Some library computer access

How to Reset It:

Option 1: At the Library Desk
1. Bring your library card (or ID)
2. Go to the main desk
3. Tell staff: "I forgot my PIN"
4. Staff will verify it's your card
5. They'll give you a new PIN on the spot

Option 2: Through Library Website
1. Visit the library's website
2. Log into "My Account"
3. Look for "Manage PIN" or "Change PIN"
4. Follow the steps to reset
5. You might need your card number and birthdate

Your New PIN:
• Will be given to you right away
• Is temporary until you change it to something you'll remember
• You can change it again anytime
• Write it down until you memorize it`),
    tips: [
      t('passwordResetGuide.libraryPinTip1', 'Library staff can reset this immediately - it takes 1 minute'),
      t('passwordResetGuide.libraryPinTip2', 'Phone number is posted at the library desk'),
      t('passwordResetGuide.libraryPinTip3', 'Easier than email password reset'),
    ],
  },
  {
    id: 'recovery-options-failed',
    title: t('passwordResetGuide.recoveryDidntWork', "Recovery Didn't Work - What Now?"),
    content: t('passwordResetGuide.recoveryFailedContent', `Sometimes password recovery doesn't work. Here's why and what to do:

Common Reasons:
✗ Recovery phone number is old (you got a new phone)
✗ Backup email is outdated
✗ Forgotten security question answers
✗ Account is temporarily locked (for security)
✗ You can't access email or phone on file

What to Try:

1. Wait 24 Hours
   • Sometimes accounts are temporarily locked after failed attempts
   • Try again tomorrow
   • Usually resets within 24 hours

2. Try Different Recovery Method
   • If phone didn't work, try email
   • If email didn't work, try security questions
   • Try all available options

3. Use Another Device
   • Try on a different phone or computer
   • Sometimes device-specific issues cause problems
   • Library computers are available

4. Use Incognito/Private Browsing
   • Open new Incognito or Private window
   • Try password reset again
   • Sometimes cookies cause issues

5. Clear Browser Cache
   Windows:
   • Press: Ctrl + Shift + Delete
   • Select "All time"
   • Clear browsing data

   Mac:
   • Command + Shift + Delete
   • Select "All time"
   • Clear browsing data

6. Ask Google/Microsoft/Yahoo Directly
   For Gmail:
   • Visit: accounts.google.com/account/recovery

   For Outlook:
   • Visit: account.microsoft.com/account/recovery

   For Yahoo:
   • Visit: login.yahoo.com/forgot

What If Nothing Works?

Come visit the library! Our staff can:
✓ Help you step-by-step on library computers
✓ Contact email services on your behalf
✓ Help you create new recovery options
✓ Set up a new email account if needed
✓ Troubleshoot specific error messages`),
    tips: [
      t('passwordResetGuide.recoveryFailedTip1', 'Email services prioritize security - resets take time sometimes'),
      t('passwordResetGuide.recoveryFailedTip2', 'Library staff have seen this many times'),
      t('passwordResetGuide.recoveryFailedTip3', 'Always better to ask for help than to give up'),
    ],
  },
  {
    id: 'prevent-future',
    title: t('passwordResetGuide.preventPasswordProblemsInFuture'),
    content: t('passwordResetGuide.preventFutureContent', `Now that you've reset your password, let's prevent this happening again:

Save Your Password Safely:

Option 1: Password Manager (Recommended)
• Use: Bitwarden, 1Password, LastPass, or Apple Keychain
• They remember passwords for you
• You only need to remember one primary password
• Very secure and convenient

Option 2: Write It Down
• Write in a notebook you keep at home
• Not on a sticky note on your computer!
• Keep it somewhere safe
• This works fine for less important accounts

Option 3: Memorize It
• If it's a strong, simple password
• Say it out loud a few times
• Most people can memorize one main password

Set Up Recovery Options:

1. Add Backup Email
   • Gmail: Settings → Account → Recovery options
   • Outlook: Account.microsoft.com → Security
   • Yahoo: Account → Account security
   • Add another email you have access to
   • Makes recovery easier

2. Add Phone Number
   • Same location as backup email
   • Use a phone number you'll keep
   • They'll text you verification codes

3. Set Security Questions
   • Gmail/Outlook/Yahoo all offer this
   • Use questions with answers ONLY YOU know
   • Avoid public information

4. Create Backup Codes
   • Many services offer one-time backup codes
   • Write these down and keep them safe
   • Use only if you lose access to everything else

Enable 2-Factor Authentication (Extra Security):

What It Is:
• You log in with password
• Service sends you a code (text or app)
• You enter that code
• Makes account much more secure

How to Set Up:
Gmail:
1. Go to myaccount.google.com
2. Click "Security" on left
3. Find "2-Step Verification"
4. Click "Enable"
5. Follow the steps

Outlook:
1. Go to account.microsoft.com/security
2. Click "Advanced security options"
3. Find "Additional security options"
4. Enable 2-Step Verification

This makes your account much safer from hackers!`),
    tips: [
      t('passwordResetGuide.preventFutureTip1', 'Password managers are worth the small cost'),
      t('passwordResetGuide.preventFutureTip2', 'It takes 5 minutes to set up recovery options'),
      t('passwordResetGuide.preventFutureTip3', '2-Factor Authentication prevents most hacking'),
      t('passwordResetGuide.preventFutureTip4', 'Stronger passwords = less likely to need reset'),
    ],
  },
  {
    id: 'complete',
    title: t('passwordResetGuide.youreAllSet', "You're All Set!"),
    content: t('passwordResetGuide.completeContent', `Great job getting your password reset!

Your Next Steps:
✓ Write down or save your new password
✓ Set up recovery options (backup email/phone)
✓ Consider enabling 2-Factor Authentication
✓ Come back to the library if you have questions

Quick Reference:
• Email login issues? Visit gmail.com/outlook.com/yahoo.com directly
• Library card PIN? Ask at the desk or call
• Still stuck? Visit us - we're here to help!

Remember:
• Never share your password with anyone
• Don't use the same password for multiple accounts
• If someone asks for your password, it's probably a scam
• We never ask for passwords via email or phone

You're ready to use your account again!`),
    tips: [
      t('passwordResetGuide.completeTip1', 'Check that you can actually log in before leaving'),
      t('passwordResetGuide.completeTip2', 'Update your password on any apps that use it'),
      t('passwordResetGuide.completeTip3', 'Tell staff if you need help setting up recovery options'),
    ],
  },
]

export default function PasswordResetGuide(): React.ReactElement {
  const { t } = useTranslation()
  const steps = useMemo(() => _buildSteps(t), [t])
  return (
    <GuidedWalkthrough
      guideId="password-reset"
      title={t('passwordResetGuide.resetAForgottenPassword')}
      description={t('passwordResetGuide.pageDescription', 'Step-by-step help for resetting email or library card passwords')}
      steps={steps}
      onComplete={() => {
      }}
    />
  )
}
