<!--
  SPDX-FileCopyrightText: 2026 Luminary Nerds
  SPDX-License-Identifier: AGPL-3.0-or-later
-->
# Security Policy

L30 handles patron records and library operational data. We take security reports seriously.

## Supported versions

L30 is under active development on `main`. We support the latest tagged release and `main` for security fixes. Older tags receive fixes only for critical vulnerabilities.

| Version | Supported |
|---------|-----------|
| `main`  | Yes       |
| Latest tagged release | Yes |
| Older releases | Critical only |

## Reporting a vulnerability

**Do not file public GitHub issues for security vulnerabilities.**

Use [GitHub's private vulnerability reporting](https://github.com/luminarynerds/l30-library/security/advisories/new) when available. Reports go to this repository's maintainers privately. Maintainers must enable this feature when the repository is made public; it is not available for this private release candidate.

If you cannot use GitHub private reporting, file a public issue titled "Request for private security contact" and we will reach out.

In your report, please include:

- **What**: a description of the vulnerability.
- **Where**: file path / endpoint / version / configuration.
- **Impact**: what an attacker can do (data exposure, privilege escalation, denial of service, etc.).
- **Reproduction**: minimal steps to reproduce, or a proof of concept.
- **Suggested fix**: optional, if you have one.

## What to expect

- **Acknowledgement**: within 5 business days.
- **Triage**: initial severity assessment within 10 business days.
- **Fix**: timeline depends on severity. Critical / high: target patched release within 30 days. Medium / low: scheduled into a normal release cycle.
- **Disclosure**: we coordinate public disclosure with you. Credit is offered for the report unless you prefer anonymity.

## Scope

**In scope:**

- L30 backend (`backend/`) and frontend (`frontend/`) source.
- Default configuration shipped in this repository (`docker-compose.yml`, `nginx/`, `.env.example`).
- Authentication, authorization, session management, data handling.
- Patron PII handling, encryption-at-rest, logging hygiene.

**Out of scope:**

- Third-party services L30 integrates with (Cloudflare, Resend, Stripe, etc.) -- report to the vendor.
- Self-hosted deployments with non-default configuration -- we'll advise but the deployer is responsible.
- Issues that require local physical access to the server or an authenticated admin account performing intended-but-destructive actions.
- Social engineering or phishing against library staff.

## Best practices for deployers

If you self-host L30, the following are your responsibility:

- Keep dependencies current (Dependabot is configured; review and merge alerts).
- Run behind a reverse proxy with TLS. Don't expose the backend directly.
- Set strong values for `SECRET_KEY`, `DATABASE_URL` credentials, and `PII_ENCRYPTION_KEY`. Never commit `.env` files.
- Enable rate limiting (`RATE_LIMIT_ENABLED=true`, `RATE_LIMIT_OBSERVE_ONLY=false`).
- Restrict backend ingress to your reverse proxy's IPs.
- Configure DMARC / SPF / DKIM for your sending domain.

See [SELF_HOSTING.md](SELF_HOSTING.md) for deployment guidance.

## License

This policy is licensed under [AGPL-3.0-or-later](LICENSE) along with the rest of the project.
