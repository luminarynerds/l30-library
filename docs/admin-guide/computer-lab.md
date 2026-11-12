# Computer Lab

Sidebar "Tech Services" group. Requires `tech_services_enabled`. The
computer-lab module is the operational surface for L30's public PCs:
session lifecycle, time limits, reservations, guest passes, the floor
view, the lab-map editor, and the per-station inventory. Print release
lives in its own page (`/staff/print`, see [Front Desk](front-desk.md))
but is referenced here because most lab interventions involve a stuck
print job.

Three pages do the work:

- `/staff/computers` — Floor view (live operations). Requires
  `tech_services_enabled`.
- `/staff/admin/computers` — Inventory + lab-map editor (configuration).
- `/computers` — Patron-facing reservation + active-session view. Mirrors
  what patrons see at home or on a kiosk browser.

---

## 1. Overview

The computer-lab module covers:

- **Stations** — the inventory of physical PCs (name, number, type,
  branch, location label, OS, capabilities, max session minutes,
  status).
- **Sessions** — a patron's active use of one station. Has a start
  time, a calculated end time, and an end reason.
- **Reservations** — future-dated bookings. Convert into a session at
  check-in.
- **Guest passes** — temporary credentials for non-cardholders (visiting
  patrons, drop-ins). Bypass the card lookup.
- **Waitlist** — when a station type is fully booked, patrons can hold
  a position in line.
- **Extensions** — patrons can request more time; staff approve or
  deny.
- **Lab map** — visual floor-plan editor. Stations are dragged into
  position; the same layout renders for patrons on `/computers` and for
  staff on the Floor view.
- **Stats** — per-station and system-wide usage (sessions, minutes,
  by hour, by day, by type).

Print jobs are not owned by this module. They live at `/staff/print`
and reference the station via `has_print_release` on the inventory
record. See section 4.

---

## 2. The lab map (`/staff/admin/computers`, "Arrange" tab)

Backed by `AdminComputerMapArranger` and the `computer-lab-map-api`.

Two views share this page:

- **List** — table-style inventory of every station. Add, edit,
  delete, change status.
- **Arrange** — drag-and-drop floor plan editor.

### Station fields

When you add or edit a station, these are the fields that drive
everything downstream:

- `name` (required) — display name, e.g. `PC-A01`. Shown on the floor
  view, on patron reservation cards, and on the lab map.
- `computer_number` — short label, e.g. `A01`. Used on signage and on
  the lab map node.
- `computer_type` — one of `adult`, `teen`, `kids`, `accessible`.
  Drives which patron group can reserve it and which type-filter it
  shows under. Accessible stations get a separate icon on the patron
  map.
- `location` (required) — human-readable area label, e.g.
  "Adult Services - Main Floor". Shown under the station name.
- `os_type` — free-text, e.g. `Windows 11`. Shown as a chip.
- `branch_id` (required) — which branch this station physically lives
  in. Filters the floor view and the patron-side map.
- `has_internet` — boolean. Patrons see a "Net" chip; affects which
  filters match.
- `has_print_release` — boolean. Patrons see a "Print" chip. If false,
  the station does NOT appear in the print-release picker on
  `/staff/print`.
- `max_session_minutes` — hard cap on a single session (15-480).
  Default policy is 60.
- `status` — `available`, `in_use`, `maintenance`, `offline`,
  `reserved`. Set manually here, or driven by sessions/reservations
  in real life.

### Editing the layout

The Arrange tab is a positional editor. Drag each station node onto
the floor diagram; the saved x/y/branch coordinates are what
`/computers` and `/staff/computers` both render. There is no "publish"
step — saves are live the moment you confirm.

Workflow for a layout change:

1. Open `/staff/admin/computers` and switch to the "Arrange" tab.
2. Drag a station to its new position. Stations grouped in clusters
   should sit within a few pixels of each other so the patron-side
   map reads cleanly.
3. Save. Reload `/computers` in a separate tab to confirm the patron
   view looks right.
4. If a station has moved branches, edit it in the List tab first to
   update `branch_id`, then re-arrange.

### Removing a station

Use the trash icon in the List tab. Stations are marked `is_active =
false`, not hard-deleted; they keep their session history and stop
appearing in patron pickers. To re-add, edit the existing record
rather than creating a duplicate `computer_number`.

---

## 3. Sessions (`/staff/computers`, "Floor view" tab)

Backed by `GET /computers/staff/floor-view` (polled every 30s when no
WebSocket, every 60s when a live socket is connected — the page
auto-detects).

