# Blog

The {{library_name}} public blog at [/blog](/blog), administered from
[/staff/blog](/staff/blog). For the writer-facing handbook (tone, voice,
draft / schedule / publish workflow), see
[Marketing -- publish a blog post end-to-end](../staff-training/roles/marketing/blog-publishing.md).
This page is the admin angle: who can do what, what to configure,
what to watch.

---

### Blog list (`/staff/blog`)
Staff-side dashboard: search, status filter (draft / scheduled /
published), bulk publish, bulk delete, per-row schedule / publish /
unpublish / edit. Header counters show total / published / scheduled /
draft. Bulk delete is permanent; train marketing staff to **unpublish**
rather than delete unless the post is genuinely junk.

### New / edit post (`/staff/blog/new`, `/staff/blog/:id/edit`)
TipTap editor for the body, plus title, slug, TLDR, meta description,
featured image, tags (autocomplete from existing), series. Version
history per post; **Restore** brings a prior version back as the current
draft. Image uploads cap at 5 MB and require alt text on upload.

### Feature gating
There is **no dedicated `blog_enabled` feature flag** at the time of
writing -- the blog ships on for every organization. If you need to
hide the public blog (e.g. for a soft-launch library), the supported
ways today are:

- Keep all posts in draft, so `/blog` shows an empty list.
- Remove or hide the blog link in the site header / footer.

If a hard on/off switch becomes a need, it belongs on the
`OrganizationFeatures` model alongside `marketing_enabled` and friends
-- file a ticket rather than improvising a flag.

### Categories and tags
There are no categories. Organization is by **tags** (free-form,
shared across all posts) and optional **series** (a named, ordered run
of posts).

To manage tags, edit a post -- adding or removing a tag from a post
adds or removes it system-wide. There is currently no admin UI for
renaming or merging tags; if a tag has a typo or duplicates an
existing one, fix it on every post that uses the wrong one, and the
orphaned tag will stop appearing. (If this gets painful at scale,
build a tag-merge admin tool -- it is a small backend job.)

Series names are case-sensitive and exact-match. Spelling consistency
is the only "configuration" needed.

### Bulk actions
From [/staff/blog](/staff/blog):

- **Bulk publish** -- moves selected drafts to published immediately.
  Useful when batch-prepping content for a campaign launch.
- **Bulk delete** -- permanent. Two-step confirm. Audit-log-worthy;
  prefer unpublish.

There is currently no bulk re-tag or bulk re-schedule. If you need
those, raise a ticket -- they are straightforward additions.

### Moderation queue
There is no moderation queue, because there is no on-site comment
system and no patron-submitted posts. Every post is staff-authored
through [/staff/blog](/staff/blog).

If you later introduce patron-submitted posts or comments, build the
moderation queue first -- do not ship the submission UI without one.

### Scheduled posts
Scheduled posts flip to **published** server-side when their
`scheduled_at` timestamp passes (UTC). If your server clock drifts
or the scheduler service is paused, scheduled posts will be late.
Spot-check by sorting [/staff/blog](/staff/blog) by status =
Scheduled and confirming nothing in the past is still sitting there.

### Public surfaces
- `/blog` -- list, paginated.
- `/blog/<slug>` -- post.
- `/blog/series/<series_name>` -- ordered series.
- `/api/v1/blog/feed` -- RSS / Atom. Linked from the homepage
  `<link rel="alternate">` for auto-discovery.
- `/api/v1/blog/sitemap.xml` -- for search engines.
- `/api/v1/blog/analytics` -- aggregate view counts, deduplicated
  by hashed IP+UA (no raw IP storage).

### Media
Image uploads from the editor live in the blog media store. List and
delete via the admin media endpoints (`/api/v1/blog/media`,
`/api/v1/blog/media/<filename>`). There is no orphan-cleanup cron
today; expect the store to grow slowly and prune manually a few times
a year.

### Related docs
- [Marketing -- publish a blog post end-to-end](../staff-training/roles/marketing/blog-publishing.md)
- [Marketing](marketing.md)
