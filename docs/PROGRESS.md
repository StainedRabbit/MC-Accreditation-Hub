# Progress

## Current slice

Cycle Lifecycle and Recovery checkpoint: scoped close/reopen controls, account password workflows, and lifecycle audit history.

## Completed work

- React + Vite frontend and Django REST Framework backend run against PostgreSQL.
- Session login/logout and CSRF protection; scoped Administrator, Coordinator, Reviewer, Custodian, and Viewer assignments.
- Active/closed cycles, areas, requirements, mandatory evidence items, immutable document versions, mappings, submissions, decisions, and audit events.
- Protected file validation and attachment download. Supported files are PDF, DOCX, XLSX, PNG, and JPEG up to 25 MB.
- Figma-style login, authenticated shell, dashboard, areas, requirements/detail, repository/version history, review queue, and audit view.
- Fictional demo seed command and local-start script. No real institutional evidence is seeded.
- `RequirementCertification` is append-only. It records a Coordinator's rationale-backed `complete` or `reopened` decision without changing existing evidence, version, review, or audit records.
- Scoped `GET`/`POST /api/requirements/{id}/certifications/` endpoints and revised compliance statuses/counts are available. Only Coordinators in the requirement's scope can post certification actions.
- The React requirement detail now clearly shows Ready for Completion Review, immutable certification history, and Coordinator-only Complete/Reopen controls. Both actions require a rationale and use the existing API.
- Dashboard and compliance data refresh after a certification action. The dashboard now distinguishes Coordinator-certified requirements from items awaiting completion review.
- The Playwright workflow now covers approved evidence becoming ready, Coordinator completion, dashboard count change, reopening, and the reversed count change. It also confirms a Reviewer cannot see certification controls.
- Scoped Search returns only authorized requirement and document metadata. Compliance Reports reuse the same scoped status calculation as the dashboard, support area/status filters, print cleanly, and export formula-safe CSV.
- Audit Trail remains user-facing and now supports server-side scoped text/action filters for future pagination and UI controls.
- Scoped Coordinators can close an active cycle or reopen a closed cycle from the Dashboard. Both transitions require a rationale, are audited per area, and all normal write endpoints continue to enforce active-cycle locking.
- Signed-in users can change their password from Account security without losing their current session. Recovery email is deliberately disabled until SMTP, sender, and public application URL settings are supplied; the login flow directs users to administrator-assisted recovery when it is unavailable.

## Verified behavior

- `python backend/manage.py test hub --noinput`: 24 PostgreSQL-backed tests passed on 2026-09-09.
- `python backend/manage.py check` and `python backend/manage.py makemigrations --check --dry-run`: passed on 2026-09-09.
- `npm.cmd run build --prefix frontend`: passed on 2026-09-09.
- `npm.cmd run test:e2e --prefix frontend` with the local Playwright Chromium executable: 2 tests passed on 2026-09-09. The PostgreSQL-backed browser flow created a fictional requirement, uploaded/revised/reapproved evidence, reached Ready for Completion Review, marked it complete with a rationale, verified dashboard counts, reopened it with a rationale, and verified the counts reverted.
- Focused PostgreSQL tests for Search/Reports passed on 2026-09-09: scoped search, report totals, CSV export, audit filtering, and spreadsheet-formula neutralization.
- `npm.cmd run test:e2e --prefix frontend` with the local Playwright Chromium executable: 3 tests passed on 2026-09-09, including scoped Search and the printable Compliance Report/export controls.
- Tests cover CSRF/session handling, scoped lists and downloads, self-review prevention, stale/competing review decisions, invalid uploads, expiry, exclusions, closed cycles, historical immutability, Coordinator-only certification, reopening, rationale validation, and the revised compliance calculation.
- Focused Slice 9 PostgreSQL tests passed on 2026-09-09: scoped close/reopen transitions and audit reasons, blocked writes while closed, password-change validation/session continuity, disabled recovery messaging, and configured one-time password recovery.
- `python backend/manage.py check`, `python backend/manage.py makemigrations --check --dry-run`, and `npm.cmd run build --prefix frontend` passed on 2026-09-09.

## Known incomplete or broken work

- The app permits controlled cross-area mapping, while the older plan defers cross-area sharing. That policy remains unresolved and is outside the current certification change.
- Pagination, two-factor authentication, notifications, full cycle administration UI, deployment/backup restoration, and malware scanning remain outside this checkpoint.
- The actual Figma site was not available for inspection; login and supplied screenshots guided the current visual design.

## Next exact task

Implement Slice 10 only: deployment configuration, backup/restore procedure, release verification, and thesis evaluation materials. Do not begin deferred features.

## Important decisions

- Django owns permission checks, workflow transitions, compliance calculations, and protected download authorization.
- Reviews attach to a submitted document version and never transfer to a later version.
- A reviewer cannot decide on their own upload or submission.
- Approval alone never completes a requirement. Compliance counts only the latest effective Coordinator `complete` certification; a later `reopened` certification removes it from the numerator while preserving history.
- A recorded completion remains effective until a Coordinator reopens it; later uploads, submissions, or evidence expiry do not silently alter the certification.
- React renders certification controls only when the backend returns `can_complete` or `can_reopen`; the backend remains the source of authorization. API validation, forbidden, and failed-request responses are shown in the action dialog without discarding the entered screen state.
- CSV exports use `download=csv` rather than DRF's reserved `format` query parameter. Cells starting with `=`, `+`, `-`, `@`, tab, or carriage return receive a leading apostrophe to prevent spreadsheet formula execution.
- The existing local PostgreSQL development cluster uses port 55432 and is isolated under ignored `.local/` data.
- Demo data is explicitly labeled fictional and uses generated local-only credentials.
