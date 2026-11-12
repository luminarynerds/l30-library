# Marketing

Sidebar "Marketing" group. Gated by `marketing_enabled`. Most pages send
external comms (email/SMS/social), so every action here is audit-logged
and most have a "test send" path. Use it.

---

### Marketing Hub (`/staff/marketing-hub`)
`/staff/marketing-nav` (the old standalone navigation hub) now redirects
here — it was folded into this page's **Directory** tab, a tile grid
linking to campaigns, email/event marketing, and analytics. Start here
when you don't know which marketing surface you need.

The **Create** and **History** tabs on the same page are the AI-assisted
campaign generator: copy drafts, segment suggestions, send time
predictions. Requires `ai_tools_enabled`; hidden when it's off. Outputs
are drafts — nothing is sent until you explicitly schedule it from
Campaigns.

### Campaigns (`/staff/marketing`)
Manage email/SMS marketing campaigns end-to-end: audience, content,
schedule, send. Requires `outreach_enabled`. Always send a test to
yourself before scheduling to a real segment.
See also: [Patron Segmentation](admin-settings.md#patron-segmentation-staffpatron-segmentation).

### Email Marketing (`/staff/admin/email-marketing`)
Redirects to Outreach & Communications with the email-marketing hash.
Templates, sender domain config, opt-out compliance lives here.
See also: [Outreach & Communications](admin-settings.md#outreach--communications-staffadminoutreach).

### Event Marketing (`/staff/admin/event-marketing`)
Redirects to Outreach & Communications with the event-marketing hash.
Event-specific promo templates and pre-event reminder cadence.

### Sharing Analytics (`/staff/admin/analytics/sharing`)
Which titles/programs/pages are being shared externally and through
which channel. Use this to figure out what's resonating before you
spend marketing budget on it.
