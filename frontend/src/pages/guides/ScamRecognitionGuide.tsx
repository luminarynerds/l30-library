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
    title: t('scamRecognitionGuide.recognizingAvoidingScamsOnline'),
    content: t('scamRecognitionGuide.introContent', `Scammers are clever and try to trick millions of people every day.
You can protect yourself by knowing what to look for.

This guide teaches you:
• How to recognize common scams
• What to do if you see one
• How to report scams
• How to stay safe online`),
    tips: [
      t('scamRecognitionGuide.introTip1', 'Scams target everyone - young and old'),
      t('scamRecognitionGuide.introTip2', 'If something feels wrong, it probably is'),
      t('scamRecognitionGuide.introTip3', 'Never feel embarrassed if you almost fell for one'),
      t('scamRecognitionGuide.introTip4', 'Telling others helps protect them too'),
    ],
  },
  {
    id: 'email-scams',
    title: t('scamRecognitionGuide.emailScamsPhishing', 'Email Scams: Phishing'),
    content: t('scamRecognitionGuide.emailScamsPhishingContent', `Phishing emails try to trick you into revealing passwords or personal info.

What They Look Like:
[WARNING] "Confirm your password"
[WARNING] "Verify your account"
[WARNING] "Unusual activity on your account"
[WARNING] "Update your payment information"
[WARNING] "Click here to claim prize"

Red Flags:
[FLAG] Urgent language ("ACT NOW!" "IMMEDIATE ACTION REQUIRED")
[FLAG] Asking for passwords or personal info
[FLAG] Mismatched email address (looks official but isn't)
[FLAG] Bad grammar or spelling
[FLAG] Link doesn't match the sender name
[FLAG] Generic greeting ("Dear Customer" instead of your name)
[FLAG] Suspicious attachments

Example:
"From: PayPal Security Team
Subject: URGENT - Unusual activity detected!
Message: Click here to confirm your identity

Your account has been locked.
Click: www.paypall-security.com (NOT real PayPal!)
Enter your password to unlock."

What to Do:
• Don't click the link
• Don't reply to the email
• Close the email
• Go directly to the real website (not the link)
• Report the email as spam/phishing
• Delete the email

How to Report:
Gmail: Click "Report phishing"
Outlook: Click "Junk" → "Phishing"
Other: Forward to phishing@company.com`),
    tips: [
      t('scamRecognitionGuide.emailScamsPhishingTip1', 'Real companies never ask for passwords in emails'),
      t('scamRecognitionGuide.emailScamsPhishingTip2', 'Go directly to the official website, never click email links'),
      t('scamRecognitionGuide.emailScamsPhishingTip3', 'Hover over links to see the real address (don\'t click)'),
      t('scamRecognitionGuide.emailScamsPhishingTip4', 'When in doubt, call the company directly'),
    ],
    troubleshooting: t('scamRecognitionGuide.emailScamsPhishingTroubleshooting', `If you clicked a link: Change your password immediately and monitor your account for fraud.`),
  },
  {
    id: 'tech-support-scams',
    title: t('scamRecognitionGuide.techSupportScams', 'Tech Support Scams'),
    content: t('scamRecognitionGuide.techSupportScamsContent', `These scammers pretend to be tech support and trick you into giving access to your computer.

What They Look Like:
[WARNING] "Your computer has a virus - call now!"
[WARNING] Pop-up saying "System Error - Contact Tech Support"
[WARNING] Pop-up with phone number to call
[WARNING] Email saying you have malware
[WARNING] Caller claiming to be from Apple, Microsoft, or your bank

Red Flags:
[FLAG] Unsolicited call or message
[FLAG] They want remote access to your computer
[FLAG] They ask you to download something
[FLAG] They want payment for "fixing" the problem
[FLAG] They ask for credit card information
[FLAG] Pop-ups claiming urgent action needed

Example:
"WARNING: VIRUS DETECTED!
Your computer is at risk!
Call 1-800-555-0199 immediately
Or download antivirus software"

The Reality:
• Your browser can't detect viruses in pop-ups
• Apple/Microsoft/Banks don't call randomly
• Real tech support doesn't ask for remote access
• They don't demand immediate payment
• Real software never pops up with urgency

What to Do:
• Don't call the number
• Don't download anything
• Close the browser tab or window
• Restart your computer if needed
• Ignore pop-up messages
• Report the pop-up (right-click → Report)

If You Already Did:
• Change your passwords immediately
• Check your credit card for fraud
• Run a real antivirus scan (Windows Defender, Malwarebytes)
• Tell your bank about any credit card activity
• Consider calling a real tech expert`),
    tips: [
      t('scamRecognitionGuide.techSupportScamsTip1', 'Real tech support never calls you first'),
      t('scamRecognitionGuide.techSupportScamsTip2', 'If your computer acts up, call YOUR provider directly'),
      t('scamRecognitionGuide.techSupportScamsTip3', 'Close pop-ups without clicking anything inside'),
      t('scamRecognitionGuide.techSupportScamsTip4', 'Library staff can help check your computer'),
    ],
  },
  {
    id: 'romance-scams',
    title: t('scamRecognitionGuide.romanceDatingScams', 'Romance & Dating Scams'),
    content: t('scamRecognitionGuide.romanceDatingScamsContent', `Scammers create fake profiles to build relationships and then ask for money.

What They Look Like:
[WARNING] Too-good-to-be-true profile pictures
[WARNING] Person immediately says "I love you"
[WARNING] Quick progression to meeting/marriage talk
[WARNING] Then asks for money ("emergency back home")
[WARNING] Asks for gift cards or wire transfer

Red Flags:
[FLAG] Won't video chat (always excuses)
[FLAG] Asks for money very soon in relationship
[FLAG] Says they're stuck abroad needing rescue
[FLAG] Claims family emergency needing funds
[FLAG] Asks you to keep relationship secret
[FLAG] Profile looks like a model/celebrity
[FLAG] Lives conveniently far away

Common Excuses:
"I need money for plane ticket to see you"
"My mother needs surgery"
"I'm stuck at airport"
"Business emergency - need $5,000"

What to Do:
• Ask for video chat - real people will
• Do a reverse image search (Google Images)
• Ask personal questions (memory from past conversations)
• Don't send money - EVER
• Tell trusted friends/family about concerns
• Report the profile

If You've Been Scammed:
• Tell your bank immediately
• Report to the dating app
• Report to FBI (ic3.gov)
• Tell someone you trust
• Don't feel ashamed - it happens to thousands`),
    tips: [
      t('scamRecognitionGuide.romanceDatingScamsTip1', 'Real relationships don\'t require money from strangers'),
      t('scamRecognitionGuide.romanceDatingScamsTip2', 'Video chat early if it\'s getting serious'),
      t('scamRecognitionGuide.romanceDatingScamsTip3', 'Google image search photos to verify identity'),
      t('scamRecognitionGuide.romanceDatingScamsTip4', 'Trust your gut - if weird, it probably is'),
    ],
  },
  {
    id: 'money-transfer-scams',
    title: t('scamRecognitionGuide.moneyTransferPrizeScams'),
    content: t('scamRecognitionGuide.moneyTransferPrizeScamsContent', `These scammers claim you won something or have money waiting, but need to send money first.

"You Won!" Scams:
[WARNING] "You won a prize!" (you never entered)
[WARNING] "Claim your inheritance" (from unknown relative)
[WARNING] "Congratulations - lottery winner!" (didn't buy ticket)
[WARNING] "Free money from government"

They Always Ask:
• Processing fee
• Tax payment upfront
• ID verification fee
• Wire transfer of funds
• Gift cards or cryptocurrency

The Reality:
• Real prizes don't require money first
• Actual lotteries don't notify by email
• Government benefits don't work this way
• You never have to pay to get free money
• Legitimate contests are verified

What to Do:
• Delete or ignore the message
• Don't respond or click links
• If unsure, call the organization directly
• Report the message
• Tell others

Example Scams:
1. "You won $500,000 in Microsoft Lottery!"
   → You never entered a Microsoft Lottery

2. "Claim your $1,200 stimulus check"
   → Government doesn't email about benefits

3. "You inherited money from a relative"
   → From someone you've never heard of

4. "Free government grant for small business"
   → Legitimate grants don't work this way`),
    tips: [
      t('scamRecognitionGuide.moneyTransferPrizeScamsTip1', 'If it sounds too good to be true, it is'),
      t('scamRecognitionGuide.moneyTransferPrizeScamsTip2', 'Real organizations have websites you can verify'),
      t('scamRecognitionGuide.moneyTransferPrizeScamsTip3', 'Never send money for "free" money'),
      t('scamRecognitionGuide.moneyTransferPrizeScamsTip4', 'Call organizations directly using phone book number'),
    ],
  },
  {
    id: 'social-media-scams',
    title: t('scamRecognitionGuide.socialMediaScams', 'Social Media Scams'),
    content: t('scamRecognitionGuide.socialMediaScamsContent', `Scammers use Facebook, Instagram, and other social media to target people.

Common Social Media Scams:

Friend/Family Impersonation:
"Hi Mom! I'm stuck in Mexico and need $1,000 for hotel!"
Reality: Usually someone hacked their account or it's a fake profile

What to Do:
• Call your friend/family to verify
• Ask personal questions only they'd know
• Don't send money via social media
• Tell the platform it's impersonation

Fake Giveaways:
"Like and share to win an iPhone!"
Reality: You'll get hacked or spam, never the prize

Fake Jobs:
"Make $5,000/week from home!"
Reality: They'll ask for money upfront or your info

Marketplace Scams:
Selling something on Facebook/Craigslist?
[WARNING] Paying in gift cards
[WARNING] Overpaying and asking you to wire back difference
[WARNING] Meeting in unsafe location
[WARNING] No payment verification

What to Do:
• Meet in safe public place (police station parking lot)
• Bring someone with you
• Verify payment before handing over item
• Use secure payment methods
• Tell someone where you're going

Red Flags on Social Media:
[FLAG] Account brand new (few friends/followers)
[FLAG] Few or stolen photos
[FLAG] Messages with poor grammar
[FLAG] Quick trust-building
[FLAG] Requests to move to private messaging`),
    tips: [
      t('scamRecognitionGuide.socialMediaScamsTip1', 'Don\'t click suspicious links on social media'),
      t('scamRecognitionGuide.socialMediaScamsTip2', 'Verify friend requests from people you know'),
      t('scamRecognitionGuide.socialMediaScamsTip3', 'Never send money through social media'),
      t('scamRecognitionGuide.socialMediaScamsTip4', 'Report suspicious accounts and messages'),
    ],
  },
  {
    id: 'what-to-do',
    title: t('scamRecognitionGuide.ifYouSuspectAScam'),
    content: t('scamRecognitionGuide.ifYouSuspectAScamContent', `Follow these steps if you think something is a scam:

Step 1: STOP
[WARNING] Don't send money
[WARNING] Don't click links
[WARNING] Don't download anything
[WARNING] Don't give personal info

Step 2: VERIFY
Call the organization directly using a number from their official website
(Not a number from the email/message)

Step 3: REPORT
Report to:
• Email provider (Gmail, Outlook, etc.)
• Social media platform
• Website/organization
• FTC (ftc.gov)
• FBI (ic3.gov)
• Local police (non-emergency)

Step 4: TELL SOMEONE
Tell trusted friends/family so they're aware too

If Money Was Sent:

Immediately:
1. Contact your bank/payment service
2. Tell them you were scammed
3. Ask about reversing the transaction
4. Report stolen payment method
5. File a police report

Then:
• Change all your passwords
• Monitor credit cards for fraud
• Consider credit freeze (protects against ID theft)
• Don't be embarrassed - this happens to millions

Reporting Resources:
• FBI Internet Crime Complaint Center: ic3.gov
• FTC Scam Report: reportfraud.ftc.gov
• Local police: Non-emergency number
• Your bank's fraud department

Important:
Scammers are good at what they do. If you fell for one, it's not your fault. Millions of smart people fall for scams every year.

The important thing is:
• Recognize it as fraud
• Stop engaging
• Tell authorities
• Help protect others by sharing`),
    tips: [
      t('scamRecognitionGuide.ifYouSuspectAScamTip1', 'Money rarely can be recovered once sent'),
      t('scamRecognitionGuide.ifYouSuspectAScamTip2', 'Act fast if money was already sent'),
      t('scamRecognitionGuide.ifYouSuspectAScamTip3', 'Keep all emails and messages as evidence'),
      t('scamRecognitionGuide.ifYouSuspectAScamTip4', 'Follow up on your reports'),
    ],
  },
  {
    id: 'protect-yourself',
    title: t('scamRecognitionGuide.howToProtectYourself'),
    content: t('scamRecognitionGuide.howToProtectYourselfContent', `Best Practices:

Passwords:
• Use strong passwords (8+ characters, mix of letters/numbers/symbols)
• Different password for each account
• Password manager (like Bitwarden) remembers them for you
• Never share passwords

Two-Factor Authentication:
• Enable on email, social media, bank accounts
• Even if they get your password, they can't access your account
• Takes extra 10 seconds but protects you

Email & Online:
• Don't open attachments from strangers
• Hover over links to see real address (don't click)
• Check sender address carefully
• If unsure, go directly to website

Shopping Online:
• Only use secure websites (look for padlock icon)
• Only use trusted retailers
• Keep receipts and confirmation emails
• Monitor credit card statements

Phone Calls:
• Don't give info to unsolicited callers
• Hang up and call back using official number
• Banks will never call asking for passwords
• Real support can wait - you call them

General Safety:
• Keep software/apps updated
• Use antivirus (Windows Defender, Malwarebytes)
• Be skeptical - if weird, question it
• Talk to trusted people about suspicious things
• When in doubt, ask a librarian!

What NOT to Do:
[WARNING] Don't share passwords via email
[WARNING] Don't use WiFi without VPN for banking
[WARNING] Don't save passwords in browser
[WARNING] Don't ignore security warnings
[WARNING] Don't trust caller ID (easily spoofed)
[WARNING] Don't click links in unexpected emails
[WARNING] Don't enable remote access for strangers`),
    tips: [
      t('scamRecognitionGuide.howToProtectYourselfTip1', 'Most scams are preventable with caution'),
      t('scamRecognitionGuide.howToProtectYourselfTip2', 'Your library staff can help with online safety'),
      t('scamRecognitionGuide.howToProtectYourselfTip3', 'Teaching others helps protect your community'),
      t('scamRecognitionGuide.howToProtectYourselfTip4', 'Stay curious but cautious online'),
    ],
  },
  {
    id: 'complete',
    title: t('scamRecognitionGuide.youreNowMoreAware', 'You\'re Now More Aware!'),
    content: t('scamRecognitionGuide.youreNowMoreAwareContent', `You now know how to recognize and avoid common scams!

Remember:
• If it feels wrong, it probably is
• Real organizations don't ask for passwords
• Money sent can't usually be recovered
• You're not alone - millions get targeted
• Reporting scams helps others

Quick Reference:
- Phishing Emails: Don't click, report
- Tech Support: Don't download, don't call
- Romance: Video chat, verify identity
- Money "Offers": Never send money first
- Social Media: Verify before trusting
- Any Scam: Report it!

If Something Seems Wrong:
1. Trust your instinct
2. Ask a trusted person
3. Go directly to official sources
4. Never send money to verify
5. Report if it's fraud

Resources:
• Scam alert website: fbi.gov/scams-safety
• FTC fraud report: reportfraud.ftc.gov
• Your library staff - we can help!
• Trusted friends and family

Stay safe online!`),
    tips: [
      t('scamRecognitionGuide.youreNowMoreAwareTip1', 'Awareness is your best defense'),
      t('scamRecognitionGuide.youreNowMoreAwareTip2', 'Share this knowledge with friends and family'),
      t('scamRecognitionGuide.youreNowMoreAwareTip3', 'If you spot a scam, help others avoid it'),
      t('scamRecognitionGuide.youreNowMoreAwareTip4', 'Library staff can help answer safety questions'),
    ],
  },
]

export default function ScamRecognitionGuide(): React.ReactElement {
  const { t } = useTranslation()
  const steps = useMemo(() => _buildSteps(t), [t])
  return (
    <GuidedWalkthrough
      guideId="scam-recognition"
      title={t('scamRecognitionGuide.recognizingAvoidingScamsOnline2')}
      description={t('scamRecognitionGuide.description', 'Learn how to spot common scams and protect yourself online')}
      steps={steps}
      onComplete={() => {
      }}
    />
  )
}
