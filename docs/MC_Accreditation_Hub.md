# MC Accreditation Hub — Codex Implementation Plan

Version: 1.0, proposed implementation baseline

## 1. Instructions to Codex

Build this project one complete feature at a time. Each feature includes the necessary database migrations, Django API, authorization, React interface, meaningful tests, and manual verification instructions. Do not build the entire backend before connecting the frontend.

First inspect the repository and its instructions. If it is empty, prepare the proposed directory structure. Read this plan and supplied presentation/screenshots. Explain any contradictions and record assumptions. Implement only the slice the user requests; finish at a working checkpoint and wait for the next slice. Do not implement every slice in one run.

The required stack is React + Vite, Django + Django REST Framework, PostgreSQL, and protected document storage. Do not substitute htmx, Firebase, or a different backend. Do not introduce paid services, microservices, AI features, or a public deployment without a concrete requirement.

Keep code understandable for a thesis defense. Explain important decisions, not every line. Update the README and a short progress record after each slice. Never claim a test passed unless it ran; distinguish implementation from verified behavior.

## 2. Project purpose and source boundaries

The system supports the Graduate School of Mabini Colleges, Inc. in organizing PACUCOA accreditation evidence, reviewing submissions, tracking internal readiness, and generating preparation reports.

Sources supplied by the user:
- `MC_Accreditation_Hub.pptx`: 11-slide project presentation previously reviewed.
- Login screenshot: blue gradient, institutional branding and feature descriptions on the left, white login card on the right.
- Figma reference: https://base-stool-67955880.figma.site/ — not successfully inspected in the planning conversation. Only the login screenshot has been visually reviewed. Do not claim other screens match Figma without inspecting them.

Confirmed: React + Django; evidence repository, requirements management, evidence mapping, review, dashboard, search, reporting, roles, and audit history; intended school-owned hosting.

Everything labeled “proposed” below is an implementation assumption, not an established institutional or PACUCOA policy. Use synthetic demonstration data. Do not invent official accreditation criteria, scores, or classifications.

## 3. Scope

Version 1 includes accounts and scoped roles; assessment cycles; areas and requirements; assignments and deadlines; document versions; submissions containing evidence; approval and revision requests; requirement completion decisions; dashboard; metadata search; CSV and printable reports; audit history; and deployable backup/restore procedures.

Deferred: AI classification, OCR/full-document search, electronic signatures, external accreditor accounts, public registration, SSO, automated email reminders, bulk evidence ZIP exports, mobile applications, and integrations with other school systems. Add only after the core workflow works and the scope is explicitly extended.

An approval represents an internal verification decision. It is not an official accreditation award or PACUCOA rating.

## 4. Architecture

Use a modular Django monolith with a separate React single-page application in one repository. PostgreSQL stores structured records; protected filesystem storage stores document bytes.

| Component | Responsibility |
|---|---|
| React + Vite | Routes, accessible forms, tables, dashboard, upload and review interfaces |
| Django REST Framework | API serialization, authentication, scoped queries, validation |
| Django domain services | Submission transitions, review decisions, requirement completion, audit writes |
| PostgreSQL | Relational data, constraints, transactions, history references |
| Protected storage | Immutable evidence-version files outside public web directories |
| Reverse proxy | HTTPS, React production assets, forwarding `/api/` and restricted admin traffic |

Production request flow: browser requests the site; proxy serves the React build; React calls same-origin `/api/v1/`; Django checks authentication and permissions, then accesses data or files. The browser never connects to PostgreSQL. No database credentials or server secrets belong in frontend environment variables.

Use Django session authentication with CSRF protection for this same-origin browser application. Protect login itself against CSRF; do not assume DRF's authenticated-request CSRF handling protects an anonymous login endpoint. Session cookies are HTTP-only and secure over production HTTPS. Do not store authentication tokens in localStorage. Use the Vite development proxy for API requests locally, and verify cookie/CSRF behavior.

