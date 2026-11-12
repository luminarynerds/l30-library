<!--
  SPDX-FileCopyrightText: 2026 Luminary Nerds
  SPDX-License-Identifier: AGPL-3.0-or-later
-->
# Contributing to L30

Thanks for your interest. This document covers how to propose changes -- branch naming, commit format, test expectations, and PR conventions.

For local-dev setup (Docker, env vars, ports), see [DEVELOPER_SETUP.md](DEVELOPER_SETUP.md).

## Quick start

```sh
# Fork on GitHub, then:
git clone git@github.com:YOUR_USER/l30-library.git
cd l30-library
git checkout -b feat/your-feature-name

# Make changes, run tests, then:
git push -u origin feat/your-feature-name
gh pr create --base main
```

## Branch naming

Prefix branches by intent:

| Prefix       | Use for                                |
|--------------|----------------------------------------|
| `feat/`      | New user-visible features              |
| `fix/`       | Bug fixes                              |
| `refactor/`  | Internal restructuring, no behavior change |
| `test/`      | Test-only changes                      |
| `chore/`     | Build, deps, tooling, hygiene          |
| `docs/`      | Documentation only                     |
| `perf/`      | Performance work                       |

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/) format:

```
feat(catalog): add subject filter to search results
fix(auth): reject expired tokens at refresh
refactor(billing): extract Stripe client to its own module
docs: add deployment troubleshooting section
chore(deps): bump fastapi to 0.110
```

Subject line under 70 chars. Body explains WHY, not WHAT. Reference issues with `Closes #N` or `Refs #N` when applicable.

## Tests

**Backend** (`cd backend && pytest`):
- Use Python 3.12 and the test dependencies listed in the backend GitHub Actions workflows.
- Tests need isolated PostgreSQL and Redis services. See [DEVELOPER_SETUP.md](DEVELOPER_SETUP.md).
- Use synthetic data and `TEST_REQUIRE_POSTGRES=1`; never use a production database.

**Frontend** (`cd frontend && npm test`):
- `npm run typecheck` for TypeScript validation.
- `npm test` runs Vitest unit/component tests.

Pull requests run the configured CI checks. The full source-install smoke
workflow is manual because it builds the whole stack; run it before a release.
A workflow file being present does not establish that its latest run passed.

## Pull requests

- Open PRs against `main`.
- Squash-merge on green. PR title becomes the squash commit message -- write it like a conventional-commit subject.
- One concern per PR. If a PR grows beyond ~500 LOC, consider splitting.
- Include a brief "what changed and why" in the PR body. Test plan as a checklist if non-trivial.

## Code style

- **No defensive overcoding**: trust internal calls. Validate only at system boundaries (user input, external APIs).
- **No comments for the obvious**: well-named identifiers > restatement comments. Comment WHY when non-obvious.
- **Keep repository docs current and durable**: document how the system works or how to use it. Do not commit task handoffs, implementation summaries, AI transcripts, or one-off status reports.
- **Match surrounding patterns**: search the codebase for prior art before introducing new abstractions.
- **No emojis in source** unless explicitly requested.
- **Prefer editing existing files** over creating new ones.

## Issues

Open issues for bugs, feature requests, and questions. For security vulnerabilities, see [SECURITY.md](SECURITY.md) instead -- do **not** file public issues.

## License

By contributing you agree your work will be licensed under [AGPL-3.0-or-later](LICENSE).
