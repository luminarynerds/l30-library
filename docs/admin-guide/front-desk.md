# Front Desk

Sidebar "Front Desk" group. Requires `front_desk_enabled`. These are the
high-frequency operational pages used by staff at the service desk. Most
are not "admin" in the configuration sense — they're the daily-driver
operational surfaces — but they're included here because they're the
landing experience for most front-line staff.

---

### Front Desk Hub (`/staff/front-desk-hub`)
Landing page. Tile-grid of circulation, fast checkout, patrons, holds
shelf, transit. First thing a desk-shift staffer should see.

### Circulation (`/staff/circulation`)
Full circulation workspace: checkout, check-in, renew, place hold,
collect fine, manage patron account. The default desk view.

### Fast Checkout (`/staff/checkout/streamlined`)
Streamlined checkout flow optimized for high-volume single-patron
transactions (e.g. a big bag of picture books). Skips some of the
default circulation UI chrome.

### Patrons (`/staff/patrons`)
Patron directory: search, view account, edit details, see history,
manage notes. Note the alternate `/staff/card-applications` for new
card applications in progress.

### Card Applications (`/staff/card-applications`)
New patron card applications: triage, approve, deny, request more info.

### Holds Shelf (`/staff/holds/shelf`)
The pickup shelf: see what's waiting, mark as picked up, expire stale
holds, surface stranded holds.

### Transit (`/staff/transit`)
Items in transit between branches: outgoing, incoming, late, lost.
Use to chase missing transits before they become "lost".

### Cash Drawer (`/staff/cash-drawer`)
Open/close cash drawer with starting/ending counts. Reconcile against
fines collected. Audit-logged.

### End of Day (`/staff/end-of-day`)
End-of-day closeout: cash reconciliation, drop-box notes, hand-off log
for the next opener.

### End of Shift (`/staff/end-of-shift`)
Mid-day shift hand-off: notes, open issues, in-progress work. Lighter
than End of Day.

### Message Board (`/staff/message-board`)
Internal staff message board for shift-to-shift comms.

### Knowledge Base (`/staff/knowledge-base`)
Staff knowledge base: policies, how-tos, FAQs. Searchable.
Also surfaced in the Help sidebar group.

### Print Management (`/staff/print`)
Public print queue and quota management. Requires `printing_enabled`.

### Panic Alerts (`/staff/panic-alerts`)
Emergency panic alert dashboard. Requires `emergency_services_enabled`.
Visit only during/after an incident; alerts auto-page.

### Medical Emergency (`/staff/medical-emergency`)
Medical emergency response page. Requires `emergency_services_enabled`.
Companion to Panic Alerts for medical-specific incidents.

### Rooms (`/staff/rooms`)
Meeting room reservations: view, book on behalf of patron, cancel,
check-in. Requires `meeting_rooms_enabled`.

### Makerspace (`/staff/makerspace`)
Makerspace equipment and project tracking. Requires
`makerspace_enabled`.

### SIP2 (`/staff/sip2`)
Live SIP2 session monitor for connected self-checkout kiosks.
Requires `sip2_rfid_enabled`. Useful when a kiosk is misbehaving.

### RFID (`/staff/rfid`)
RFID reader status and tag programming console. Pairs with the
RFID Simulator under Admin for testing without hardware.

### Audit Logs (`/staff/audit-logs`)
Browseable audit log for patron-account and circulation actions.
Read-only.

### Streaming (`/staff/streaming`)
Streaming media platform admin: titles, playlists, featured.
Requires `streaming_enabled`. Reports at `/staff/streaming/reports`.

### Downloads (`/staff/downloads`)
Download monitor for digital content delivery: in-flight downloads,
recent completions, failures.

### Positivity Hub (`/staff/positivity`)
Staff wellness/positivity hub: shoutouts, peer recognition.
Requires `staff_wellness_enabled`.

### Shift Swap Board (`/staff/shift-swap`)
Staff-to-staff shift swap requests. Requires `staff_scheduling_enabled`.
