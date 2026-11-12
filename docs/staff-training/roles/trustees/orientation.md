---
title: Board trustee -- portal orientation
audience: trustees
diataxis: tutorial
estimated_time: 45-60 minutes
last_reviewed: 2026-05-17
app_routes:
  - /board
  - /board/meetings
  - /board/minutes
  - /board/motions
  - /board/documents
  - /board/committees
  - /board/members
  - /board/public-comments
  - /account
---

# Board trustee -- portal orientation

## What this is for

A walk-through of the L30 board portal for a brand-new trustee, end to end. After this doc you should be able to find your next meeting, read its packet, review and vote on minutes from the last one, comment on a draft policy, and pull up the documents your board has adopted.

## When you'd use it

- Your first time logging into the portal, usually the day after you're sworn in.
- Coming back to the portal after a stretch away (a summer recess, a missed meeting cycle) and wanting to re-orient.

You do not need to read this in one sitting. The portal is designed so that a meeting reminder email tells you exactly which link to open and what to do; this doc is the map you keep open the first few times.

## Before you start

- You've been invited as a trustee by `{{system_admin_email}}` or by `{{board_president_name}}`. The invitation arrives as an email from this library's L30 instance with a one-time setup link.
- You have the device you'll use for board work (a personal laptop or tablet is fine -- the portal works in any modern browser).
- You know your library's open-meetings law basics. The portal helps you comply but does not replace your training as a trustee.

## First login and account setup

1. Open the email titled something like "You've been invited as a trustee at `{{library_name}}`." Click the setup link.
2. Set a password. The portal enforces a minimum of 12 characters and rejects common passwords; a passphrase of three or four unrelated words is the easiest pattern to remember and the hardest to guess.
3. Enable multi-factor authentication (MFA). You'll be prompted on first login. The portal supports authenticator apps (Google Authenticator, 1Password, Authy, etc.) and, where configured by your admin, email-based codes. Authenticator app is preferred -- it doesn't depend on your mail being delivered in time.
4. After login you land at [/board](/board), the board hub. If you instead land at the staff dashboard with no `Board` item in the sidebar, your trustee role hasn't been applied -- email `{{system_admin_email}}`.

If you forget your password, use the "Forgot password" link on the sign-in page. The reset email comes from the same address the invitation did. If MFA codes stop working (lost phone), `{{system_admin_email}}` can reset MFA for you; for security, password and MFA cannot both be reset over chat or phone.

## The shape of the board hub

When you open [/board](/board) as a trustee, the dashboard surfaces what's coming up and what's waiting on you:

- **Attention items.** A list of things needing board action -- minutes pending your review, motions open for vote, policies in public-comment that you've been asked to weigh in on.
- **Next meeting.** Date, time, location, and a link to the meeting detail page with the agenda and packet.
- **Upcoming timeline.** The next several scheduled meetings and any deadlines (annual report due, audit window, policy review cycle).
- **Recent activity.** Documents added, minutes approved, motions closed since you last logged in.
- **Status by area.** Governance and administration status cards: are minutes current, is the conflict-of-interest disclosure cycle complete, is the annual report on track. Green/amber/red rollups.

The hub is a status surface -- the work happens on the sub-pages linked from each tile. The rest of this doc walks each major surface in the order you'll most often use them.

<!-- screenshot: trustee dashboard with attention items, next meeting, and status cards labeled -->

## Meetings

**Where:** [/board/meetings](/board/meetings).

**What's here.** Every board meeting -- past, upcoming, cancelled -- with date, location, type (regular, special, executive session), and status. Click into a meeting for the detail page: full agenda, attached packet documents, public-comment registrations, attendance, and (after the meeting) the minutes and recorded votes.

**What you can do.**

- Review the agenda and packet before a meeting. Most boards publish the packet 3-7 days ahead per your local open-meetings rules.
- RSVP for an upcoming meeting using the `Attendance` control on the meeting detail page. Pick `attending`, `not attending`, or `tentative`. Your RSVP helps the chair confirm quorum in advance.
- During the meeting, check in via the attendance panel -- this becomes part of the official record.
- After the meeting, follow links from the meeting detail page to its minutes and votes.

**What you cannot do.**

- You cannot create or edit meetings. Scheduling is an admin/director task. If a date conflict comes up, message `{{board_president_name}}` or `{{system_admin_email}}`.
- You cannot edit attendance records for other trustees. Each trustee marks their own.

## Minutes

**Where:** [/board/minutes](/board/minutes), or follow the `Minutes` link from a meeting detail page.

