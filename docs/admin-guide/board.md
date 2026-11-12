# Board

Sidebar "Board" group. Requires `board_features_enabled`. Surfaces split
between staff-portal board management and the dedicated board-member
portal at `/board/*`.

---

### Board Hub (`/staff/board-hub`)
Landing page for board-related operations from the staff side.
Tile-grid of members, meetings, documents, public comments, audit.

### Members (`/board/members`)
Board member directory: roles, terms, contact info, committee
assignments. Maintained by admin/director; visible to all board members.

### Meetings (`/board/meetings`)
Meeting schedule, agendas, minutes, recordings. Each meeting record
links to its packet documents.

### Documents (`/board/documents`)
Board document library: policies, financials, packets, historical
minutes. Permissions vary by document.

### Public Comments (`/staff/admin/board/public-comments`)
Manage public comments submitted for board meetings: triage, mark
read-aloud, archive. AdminAuth + `board_features_enabled`.

### Board Management (`/staff/admin/board`)
Admin surface for board-level config: meeting cadence, packet
templates, public comment policy. AdminAuth + `board_features_enabled`.

### Board Audit Log (`/staff/admin/board/audit-log`)
Tamper-resistant governance audit trail. Append-only at the database
level. Director and admin access. Use for compliance review; never
edit (you can't anyway).

### Board Demo (`/staff/board-demo`)
Demo/sandbox board view used for training and walkthroughs.
Requires `board_features_enabled`.

### Strategic Administration (`/staff/admin/strategic`)
Strategic plan management feeding the Board portal. See
[admin-settings.md](admin-settings.md#strategic-administration-staffadminstrategic).

### Board Treasurer Dashboard (`/staff/admin/board-treasurer`)
Comprehensive financial analysis and reporting for the board treasurer.
AdminAuth + `board_features_enabled`. Distinct from the operational
Treasurer Dashboard — this one is built for board-meeting consumption.
See also: [Treasurer Dashboard](admin-settings.md#treasurer-dashboard-staffadmintreasurer).