The floor view shows every station as a card, color-coded by urgency:

- **Normal** — available or comfortably mid-session.
- **Warning** — session is approaching the time cap.
- **Overtime** — session has run past the cap.
- **Pending extension** — patron requested more time; needs your
  approve/deny.

### Starting a session

Most sessions start one of three ways:

1. **Patron self-service** — they reserved on `/computers` and check
   in at the time slot. No staff action needed.
2. **Reservation check-in at the desk** — pull up the patron's
   reservation under the "Reservations" tab and click "Check in".
   Walk-in check-in is also supported via the
   `/reservations/{id}/check-in/walk-in` endpoint when the patron is
   physically here but didn't reserve in advance.
3. **Guest pass** — for non-cardholders. Under the "Guest passes" tab,
   create a pass; the patron uses the pass code at the kiosk login
   page.

### Ending a session

Click the station card on the floor view, then "End session." You
will be asked for an end reason:

- `time_up` — normal expiry.
- `patron_left` — they walked away before the timer ran out.
- `staff_ended` — you ended it for any operational reason.
- `violation` — policy violation (note required).
- `technical_issue` — station failed mid-session.

Notes are recorded against the session and feed the stats page.

### Extending a session

Two paths:

- Patron requests an extension from `/computers`. The card moves into
  the "pending extension" tier. Click "Approve" or "Deny."
- Staff grant time directly from the session card without a request.
  This is the right call when the lab is empty and a patron is
  obviously working on something legitimate.

Extensions are capped by the system extension policy; the UI will
refuse silently if the cap is hit.

### Blocking a station

Two ways to take a station out of service:

- **Soft**: from the floor view card, "Mark maintenance." Sessions
  end, station shows yellow, no new reservations accept.
- **Hard**: from `/staff/admin/computers` (List tab), set status to
  `offline`. Use this when the station is being moved, replaced, or
  is out for repair longer than a shift.

### Bulk actions

The floor view supports multi-select. Use it for end-of-day closeout:

1. Click "Select all visible," or check individual cards.
2. Choose a bulk action: end all sessions, mark all maintenance, or
   release all reservations.
3. Confirm with a single reason + optional note. The note applies to
   every affected session.

Backed by `POST /computers/staff/bulk`. Audit-logged.

---

## 4. Print jobs

The print queue itself lives at `/staff/print`, not here. This guide
covers only the lab-side touchpoints.

A station only accepts print release when its inventory record has
`has_print_release = true`. If a patron complains "my print isn't
showing up," check that first.

Common interventions:

1. **Release a stuck job** — on `/staff/print`, find the job by
   patron name or release code; click "Release" to push it to the
   printer. The patron-facing how-to is at `/guides/check-print-jobs`
   ([CheckPrintJobsGuide](../../../frontend/src/pages/guides/CheckPrintJobsGuide.tsx)).
2. **Refund a charge** — if the print failed (jam, paper out,
   misprint), refund from the patron's account page, not from the
   print queue. The print queue records the charge; circulation
   records the refund.
3. **Patron printed from their laptop** — that's the wireless flow,
   documented at `/guides/wireless-printing`
   ([WirelessPrintingGuide](../../../frontend/src/pages/guides/WirelessPrintingGuide.tsx)).
   They submit to the print server, get a release code, walk to any
   `has_print_release` station, and release.
4. **Job sitting in queue for >30 min** — the server may have lost
   the upstream connection. Walk to the printer, check the panel,
   then on `/staff/print` cancel + ask the patron to resubmit.

---

## 5. Reservations

Two flows exist in the codebase:

- **Time-slot reservation** (`POST /computers/reservations`) — patron
  picks a future start time and a duration. Standard library model.
- **Booking reservation** (`POST /computers/reservations/book`) — a
  simpler "grab the next available slot for the next N minutes"
  flow, used by the booking calendar on `/computers`.

Both produce the same `Reservation` record under the hood. Patrons see
their upcoming and active reservations on `/computers`; staff see all
of them on the "Reservations" tab of `/staff/computers`.

### Patron-side workflow

1. Patron visits `/computers`.
2. Picks a station card (or a calendar slot) and confirms duration.
3. Reservation is created; patron sees a `ReservationCard` with
   check-in instructions.
4. At the start time, patron clicks "Check in" — converts to an
   active session and moves to the "Session" tab.

### Staff override

From `/staff/computers` "Reservations" tab:

- Filter by status (`pending`, `active`, `cancelled`, `no_show`).
- Cancel on behalf of a patron (`DELETE
  /computers/reservations/{id}`).