**What's here.** The minutes for each past meeting, in one of these states: `draft` (the recorder is still writing), `pending approval` (ready for the board to approve at the next meeting), `approved` (finalized and part of the permanent record), or `amended` (approved but later corrected via a formal amendment).

**What you can do.**

- Read draft and pending minutes ahead of the next meeting so you arrive ready to approve, correct, or move to amend.
- Approve minutes during the meeting via the motion-and-vote workflow (see "Review and approve minutes" below).
- After approval, view the minutes any time as part of the public record. Approved minutes are PDF-exportable from the meeting detail page.

**What you cannot do.**

- You cannot edit minutes after they're approved. Approved minutes are locked; corrections require a formal amendment motion. The portal enforces this -- the edit controls disappear once a minutes record flips to `approved`.
- A trustee who recorded or drafted a set of minutes cannot also be the approver-of-record; the portal enforces separation of duties between creator and approver.

## Motions and votes

**Where:** [/board/motions](/board/motions). Individual motions live at `/board/motions/{id}`.

**What's here.** Every motion the board has considered, with its current state (`open`, `passed`, `failed`, `tabled`, `withdrawn`), the tally if voting has closed, and the recorded votes per trustee. Motions are linked to the meeting they were taken at and, where applicable, to the resolution or policy they enacted.

**What you can do.**

- Cast your vote on any motion that is `open` and that you have not already voted on. The portal records `yes`, `no`, or `abstain` with a server-side timestamp; once recorded, your vote cannot be re-cast.
- View your own and other trustees' votes after the vote closes. Every vote is public to the board.
- See the quorum and threshold (simple majority, two-thirds, unanimous) the motion requires.

**What you cannot do.**

- You cannot change or delete a vote once cast. If you mis-clicked, tell the chair before the vote closes; the chair has the procedural authority to re-open a vote, but the original cast vote stays in the audit log.
- The portal currently does not block a trustee with a declared conflict from casting a vote -- recusal is on the honor system and is also tracked separately under "Conflict of interest" below. If you have a conflict, recuse yourself by abstaining and stating the recusal aloud for the record. Your board's parliamentarian or counsel is the authority here, not the software. (Tracking issue: portal recusal enforcement.)

## Documents

**Where:** [/board/documents](/board/documents).

**What's here.** Policies, bylaws, the board manual, adopted resolutions, packets, and other governance documents -- versioned, with publication date and (for policies) review cycle. Each document has an active version and, where applicable, an archive of prior versions.

**What you can do.**

- Read any document the board has access to. Most board documents are also public; some (personnel policy drafts, attorney memoranda) may be restricted to trustees.
- Download a PDF of any version.
- For documents in `draft` status that have been opened for board input, leave comments on the document detail page. Comments are visible to other trustees and to the drafting staff.

**What you cannot do.**

- You cannot edit, publish, or archive documents directly. Drafting and publication is done by staff (typically the director or the board secretary). Your role is to comment, then to vote when the document comes up as a motion.

## Committees

**Where:** [/board/committees](/board/committees). Individual committees live at `/board/committees/{id}`.

**What's here.** Each standing or ad-hoc committee (finance, personnel, policy, building, etc.) with its current charge, membership, and a list of its meetings, agendas, and minutes. Committees follow the same meeting and minutes model as the full board.

**What you can do.**

- See who serves on each committee and what each committee's current charge is.
- If you serve on a committee, the committee detail page is your working surface for that committee's meetings -- same agenda/packet/minutes/voting flow as the full board, scoped to the committee.
- If you don't serve on a committee, you can still read its minutes and agendas (unless the committee meets in executive session for a sealed topic).

**What you cannot do.**

- You cannot change committee membership. The board appoints committee members through a regular motion; the admin updates the roster after the appointment passes.

## Members and conflict of interest

**Where:** [/board/members](/board/members).

**What's here.** The current board roster with each trustee's position (president, vice president, secretary, treasurer, member-at-large), term start and end, and contact info shared with the board. Past trustees appear in the historical roster.

Your own profile is where your contact preferences and conflict-of-interest disclosures live. Conflict-of-interest disclosures should be filed annually (and any time a new conflict arises). The portal does not currently block you from voting on a matter where you've disclosed a conflict -- this is on you and your chair to enforce per board policy.

**What you can do.**

- Update your own profile and contact preferences.
- File a conflict-of-interest disclosure.
- View other trustees' published profile info (the parts they've chosen to share with the board).

**What you cannot do.**

- You cannot add, remove, or change another trustee's role. That happens at the admin level after a board action.

## Public comments

**Where:** [/board/public-comments](/board/public-comments).