Reference: [DRF authentication](https://www.django-rest-framework.org/api-guide/authentication/).

Proposed repository folders:
- `backend/config/`: settings, URLs, application entry points.
- `backend/accounts/`: custom user model, authentication, account administration, scoped roles.
- `backend/accreditation/`: cycles, areas, requirements, assignments, requirement completion.
- `backend/evidence/`: evidence, versions, submissions, reviews, authorized downloads.
- `backend/reporting/`: dashboard queries and report endpoints; reuse domain rules.
- `backend/audit/`: audit event model and write helper.
- `frontend/src/app/`: routing, providers, authenticated shell.
- `frontend/src/features/`: auth, accounts, requirements, evidence, reviews, dashboard, reports.
- `frontend/src/components/`: shared controls and layout.
- `frontend/src/lib/`: API client and error handling.
- `docs/`: architecture, API conventions, decisions, manual checks, progress.
- `deploy/`: deployment examples and operational instructions.

Proposed frontend baseline: JavaScript/JSX, React Router, CSS variables and reusable CSS components, one API wrapper using fetch. Respect existing repository conventions if a project already exists. Avoid adding a state library until justified; do not duplicate server data across unrelated local stores.

Codex must verify compatible supported package versions when implementation starts, pin dependencies, and retain lockfiles. This plan deliberately does not prescribe guessed latest version numbers.

## 5. Users and access policy

Proposed roles are capabilities with scope, not job titles. The Dean can be assigned Viewer access; faculty/staff can be Contributors. A person may have several roles in different areas.

| Role | Scope and capabilities |
|---|---|
| Administrator | Manage accounts, roles, cycles and institution-wide configuration; read records and audit history. Academic review requires an explicit reviewer/coordinator grant. |
| Coordinator | Manage areas/requirements, assignments and deadlines within a granted cycle; approve applicability decisions and certify requirement completion; review only where authorized. |
| Reviewer | Read assigned-area requirements and submitted evidence; approve or request revisions; no account administration or unrelated-area access. |
| Contributor | Read requirements in granted areas; create evidence and submit work for assigned requirements; change their own drafts; no approval powers. |
| Viewer | Read authorized scope, dashboards, approved evidence and reports; no changes. |

Use Django Groups/permissions for capability names and a RoleGrant model for scope. Admin is institution-wide; Coordinator is cycle-wide; Reviewer/Contributor/Viewer can be area-wide or cycle-wide. Validate allowed combinations. Default deny if no matching grant. Grants should not silently become global when scope fields are absent.

Proposed separation of duties: reject a review when the actor submitted the package or uploaded any version in it. If staffing makes this impractical, obtain the user's decision before weakening it. Do not silently use superuser access to bypass the product workflow.

Filter list querysets, dashboards, search, counts, exports and download access using the same policy. Object checks alone are insufficient for lists and creates. Validate ownership and scope when accepting foreign-key IDs. Permission changes must take effect on subsequent requests, including file access. Reference: [DRF permissions](https://www.django-rest-framework.org/api-guide/permissions/).

Version 1 evidence belongs to a single cycle and area. It may support several requirements in that area. Cross-area sharing is deferred until an explicit visibility policy is agreed. Within an area, reviewers/coordinators may read submitted packages; viewers read approved evidence only; contributors see their own drafts/submissions and approved shared evidence. Document titles and search snippets must follow the same visibility rules as files.

## 6. Initial database design

Plan these relationships now; create migrations only as the relevant slice is implemented. Use UUIDs for externally exposed records, timezone-aware timestamps and database constraints. UUIDs do not replace permission checks.

| Entity | Essential fields and relationships |
|---|---|
| User | Custom Django user created before initial migrations; unique username, unique normalized email, name, active flag; Django password handling |
| AccreditationCycle | Name, program label, framework label/version, period dates, status: draft/active/closed; archive flag |
| Area | Cycle FK, code, title, description, display order; unique code within cycle |
| RoleGrant | User FK, role, optional cycle/area scope under validated combinations; unique grant |
| Requirement | Area FK, code, title, description, acceptance criteria, due date, applicable flag, exclusion reason, archive flag, revision counter; unique code within area |
| RequirementAssignment | Requirement FK, user FK; unique pair; user must have contributor access to that scope |
| Evidence | Cycle and area FKs, title, description, creator; logical document identity |
| EvidenceVersion | Evidence FK, version number, private storage key, original filename, media type, byte size, checksum, uploader, created timestamp; unique evidence/version pair |
| Submission | Requirement FK, attempt number, submitter, status, notes, timestamps, requirement revision/snapshot at submission; unique requirement/attempt |
| SubmissionItem | Submission FK, EvidenceVersion FK, explanatory note; unique submission/version pair |
| ReviewDecision | Submission FK, reviewer, approve/revisions_requested, comment, timestamp; one terminal decision per submitted attempt |
| RequirementAssessment | Requirement FK, actor, complete/reopened/not_applicable/applicable, rationale, criteria snapshot, timestamp; append-only |
| AssessmentSubmission | RequirementAssessment FK, approved Submission FK; records exactly which packages support completion |
| AuditEvent | Actor or system identity, action, entity reference, timestamp, request correlation ID, safe change summary |

Do not duplicate a cycle/area relationship without validating consistency. A submission item must match the requirement's area and cycle. The same evidence version may appear in several submissions, each reviewed independently.

Use protected relationships for referenced history. Archive records rather than deleting cycles, requirements, submitted evidence or decisions. Deactivate users instead of deleting them. Unsubmitted drafts can be deleted by their owner if not referenced elsewhere. Do not expose update/delete endpoints for decisions or audit events.

Audit records are append-only through application APIs, not claimed tamper-proof against a database administrator. Avoid recording passwords, session tokens, full files, or excessive personal data.

## 7. Workflow and status rules

### Evidence and submissions

An EvidenceVersion is immutable: uploading a replacement produces a new version. A review always refers to a package of pinned versions, never an implicit “latest file.” New versions do not automatically change prior submissions or approvals.

Proposed submission states: `draft`, `submitted`, `approved`, `revisions_requested`, `withdrawn`.

Allowed transitions:
- Draft to submitted: assigned contributor; at least one valid evidence version, all scope checks passed.
- Draft to deleted: owner; no historic dependencies.
- Submitted to approved or revisions_requested: authorized independent reviewer; revision requests require an explanatory comment.
- Submitted to withdrawn: submitting contributor, before a review decision; require confirmation in the UI.
- Approved/revisions_requested/withdrawn are immutable terminal attempts.
- Resubmission creates a new draft attempt, optionally copying item references from an earlier attempt. It does not overwrite the earlier attempt.

Use a transaction and row lock or equivalent concurrency guard for submission and decision actions. Prevent double decisions and return a useful conflict response for stale actions. Proposed rule: only one currently submitted attempt per requirement; drafts may exist but cannot be submitted while another attempt awaits review.

### Requirement completion

Approving a package does not automatically certify the entire requirement. An authorized Coordinator marks a requirement Complete, provides a rationale, and selects one or more approved packages satisfying its acceptance criteria. The form must show the criteria and selected versions.

Not Applicable requires a Coordinator decision and reason. Reopen Complete before changing substantive criteria or replacing its supporting evidence; preserve the old assessment. Editorial changes can be audited without reopening, but criteria changes require an explicit operation. Submitted attempts with outdated criteria must be returned for revision before approval.

A newer document upload alone does not invalidate old evidence. Replacing evidence used for current completion requires reopening and a new assessment. No automatic expiry policy in version 1; add only with agreed validity rules.

Close a cycle only through a deliberate coordinator/admin action. Closed cycles are read-only for ordinary operations, including uploads and reviews. Reopening requires authorized action and an audit reason. Do not copy old approvals into a new cycle.

### Derived dashboard status

For active, applicable, non-archived requirements, derive one mutually exclusive state in this order:
1. Complete: latest effective assessment certifies completion.
2. For verification: an attempt is currently submitted.
3. Needs revision: latest non-withdrawn attempt requests revisions.
4. Ready for completion review: an approved package exists, but no effective completion assessment.
5. In progress: draft work exists or a requirement was reopened without a higher-priority state.
6. Missing: none of the above.

Not Applicable is shown separately. “Overdue” is a separate flag: past due date and neither Complete nor Not Applicable. Store dates consistently; display in Asia/Manila by proposed default.

Proposed internal readiness formula:

`complete applicable requirements / total applicable non-archived requirements × 100`

Display N/A when the denominator is zero. No weighting unless explicitly required. Show numerator, denominator, cycle, filters and timestamp in reports. Scope the denominator to the user's authorized view and label it “Your scope” for restricted users. All status counts must reconcile with that denominator.

The presentation's sample 94 complete out of 120 gives 78.3%, not 87%; do not reproduce that mismatch. This is internal readiness, not an official accreditation score.

## 8. API outline

Base: `/api/v1/`. Paginate lists; allowlist sorting/filter fields; return stable field errors and readable general errors. Treat server data as authoritative. Read-only actions use GET; mutations never use GET.

| Endpoint family | Purpose |
|---|---|
| `/auth/csrf/`, `/auth/login/`, `/auth/logout/`, `/auth/me/` | CSRF bootstrap, session lifecycle, current user/capabilities |
| `/auth/password-change/`, `/auth/password-reset/`, `/auth/password-reset-confirm/` | Password workflows; reset delivery requires configured institutional email |
| `/users/`, `/role-grants/` | Restricted account and scoped-access administration |
| `/cycles/`, `/areas/`, `/requirements/`, `/assignments/` | Authorized record management |
| `/cycles/{id}/close/`, `/cycles/{id}/reopen/` | Explicit lifecycle transitions |
| `/requirements/{id}/assessments/` | Complete, reopen, or applicability decisions; append-only |
| `/evidence/`, `/evidence/{id}/versions/` | Logical evidence and version uploads |
| `/evidence-versions/{id}/download/` | Authorized streamed download; no raw filesystem paths |
| `/submissions/`, `/submissions/{id}/items/` | Create/manage draft packages |
| `/submissions/{id}/submit/`, `/withdraw/`, `/resubmit/` | Explicit state actions under the submission URL |
| `/submissions/{id}/review/` | Approve or request revisions |
| `/dashboard/`, `/search/`, `/reports/compliance/`, `/audit-events/` | Scoped read and export operations |

Response details should include permitted actions to guide UI controls, but backend checks remain mandatory. Standardize unauthenticated/forbidden responses in the API wrapper; do not assume every DRF denial is HTTP 401.

## 9. Screens and interaction requirements

| Screen | Required behavior |
|---|---|
| Login | Empty credentials, show/hide password, accessible labels, validation, loading, generic login errors |
| Application shell | Responsive sidebar, current cycle selector, current user, logout |
| Dashboard | Real scoped counts, state breakdown, overdue requirements, links to filtered lists |
| Requirements list | Cycle/area/status/assignee filters, pagination, authorized create/edit |
| Requirement detail | Criteria, due date, assignees, submissions, review history, completion assessment |
| Evidence repository | Search titles/metadata, filter within allowed scope, upload, version history |
| Submission editor | Select requirement and exact evidence versions, notes, save draft, submit |
| Review queue/detail | Submitted packages, file downloads, criteria, approve or request revisions |
| Reports | Filtered compliance table, CSV download, print-friendly view |
| Account administration | Create/deactivate users, scoped role grants; no public registration |
| Audit view | Authorized filters by actor/action/date/entity; read-only |

Match the supplied login screenshot's composition and blue palette. Use consistent typography, spacing, buttons and form errors across new screens. Until more screenshots arrive, other screens are proposed designs, not verified Figma reproductions.

Every data screen needs loading, empty, failed-request and access-denied states. Preserve entered form data on recoverable failures. Disable repeated submit clicks but also guard duplicate server transitions. Confirm destructive/irreversible user actions. Support keyboard navigation, visible focus, adequate contrast and narrow screens.

“Remember me” can use configurable session lifetimes; suggested defaults are browser-session expiry when unchecked and seven days when checked, pending school policy. Password recovery must not claim an email was sent when delivery is unconfigured; provide a documented administrator recovery process for the pilot. Never prefill real credentials or include live secrets in fixtures.

## 10. File handling and operations

Proposed pilot upload limit: 20 MiB/file; allow PDF, DOCX, XLSX, PPTX, JPEG and PNG. Make the limit configurable and confirm accepted formats with users. Validate extension and detected type; reject executable/HTML/SVG content in version 1. Use generated storage keys, retain a sanitized display filename and compute a checksum. Enforce request-size limits at proxy and application layers.

Serve downloads as attachments with safe headers. Defer inline Office/PDF preview until its security behavior is deliberately implemented. Never expose a public media folder for evidence. Database and file writes are not one atomic transaction: use temporary uploads and cleanup on failed database operations, and document reconciliation for missing/orphaned files. Do not delete referenced versions.

Before real institutional uploads, agree how files will be scanned or quarantined. If malware scanning is unavailable, disclose that limitation to the system owner and constrain the pilot; do not claim files are malware-free after checking extensions.

Production proposal: Linux server, reverse proxy, production Django application server, PostgreSQL and persistent evidence directory. Docker Compose is an optional packaging choice after school IT confirms compatibility. Use a built React bundle, not the Vite development server. Reference: [Vite production build](https://vite.dev/guide/build).

School-owned on-premises hosting is confirmed as an intent, but the presentation's “private cloud” classification needs validation against the actual infrastructure. Do not claim an ordinary web server alone demonstrates all private-cloud characteristics.

Configure HTTPS, environment-managed secrets, DEBUG off, allowed hosts, restricted database access, logs and health checks. Do not use in-memory/local-development storage for persistent production files. Uploaded files are untrusted and need a backup strategy: [Django deployment checklist](https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/).

Back up PostgreSQL and evidence files as a recoverable set, plus configuration needed for recovery. Proposed pilot schedule is nightly backups with a separate failure-domain copy; actual retention, acceptable data loss and recovery time require school approval. Test restoring into a separate environment and verify an approved evidence download and its review history. A same-disk copy is not the sole backup.

## 11. Feature-by-feature build sequence

Every slice uses real API-backed data by its completion. Temporary fixtures are allowed during construction, but label them and remove them from the production flow before declaring the slice done.

| Slice | Full-stack deliverable | Acceptance checkpoint |
|---|---|---|
| 0. Repository and plan | Inspect existing work; reconcile this plan; record architecture, assumptions, API conventions and dependency choices | Clear plan and commands; no broad implementation yet |
| 1. Setup and authentication | PostgreSQL configuration, custom user, sessions/CSRF, React login and protected shell, minimal authenticated landing page | Login, refresh, logout, inactive-user denial and CSRF rejection work in the browser |
| 2. Cycles and scoped access | Cycle/area models and screens, user administration, role grants, audit foundation | Admin can create a cycle/area and grant scoped access; unauthorized users cannot list or modify it |
| 3. Requirements and assignment | Requirements, criteria, due dates and assignment forms/list/detail | Coordinator assigns a requirement; assigned contributor sees it; cross-area IDs are rejected |
| 4. Evidence and versions | Private upload/download, metadata repository and version history | Contributor uploads and downloads an allowed file; version 2 preserves version 1; unauthorized downloads fail |
| 5. Submission workflow | Draft editor with pinned versions, submit/withdraw/resubmit actions and history | Submitted package is immutable; invalid scope and duplicate pending attempts are rejected |
| 6. Reviews | Reviewer queue, package detail, approve/revision actions, concurrency protection | Reviewer returns work; contributor resubmits; independent reviewer approves; self-review and duplicate decisions fail |
| 7. Completion and dashboard | Completion/reopen/applicability assessments; shared status computation; real dashboard | Coordinator certifies against approved packages; counts reconcile; 0 denominator and reopened cases are correct |
| 8. Search and reports | Scoped metadata search, CSV and printable compliance report, user-facing audit view | Results respect scope; CSV totals match dashboard under the same filters; spreadsheet-formula injection is neutralized |
| 9. Cycle lifecycle and recovery | Close/reopen/archive actions, password change/recovery, responsive/accessibility finishing | Closed cycle cannot mutate; reopen is logged; configured reset works; mobile main flow is usable |
| 10. Deployment and thesis evaluation | Deployment config, restore procedure, release verification and user-evaluation materials | Whole workflow passes on target-like environment; backup restoration verified; limitations documented |

Build audit recording and permissions alongside slices 1–9; slice 8 adds the audit viewing interface, not the first audit records. Do not delay file protection until deployment.

## 12. Verification and definition of done

Use focused Django/DRF integration tests for state transitions, scope checks, login/CSRF, file validation, version immutability, completion and dashboard reconciliation. Use PostgreSQL for database-dependent constraints and concurrency checks. Add browser workflow tests when the relevant full workflow exists; use the existing test framework or a small Playwright setup if needed.

Important checks:
- A Contributor cannot approve or obtain another scope's files by guessing URLs.
- Search, reports and dashboard counts do not disclose hidden records.
- Two reviewers cannot commit conflicting decisions on the same attempt.
- A new file version does not rewrite a previously approved package.
- Approved package alone does not mark a requirement Complete.
- Closed-cycle writes fail regardless of which endpoint is used.
- N/A exclusions and reopened requirements produce correct readiness totals.
- Files and database records remain usable after restoration.

Each slice is done when migrations run, the actual UI/API workflow works, relevant failures are handled, meaningful checks pass, and documentation describes manual verification and known limits. Run only relevant checks plus required project gates. Explain any test that could not run.

Keep Git changes focused. Commit only project-related files if the user's repository workflow permits; never rewrite history or commit secrets. If committing is not authorized, provide a suggested commit message. Do not deploy or run migrations against a real school database as part of local implementation without that target being explicitly authorized.

## 13. Thesis evidence and evaluation

Keep an ERD, architecture explanation, role matrix, workflow description, screenshots, acceptance results and deployment instructions consistent with the implemented system. Update them when behavior changes.

Proposed evaluation measures: time to retrieve a specified document, time to identify missing requirements, task completion rate, review turnaround and usability feedback. Use the same tasks and comparable conditions for a baseline comparison. Record actual participant results; do not fabricate evaluation scores. Sample dashboard data must be labeled synthetic.

## 14. Decisions to confirm, without blocking initial setup

| Question | Proposed baseline | Needed by |
|---|---|---|
| Official accreditation areas/requirements and criteria? | Editable structure; synthetic fixtures only | Real content setup, slice 3 |
| One or several programs per assessment? | Each cycle represents one program/assessment scope; program is a label initially | Cycle design, slice 2 |
| Who can review and certify completion? | Independent Reviewer; Coordinator certifies completion | Permission design, slices 2 and 6 |
| Cross-area evidence sharing? | Same-area reuse only | Any requested sharing feature |
| Accepted document types and maximum size? | Proposed allowlist and 20 MiB | Slice 4 |
| Is more than one review stage needed? | Single package decision followed by requirement completion assessment | Slice 6 |
| Weighted scoring or official rubric? | Unweighted internal readiness | Slice 7 |
| Actual dashboard and internal Figma screens? | New screens use login style until references arrive | Visual implementation of each screen |
| School email delivery? | Administrator-assisted recovery until configured | Slice 9 |
| Server OS, CPU/RAM, disk, network/domain and IT owner? | No assumed provisioning or public access | Slice 10 |
| Retention, backup targets and real file sensitivity? | Preserve history; no automatic purge | Production release |
| Deadline, expected users and concurrent uploads? | Small institutional pilot; no invented sizing promise | Scheduling and deployment |

When an unresolved policy affects the current slice, present the exact decision and its consequence. Continue unrelated authorized work. Do not repeatedly ask questions already answered.

## 15. Prompts to use with Codex

### First session

Read MC_Accreditation_Hub_Codex_Plan.md and the supplied presentation/screenshots. We are using React + Vite, Django + DRF and PostgreSQL. Inspect the repository first. Complete Slice 0 only: reconcile the plan with existing code, list material assumptions, and propose the initial architecture and schema. Do not implement the whole application. Preserve the single-feature end-to-end workflow in this plan.

### Start the first working feature

Implement Slice 1 only from the agreed plan. Build the database setup, custom user, Django session/CSRF authentication and React login/protected shell together. Use the login screenshot. Verify the browser workflow, invalid credentials, inactive accounts, logout and CSRF protection. Explain the changes and give exact local commands and manual checks. Pause when this slice is working.

### Continue subsequent slices

Read the plan and current progress. Implement Slice [NUMBER] only, respecting completed features and existing conventions. Include its models/migrations, API, scoped permissions, React screens and meaningful verification. Use real backend data. Document decisions and any remaining limitations. Finish at a working checkpoint; do not start the next slice yet.

### Fix a failed checkpoint

The current slice fails this behavior: [EXPECTED BEHAVIOR]. Actual result: [ERROR OR SCREENSHOT]. Investigate the root cause and fix this slice without expanding scope. Add a focused regression check if appropriate, rerun affected verification and explain how to confirm the fix.
