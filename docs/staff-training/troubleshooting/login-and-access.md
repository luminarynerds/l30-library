---
title: Troubleshooting -- login and access
audience: all-staff
diataxis: reference
estimated_time: 5 min
last_reviewed: 2026-05-14
app_routes:
  - /login
  - /forgot-password
  - /reset-password
  - /account
  - /staff
---

# Troubleshooting -- login and access

## What this is for

Self-service troubleshooting for staff who can't log in, can't access the right pages, or are seeing the wrong dashboard.

## When you'd use it

- You got blocked at the login screen.
- You logged in but pages look wrong or you can't find something you should be able to find.

## I can't log in

| Symptom | First check | Fix |
|------|------|------|
| "Invalid email or password" | Caps lock; email spelling; trailing space | Use the `Forgot password` link on [/login](/login). |
| `Forgot password` email never arrives | Spam folder; correct email on file | If the email is correct and spam is clean, ask `{{tech_support_email}}` to confirm your account exists and is active. |
| Password reset link reads "expired" | How long ago you requested it | Request a new reset from [/forgot-password](/forgot-password). Reset links expire after a short window; request fresh and use it immediately. |
| "Too many attempts" or account locked | Recent login attempts on this account | Wait 15 minutes, then try again. If still locked, contact `{{tech_support_email}}` for an unlock. |
| "Your account is inactive" | Whether your account was recently created or paused | Ask `{{head_of_circulation_name}}` or `{{tech_support_email}}` to re-activate. New accounts are sometimes inactive until staff onboarding is complete. |
| The login page itself won't load | Network; service status | If the whole staff site is unreachable for you and others, treat as outage; see "When to escalate" below. |

## I logged in but the wrong dashboard loads

The dashboard at [/staff](/staff) is role-calibrated. If it looks wrong:

1. Open [/account](/account).
2. Check the `Settings` tab for your function tag(s) and primary role. If empty or wrong, fix what you can; some role fields are admin-only and read as plain text -- ask `{{head_of_circulation_name}}` for those.
3. If you have multiple function tags, the primary tag determines the default dashboard. Set it explicitly.
4. Save, then reload [/staff](/staff).

If the dashboard still doesn't match what you expect, your role assignment in the system may not include the function you're trying to do. Ask `{{head_of_circulation_name}}` to confirm what roles your account has.

## I can't see a page I should be able to see

| Symptom | Likely cause | What to do |
|------|------|------|
| Page returns `403 Forbidden` | Your role doesn't include access | Ask `{{head_of_circulation_name}}` for the role change. Don't try to work around it. |
| Page returns `404 Not Found` | The feature may not be enabled at your library (per-library feature flag) | Check with `{{tech_support_email}}` whether the feature is supposed to be on at this library. |
| Page loads but a panel is empty or stuck spinning | Frontend cache after a deploy, or a backend timeout | First: hard-refresh (Cmd+Shift+R on macOS, Ctrl+Shift+R on Windows/Linux). If that doesn't fix it, see `troubleshooting/slow-or-broken.md` (P3). |
| Page loads but the "Something unexpected happened" boundary appears | Often a stale cached chunk from a recent deploy | Hard-refresh first. If it persists, log out and back in. If still broken, escalate to `{{tech_support_email}}`. |
| Nav link is missing entirely | Your role doesn't enable that surface, or the feature flag is off | Confirm with `{{head_of_circulation_name}}` or `{{tech_support_email}}`. |

## My session keeps logging me out

Staff sessions are valid for a multi-hour idle window; long-running sessions across days are not supported by default. If you're being logged out far more often than expected:

1. Check whether you're using a private or incognito window. Those don't persist cookies between launches.
2. If you're on a shared computer that auto-clears cookies on close, talk to `{{tech_support_email}}` about a session policy that fits.
3. If a single browser is logging you out within minutes, clear that browser's L30 cookies and log in again; a corrupted session cookie can produce this.

## Two-factor authentication issues

If your library has 2FA enabled and you can't get past the prompt:

1. Confirm you're using the right authenticator entry. Many staff have several saved in one app.
2. If your code is rejected and you're sure it's correct, your device clock may be skewed; check that automatic time sync is on.
3. If you've lost the device that holds your 2FA enrollment, contact `{{tech_support_email}}` -- an admin can reset your 2FA enrollment so you can re-enroll on a new device.

2FA isn't enabled at every library running L30. If your library doesn't use it, this section doesn't apply.

## When to escalate

| Situation | Who |
|------|------|
| You can't log in AND the password reset email isn't arriving | `{{tech_support_email}}` |
| Account locked or inactive and you need it cleared today | `{{tech_support_email}}` |
| You can log in but the *wrong* role is on your account | `{{head_of_circulation_name}}` |
| You and colleagues can't reach the staff site at all (outage) | `{{system_admin_email}}` -- treat as system down |
| Suspected security incident (someone else used your account, data appears tampered) | `{{system_admin_email}}` plus `{{head_of_circulation_name}}`; do not investigate alone |

## Related

- [Welcome to L30 -- first-day orientation](../getting-started/orientation.md)
- [Library and L30 glossary](../getting-started/glossary.md)
- [Circulation desk role orientation](../roles/circulation/orientation.md)