**What's here.** Public comments submitted ahead of, or during, board meetings. Each comment has a type (`written`, `in-person`, `virtual`), a status (`pending`, `approved`, `rejected`, `read into record`), and -- where the commenter signed up to speak -- a registration with a time limit and speaking slot.

**What you can do.**

- Read submitted public comments before a meeting so you arrive informed.
- See speaker registrations for the next meeting's public-comment period.

**What you cannot do.**

- You cannot moderate, approve, or reject comments. That is a staff function (typically the board secretary or director), and the portal logs every moderation decision.
- You cannot speak on a commenter's behalf or edit their submission.

## What you can see about patrons

**Nothing.** The trustee role grants access to board governance surfaces -- meetings, minutes, motions, documents, committees, public comments -- and to library-level reports that come up in agendas (budget, statistics, strategic plan progress). The trustee role does not grant access to patron records, individual circulation history, search history, account balances, or any data that identifies what an individual community member reads or borrows.

This is intentional and is a core privacy commitment of the library. If a patron's name comes up in a board matter (a personnel grievance involving a patron interaction, a tort claim, an appeal of a borrowing restriction), the related materials are prepared by staff and counsel, redacted appropriately, and provided to the board as document attachments to the relevant agenda item -- not by giving you a query tool over the patron database.

**Confidentiality reminders.**

- Executive session materials (when present), pre-decisional draft documents, personnel matters, and legal counsel communications are confidential. Discuss them only with other trustees and counsel, only in proper session, and not in writing outside the portal.
- Open Meetings Act compliance: deliberation between trustees about board business outside of a properly noticed meeting -- including over email or group text -- is generally not permitted in most states. Use the portal's comment fields on documents and motions; do not start a side-channel deliberation. When in doubt, ask `{{board_president_name}}` or library counsel.

## Common workflows

### Review and approve minutes from the last meeting

1. Open the meeting reminder email or go to [/board](/board) and look for "Minutes pending your review" in attention items.
2. Click through to the minutes. Read end to end. Note any corrections you want raised.
3. At the next meeting, when the chair calls for approval of the prior meeting's minutes:
   - If they're accurate, vote `yes` when the motion to approve is opened at [/board/motions](/board/motions) for that meeting.
   - If you have a correction, request it on the floor before the vote. Once approved, corrections require a formal amendment motion.
4. After the vote closes, the minutes flip to `approved` and become part of the permanent record. The minutes page shows the approval timestamp and who approved them.

### Comment on a draft policy

1. From [/board](/board) or [/board/documents](/board/documents), open the draft document. Drafts open for comment have a banner indicating so.
2. Read the draft. The document detail page shows the current version and any prior versions.
3. Use the comment field on the detail page to leave your input. Comments are visible to other trustees and to the staff drafting the policy.
4. When the policy comes to the floor as a motion, vote per your review.

### View a financial snapshot or report

1. From [/board](/board), check the next meeting's packet -- the treasurer's report and financial snapshot are typically attached.
2. For longer-form reports (annual audit, strategic plan progress, monthly statistics), open [/board/documents](/board/documents) and filter to reports.
3. If you need data not in the packet, ask `{{board_president_name}}` to request it from `{{director_name}}` ahead of the meeting. Trustees don't run reports directly; staff prepare and attach them.

### RSVP to an upcoming meeting

1. From [/board](/board), click the next meeting in the "Next meeting" tile, or open [/board/meetings](/board/meetings) and pick the meeting.
2. On the meeting detail page, find the attendance panel and pick `attending`, `not attending`, or `tentative`.
3. If you can't make it, message `{{board_president_name}}` so the chair can confirm quorum and, if applicable, arrange a substitute reporter for any committee you'd been expected to report on.

### Update your contact info or file a conflict-of-interest disclosure

1. Go to your profile at [/board/members](/board/members) and open your own entry, or use [/account](/account) for account-level settings (password, MFA, email).
2. Edit your contact info or open the conflict-of-interest section.
3. Save. Changes to disclosures are audit-logged.

## If something looks wrong

If you see something that doesn't match what you expected -- a meeting at the wrong time, minutes attributed to the wrong meeting, a vote you didn't cast appearing under your name, a document you can't open, an attention item that won't clear -- do not try to fix it by clicking around. Contact `{{system_admin_email}}` with:

- The page URL.
- What you saw.
- What you expected to see.
- The approximate time it happened.

For governance questions -- whether a motion was properly framed, whether minutes should be amended, whether a comment falls inside or outside the comment period -- contact `{{board_president_name}}`. The portal records what happens; it doesn't decide what should happen. That's the board's job, and yours.
