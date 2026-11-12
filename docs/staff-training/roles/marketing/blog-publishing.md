---
title: Marketing -- publish a blog post end-to-end
audience: marketing
diataxis: how-to
estimated_time: keep this tab open while you draft and publish
last_reviewed: 2026-05-17
app_routes:
  - /staff/blog
  - /staff/blog/new
  - /staff/blog/:id/edit
  - /blog
  - /api/v1/blog/feed
  - /api/v1/blog/sitemap.xml
---

# Marketing -- publish a blog post end-to-end

## What this is for

How to write, schedule, publish, edit, and unpublish posts on the
{{library_name}} public blog at [/blog](/blog) -- from the staff
admin at [/staff/blog](/staff/blog).

## When you'd use it

- Writing a program recap, staff pick, or director's update.
- Scheduling a post to go live during a campaign window.
- Editing a post after it has been published (typo, broken link, new info).
- Pulling a post offline (unpublish) without deleting it.

If you have never used the staff side before, do the admin orientation first.
You need a staff account with permission to manage the blog (the role is
checked server-side; if you can load [/staff/blog](/staff/blog) without a
403, you can publish).

## House voice -- read this before you draft

The {{library_name}} blog speaks as a **constructive practitioner**, not a
critic and never as clickbait. Concretely:

- Write as someone doing the work, sharing what we tried and what we
  learned. "Here is what worked for our story-time crowd this fall"
  beats "5 mistakes libraries make with story time".
- Lead with the reader's situation, not our cleverness.
- No outrage framing, no "you won't believe", no doom. If a thing in
  librarianship is broken, name it plainly, then say what we are
  doing about it.
- Plain language. Define acronyms on first use. Assume the reader
  has not been to library school.
- Cite sources by linking, not by name-dropping.
- It is okay to be warm and a little funny. It is not okay to punch down
  at patrons, peers, or other libraries.

When in doubt, ask: would a patron forward this to a friend without
feeling embarrassed? If not, soften it.

## The blog at a glance

- Public reader URL: [/blog](/blog) (list) and `/blog/<slug>` (one post).
- Staff admin: [/staff/blog](/staff/blog).
- RSS / Atom feed for patrons and aggregators: `/api/v1/blog/feed`
  (linked from the homepage `<link rel="alternate">`).
- Sitemap (for search engines): `/api/v1/blog/sitemap.xml`.
- Posts have three states: **draft**, **scheduled**, **published**.
- There are no categories. Organization is by **tags** and optional
  **series** (e.g. "Director's notes", "Local history").
- There is no patron comment system. Discussion happens in person, at
  programs, or by email -- by design.

## How to create a new post

### What this is for

Drafting a new article and getting it ready to publish or schedule.

### When you'd use it

- Any time you have something to publish. Drafts are free; create one
  the moment you have a working title, even if the body is empty.

### Steps

1. Go to [/staff/blog](/staff/blog) and click **New Post**. You will land
   on [/staff/blog/new](/staff/blog/new).
2. Fill in the fields, top to bottom:
   - **Title** (required). The headline patrons see on the list page
     and in the browser tab.
   - **Slug** (required, auto-suggested from the title). This is the
     URL: `/blog/<slug>`. Keep it short, lowercase, hyphenated. Once a
     post is published and shared, do not change the slug -- you will
     break every existing link.
   - **TLDR** (optional but recommended). One or two sentences shown
     above the post. Also used as the excerpt on the list page when
     present. This is the "if you read nothing else" summary.
   - **Meta description** (optional but recommended for SEO). One to
     two sentences shown in Google results and social-card previews.
     Aim for 140-160 characters. If left blank, search engines will
     guess from the body, usually badly.
   - **Featured image** (optional). Paste a URL to an uploaded image.
     This is the hero image at the top of the post and the social
     card image when the link is shared. Use a real photo or
     illustration with descriptive alt text. Avoid stock-photo cliches.
   - **Body** -- the TipTap rich-text editor (see next section).
   - **Tags** -- type a tag and press Enter, or pick from the
     autocomplete suggestions of existing tags. Reuse existing tags
     where possible so the tag pages stay useful.
   - **Series name** and **series order** (optional). Use these when
     the post is part of a numbered run ("Local History #3"). Series
     names are case-sensitive and exact-match, so spell consistently.
3. Click **Save Draft** to save without publishing. You can come back
   any time.

### What you should see

The post shows up in [/staff/blog](/staff/blog) with a **Draft** badge.
It does not appear at [/blog](/blog) yet. It is not in the RSS feed yet.

## The body editor (TipTap)

The body field is a rich-text editor based on TipTap. It supports:

- Headings (H2, H3 -- the post title is H1, do not add another).
- Bold, italic, strikethrough, inline code.
- Bulleted and numbered lists.
- Blockquotes.
- Links (toolbar: link icon; opens in a new tab by default).
- Images (toolbar: image icon, or drag-and-drop, or paste). Image
  uploads are capped at **5 MB**. You will be prompted for **alt text**
  on every upload -- write a real description, not the filename.
  Alt text is not optional for accessibility (WCAG 1.1.1).
- Callouts (info, warning, tip).

What it does **not** support: tables, embedded video players, raw
HTML. If you need a YouTube link, paste the URL as a regular link --
do not try to embed.

### Editor quirks worth knowing

- Pasting from Google Docs or Word can carry hidden formatting. If
  spacing looks off, select the offending block and use the
  "clear formatting" path (delete and retype is the reliable fix).
- Images are uploaded the moment you drop them in, even if you never
  save the post. They live in the blog media store; orphans can be
  cleaned up later from the media list.
- Read time is calculated from the body word count when you save
  (~238 words per minute). You do not need to set it.