- Walk-in check-in (`POST
  /computers/reservations/{id}/check-in/walk-in`) when the patron
  arrives without their card.
- End a reservation's session early (`POST
  /computers/staff/reservations/{id}/end-session`) with a reason
  category and notes.
- Re-open a recently-ended session (`POST
  /computers/staff/sessions/{id}/reopen`) when you ended it by
  mistake. Reopen is time-bounded — don't rely on it more than a
  minute or two after end.

### Waitlist

When a station type is fully booked, patrons can join a waitlist
(`POST /computers/waitlist/join`). Position is visible to them at
`GET /computers/waitlist/position`. Promotion is automatic when a
slot frees up; you don't need to manually advance the queue.

---

## 6. Hardware troubleshooting basics

The L30 module assumes the physical station and the network are
working. When something physical breaks, your job is to triage
fast and decide whether L30 needs to know about it.

Common scenarios:

1. **Out of paper** — refill the printer. No L30 action needed. If
   patrons have queued jobs they paid for, release them after the
   refill and confirm with each patron.
2. **Paper jam** — clear the jam per the printer's panel
   instructions. If the patron's job was destroyed mid-print, refund
   the charge from their account (see section 4).
3. **Station offline / won't boot** — set the station to `offline`
   in `/staff/admin/computers` so it stops appearing on the patron
   map. Open a ticket with IT. Don't leave it `available` "for now"
   — patrons will reserve it and be stranded.
4. **Mouse / keyboard dead** — swap from spares before doing anything
   in L30. Only mark `maintenance` if the swap doesn't fix it.
5. **Session won't end on the station screen but L30 says it's free**
   — the lockdown client lost contact with L30. End the session in
   L30 to force-clear, then ask the patron to log back in. If it
   happens twice on the same station in a shift, mark
   `maintenance` and call IT.
6. **Patron logged in but the timer didn't start** — refresh the
   floor view; the session probably exists but the WebSocket dropped.
   If still missing after refresh, end any phantom session on that
   station and have them log in again.

---

## 7. Reports

Two report surfaces:

- **Per-station stats** — `GET /computers/computers/{id}/stats`. Not
  surfaced as its own page; called from the floor view when you
  click into a station's history.
- **System stats** — `GET /computers/stats/system`. Rendered on the
  "Stats" tab of `/staff/computers`. Default window 7 days,
  selectable.

What the system stats answer:

- **Total sessions and minutes** in the window.
- **Sessions by station type** (adult / teen / kids / accessible).
  Use to right-size the inventory — if teen stations are 90%
  utilized while adult sits at 30%, reconfigure or rebalance.
- **Time-of-day patterns** — sessions by hour. Drives staffing,
  reservation slot length, and quiet-hours decisions.
- **Top stations by use** — which physical PCs need keyboard/mouse
  replacement first.
- **End reasons** — high `technical_issue` rates on one station are
  a hardware flag, not a patron-behavior flag.

For board-level reporting (annual computer-lab usage), pull from
`/staff/reports` rather than from this page — the Reports module
aggregates across modules.

---

## 8. When to call IT

L30 owns: session state, reservations, the lab map, station inventory
metadata, the print queue, the patron-facing reservation UI.

L30 does NOT own: the physical PC, the lockdown client (Userful,
Deep Freeze, etc.), the print server itself, the network, the
projector, the printer hardware, the cardreader at the kiosk.

Call IT when:

- A station won't boot, can't reach the network, or the lockdown
  client crashes repeatedly.
- The print server (not the L30 print queue) is unreachable. Test:
  can you print a test page from the print server's web UI? If no,
  it's IT. If yes but L30 won't release, it's L30.
- A station consistently loses its session mid-use (lockdown client
  losing contact with L30 is usually IT-side configuration).
- Hardware: monitor, keyboard, mouse, printer, kiosk reader.

Handle in L30 first when:

- Reservations missing or duplicated → check `/staff/computers`
  Reservations tab; cancel/recreate as needed.
- Print job stuck in queue but printer is fine → cancel + resubmit
  from `/staff/print`.
- Station shows `in_use` but is empty → end the phantom session
  from the floor view.
- Patron can't log in but has a valid card → check guest-pass flow
  and that the station has `has_print_release` / `has_internet`
  set correctly for what they're trying to do.

A good rule: if the symptom changes when you click something in L30,
it's an L30 problem. If the physical box is unresponsive and L30
already reflects that accurately, it's an IT problem.
