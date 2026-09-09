# Progress

## Current slice

Backend completion-certification checkpoint: approved evidence moves a requirement to Ready for Completion Review; an authorized Coordinator separately certifies or reopens completion.

## Completed work

- React + Vite frontend and Django REST Framework backend run against PostgreSQL.
- Session login/logout and CSRF protection; scoped Administrator, Coordinator, Reviewer, Custodian, and Viewer assignments.
- Active/closed cycles, areas, requirements, mandatory evidence items, immutable document versions, mappings, submissions, decisions, and audit events.
- Protected file validation and attachment download. Supported files are PDF, DOCX, XLSX, PNG, and JPEG up to 25 MB.
- Figma-style login, authenticated shell, dashboard, areas, requirements/detail, repository/version history, review queue, and audit view.
- Fictional demo seed command and local-start script. No real institutional evidence is seeded.
- `RequirementCertification` is append-only. It records a Coordinator's rationale-backed `complete` or `reopened` decision without changing existing evidence, version, review, or audit records.
- Scoped `GET`/`POST /api/requirements/{id}/certifications/` endpoints and revised compliance statuses/counts are available. Only Coordinators in the requirement's scope can post certification actions.

## Verified behavior

- `python backend/manage.py test hub --noinput`: 24 PostgreSQL-backed tests passed on 2026-09-09.
- `python backend/manage.py check` and `python backend/manage.py makemigrations --check --dry-run`: passed on 2026-09-09.
- `npm.cmd run build --prefix frontend`: passed on 2026-09-09.
- Previous Playwright desktop/mobile workflow passed before this backend-only change. The frontend has not yet been updated to display or invoke certification actions.
- Tests cover CSRF/session handling, scoped lists and downloads, self-review prevention, stale/competing review decisions, invalid uploads, expiry, exclusions, closed cycles, historical immutability, Coordinator-only certification, reopening, rationale validation, and the revised compliance calculation.

## Known incomplete or broken work

- There is no Git repository in this workspace, so no checkpoint commit can be created here.
- The frontend still lacks the Ready for Completion Review status label/count and Coordinator certification/reopen controls. It therefore cannot yet use the completed backend API.
- The app permits controlled cross-area mapping, while the older plan defers cross-area sharing. That policy remains unresolved and is outside the current certification change.
- Search/report exports, pagination, password recovery, two-factor authentication, notifications, full cycle administration UI, deployment/backup restoration, and malware scanning remain outside this checkpoint.
- The actual Figma site was not available for inspection; login and supplied screenshots guided the current visual design.

## Next exact task

Implement the React certification interface only: display Ready for Completion Review in requirement lists/detail and dashboard counts; show immutable certification history; allow an authorized Coordinator to complete or reopen with a required rationale through the existing backend endpoint; then extend the Playwright workflow.

## Important decisions

- Django owns permission checks, workflow transitions, compliance calculations, and protected download authorization.
- Reviews attach to a submitted document version and never transfer to a later version.
- A reviewer cannot decide on their own upload or submission.
- Approval alone never completes a requirement. Compliance counts only the latest effective Coordinator `complete` certification; a later `reopened` certification removes it from the numerator while preserving history.
- A recorded completion remains effective until a Coordinator reopens it; later uploads, submissions, or evidence expiry do not silently alter the certification.
- The existing local PostgreSQL development cluster uses port 55432 and is isolated under ignored `.local/` data.
- Demo data is explicitly labeled fictional and uses generated local-only credentials.