## Drafts, scheduled, published -- what each means

| State | At /blog? | In RSS feed? | In sitemap? | Who can see it |
|-------|-----------|--------------|-------------|----------------|
| Draft | No | No | No | Staff only, via [/staff/blog](/staff/blog) or a preview link |
| Scheduled | No (until the scheduled time passes) | No (until live) | No (until live) | Staff + anyone with the preview link |
| Published | Yes | Yes | Yes | Anyone on the public internet |

Preview links use the slug at `/blog/posts/preview/<slug>` and let you
share an unpublished draft with a colleague or the director before it
goes live. The preview URL is unlisted but not authenticated -- treat
it like a Google Doc "anyone with the link" share.

## How to publish a post

### Right now

From the post edit page, click **Publish**. The post goes live
immediately at `/blog/<slug>`, joins the RSS feed, and gets a
`published_at` timestamp.

From the list at [/staff/blog](/staff/blog), you can also publish a
draft in place: tick the row checkbox and use **Bulk publish** -- this
is the same as clicking Publish on each post.

### At a scheduled time

1. Open the post in the edit view.
2. Use **Schedule** and pick a date and time. The picker uses your
   browser's local time; the server stores it in UTC.
3. Save. The post status becomes **Scheduled** and the row shows the
   scheduled time.
4. At the scheduled time, the post flips to **Published**
   automatically. You do not need to do anything else.

If you need to change the time, edit the post and pick a new schedule.
If you need to send it out now, click **Publish** -- that overrides
the schedule.

## How to edit a published post

You can edit any field on a published post and save. The change is
live immediately. The `published_at` timestamp does not change.

**Revision history** is kept automatically. From the edit page:

- Open **Version history** to see prior versions.
- Each version shows the title, TLDR, and timestamp.
- Click **Restore** on a version to make it the current draft of the
  post. Restoring does not publish -- you still need to click Publish
  (or it stays as the live version if the post was already published
  and you are mid-edit).

If you fix a typo, just save. If you change the *meaning* of a published
post (correcting a fact, retracting a claim), add a short note at the
bottom: "**Update YYYY-MM-DD:** ...". Trust costs more to rebuild than
to protect.

## How to pull a post offline (unpublish)

When you need a post off the public site without deleting it (legal
request, factual error you cannot fix quickly, retraction):

1. From [/staff/blog](/staff/blog) or the post edit view, click
   **Unpublish**.
2. The post returns to **Draft**. It disappears from [/blog](/blog),
   the RSS feed, and the sitemap on the next request.
3. The slug is preserved, so if you republish later, the URL stays
   the same. Direct links from outside (Google cache, social shares)
   will 404 until you republish.

**Unpublish, do not delete**, unless you are sure no one will ever
need to see it again. Delete is permanent.

## SEO basics

You do not need to be an SEO expert. Three habits cover most of it:

1. **Write a good title and TLDR.** These are what Google and
   social-card previews show. They are also what makes a human click.
2. **Set the meta description.** 140-160 characters, written for a
   person who has not read the post yet.
3. **Use a featured image.** Open Graph / Twitter cards use it; posts
   without one look bad when shared.

The blog handles the rest automatically: canonical URL is the
`/blog/<slug>` page, sitemap pings out as posts publish, structured
data for `BlogPosting` is generated server-side.

## Comments and moderation

There is no on-site comment system. This is intentional -- moderation
load on small library teams is real, and a public comment thread tends
to attract a few loud voices rather than the broader patron base.

If you want patron feedback on a post, suggest emailing
{{contact_email}} or replying via the library's social channels.

## Feeds and discoverability

- **RSS / Atom feed**: `/api/v1/blog/feed`. Linked from the homepage
  `<link rel="alternate">` so feed readers auto-discover it. Patrons
  who use NetNewsWire, Feedly, Inoreader, etc. can subscribe.
- **Sitemap**: `/api/v1/blog/sitemap.xml`. Crawled by search engines.
- **Series pages**: `/blog/series/<series_name>` lists every post in
  a series in order.
- **Tag pages**: tagging a post automatically puts it on the tag's
  page. Tag pages are not heavily promoted but are crawlable.

## Bulk operations

From [/staff/blog](/staff/blog) you can multi-select posts and:

- **Bulk publish** -- promote selected drafts to published. Use this
  when you have prepared a backlog of posts and want a batch live.
- **Bulk delete** -- permanent. There is a confirm step. Use only for
  spam-test posts and obvious junk; for everything else, unpublish.

## Sharing analytics

The blog tracks view counts per post (deduplicated by hashed IP+UA).
View counts and aggregate analytics live at
`/api/v1/blog/analytics`. Use these to learn what resonates, not as
a score to chase -- a slow-burn post on a local-history topic can
matter more than a viral one.

## Common problems

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| "Slug already exists" on save | Another post (incl. trashed/draft) has the same slug | Change the slug; you cannot reuse |
| Image upload fails | File over 5 MB, or non-image MIME type | Resize / re-export, or convert to JPG / PNG / WebP |
| Scheduled post did not go live | Server clock drift, or post was edited and lost the schedule | Open the post, check status -- republish or re-schedule |
| Post is missing from RSS feed | Still in draft, or feed reader is cached | Confirm status = Published; the feed updates on each request |
| Edit shows a different version than /blog | Browser cached old HTML | Hard refresh (Cmd-Shift-R / Ctrl-Shift-R) |

## See also

- [Admin guide -- Blog](../../../admin-guide/blog.md) -- bulk actions,
  feature gating, moderation queue from the admin angle.
- [Marketing admin-guide page](../../../admin-guide/marketing.md) --
  campaigns, outreach, and how the blog fits into a marketing push.
