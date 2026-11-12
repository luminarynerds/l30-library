# L30 Admin Guide

Short orientation notes for every admin surface in L30. Aimed at staff and
directors who have landed on a page and need to answer three questions fast:

1. **What is this for?**
2. **When do I use it?**
3. **What should I be careful about?**

This is a skeleton, not a comprehensive manual. Each page gets a paragraph,
not a tutorial. Iterate over time as workflows shake out.

## How this guide is organized

Files match the sidebar groups in `staffSidebarMenu.ts`:

| File | Sidebar group |
|------|---------------|
| [admin-settings.md](admin-settings.md) | Admin (system, AI, compliance, computers, feature flags, etc.) |
| [reports.md](reports.md) | Reports (report hub, financial, annual reports, traffic) |
| [marketing.md](marketing.md) | Marketing (campaigns, AI hub, email, event marketing, beta) |
| [library.md](library.md) | Library (events, programs, services, training, computers) |
| [collection.md](collection.md) | Collection (cataloging, MARC, inventory, acquisitions, EDI) |
| [board.md](board.md) | Board portal (members, meetings, documents, public comments) |
| [front-desk.md](front-desk.md) | Front Desk (circulation, fast checkout, holds shelf, transit) |

Pages outside the sidebar (e.g. deep-nested admin tools accessed only via
links from a hub) are documented under whichever group they thematically
belong to.

## Conventions

- Each entry: H3 with the page H1 + the route path in backticks.
- One paragraph orientation (3-6 sentences).
- `**Status:** stub` marks placeholder/empty pages.
- `**Internal tool**` marks dev-only utilities (e.g. RFID Simulator).
- `See also:` lines cross-reference related pages.

## Contributing

When you change a major workflow, update the relevant page paragraph. When
you add a new admin route, add an entry to the right file in alphabetical
order within its section. Keep it short — if you need more than 6 sentences,
the page itself probably needs better in-app help, not a longer manual entry.
