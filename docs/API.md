# First-increment API contract

All paths below are prefixed by `/api/`. JSON unless uploading a file. All endpoints except CSRF/login require a session. Unsafe requests require `X-CSRFToken`. Retrieve a fresh token after login because Django rotates it.

| Method/path | Contract |
|---|---|
| GET `health/` | Unauthenticated readiness probe; returns only `{status:"ok"}` after a database query, otherwise HTTP 503 |
| GET `auth/csrf/` | Sets CSRF cookie and returns `{csrfToken}` |
| POST `auth/login/` | `{username, password, remember?: boolean}`; accepts username or email, returns current user and assignments |
| GET `auth/me/` | `{id, name, username, is_staff, assignments:[{role,cycle_id,area_id}]}` |
| POST `auth/logout/` | Ends session |
| POST `auth/password-change/` | Authenticated `{current_password,new_password}`; keeps the current session valid and records an audit event |
| POST `auth/password-reset/` | `{email}`; sends a non-enumerating recovery email only when institutional delivery is configured, otherwise returns the administrator-recovery instruction |
| POST `auth/password-reset-confirm/` | `{uid,token,new_password}`; consumes a valid one-time recovery token |
| GET `cycles/` | Accessible cycles only |
| POST `cycles/{id}/close/` | Scoped Coordinator only `{rationale}`; changes an active cycle to closed and logs each authorized area |
| POST `cycles/{id}/reopen/` | Scoped Coordinator only `{rationale}`; restores a closed cycle to active and logs each authorized area |
| GET `areas/?cycle=id` | Scoped areas, permission flags, and compliance totals |
| GET `requirements/?cycle=id&area=id&search=text&status=complete` | Scoped requirement summaries; filters optional |
| POST `requirements/` | `{area,code,title,description?,responsible,deadline?,active,applicable?,exclusion_reason?,items:[{label,criteria?,mandatory?}]}`; records initial applicability history |
| GET `requirements/{id}/` | Requirement plus evidence, `criteria_revision`, `certification_candidates` (current approved submissions with exact version/checksum), certification snapshots, legacy label, and applicability history |
| PATCH `requirements/{id}/` | Editorial metadata may change; changed description requires `change_reason` and increments criteria revision. Changed applicability or exclusion reason requires `applicability_reason`; exclusion also requires `exclusion_reason`. Substantive changes require a prior reopen. Cannot move areas or replace the evidence checklist. |
| GET/POST `requirements/{id}/assignments/` | Scoped Coordinator only: active assignments and eligible exact-area/cycle Custodians / `{user,reason,replace?:boolean}`. `replace:true` explicitly deactivates other active assignments and is audited. |
| GET/POST `requirements/{id}/certifications/` | Scoped append-only history / Coordinator-only `{outcome:"complete",rationale,submissions:[id,...]}` or `{outcome:"reopened",rationale}`. Completion requires deliberate selection of current, approved, unexpired submissions covering every mandatory item. Each selected submission is linked immutably and its exact version metadata is copied alongside a criteria snapshot. |
| GET `evidence-items/?requirement=id` | Scoped evidence-item definitions |
| GET `documents/?cycle=id&search=text` | Scoped metadata, visible versions and mappings |
| POST `documents/` | Multipart `file,title,area,requirement,category?,valid_until?,override_reason?`; assigned Custodian creates a stewarded document and immutable v1. A scoped Coordinator exception requires `override_reason`. |
| GET `documents/{uuid}/` | Document and accessible version history |
| GET/POST `documents/{uuid}/versions/` | List visible versions / steward-only multipart `file,valid_until?,override_reason?` replacement. A scoped Coordinator exception requires `override_reason`. |
| GET/POST `documents/{uuid}/stewardship/` | Scoped Coordinator only: eligible exact-area/cycle Custodians / `{steward,reason}` explicit stewardship delegation. |
| GET `document-versions/{id}/download/` | Permission-checked file attachment; no-store cache policy |
| GET/POST `evidence-mappings/` | List scoped mappings / `{item,document,override_reason?}`; assignment and stewardship are enforced; a Coordinator exception requires a reason and is audited. Existing pair returns the existing mapping. |
| GET/POST `submissions/` | List scoped submission history (`?cycle=id`) / `{mapping,version,override_reason?}`; assignment and stewardship are enforced; a Coordinator exception requires a reason and is audited. |
| GET/POST `review-decisions/` | List scoped decisions / `{submission,outcome,comment}` |
| GET `compliance/?cycle=id` | `{total,complete,ready_for_completion_review,pending,for_compliance,missing,excluded,percentage,formula,formula_version,calculated_at,scope}` |
| GET `audit/?cycle=id&search=text&action=name` | Last 200 scoped audit events, optionally filtered by record/actor/action |
| GET `search/?cycle=id&q=text` | Scoped requirement and document metadata search (maximum 50 each) |
| GET `reports/compliance/?cycle=id&area=id&status=value` | Scoped printable compliance report data; add `download=csv` for a formula-safe CSV export |

## Provisional F01–F03 access policy

The Project Owner has provisionally selected D01–D03 Option A; formal Academic Owner and Security/Records Owner approval remains required before production acceptance. The backend applies one default-deny visibility policy to document lists/detail/version history, mappings, submissions, reviews, search, downloads, and the frontend data returned by those endpoints. Multiple explicit grants are additive. The product Administrator role does not imply academic evidence access.

| Explicit role grant | Evidence visibility in that scope | History / authority |
|---|---|---|
| Coordinator | All versions in scope | Submission/review history in scope; only a cycle-wide Coordinator grant (`area=null`) can close/reopen the entire cycle. |
| Reviewer | Submitted versions only | Submitted/review history in scope; no drafts or lifecycle authority. |
| Custodian (Contributor implementation) | Own document/upload/submission plus approved shared evidence | New evidence work additionally requires an active requirement assignment and recorded document stewardship under provisional D04 Option A. |
| Viewer | Approved versions only | No submission/review history or write authority. |

New `POST evidence-mappings/` and `POST submissions/` requests require the document and requirement to have the same owning area and cycle, an active requirement assignee, and the document steward. A scoped Coordinator must supply a reason for any assignment/stewardship override; the action is audited. Existing immutable cross-area/cross-cycle records and pre-F04 documents/submissions are retained without invented assignments or owners. A legacy unowned document cannot receive a new version until a scoped Coordinator explicitly delegates stewardship. Search can match an original filename only when that exact version is visible to the requester; a hidden newer filename cannot produce a document result.

Decision outcomes: `approved`, `revision_requested`, `rejected`. Submission display states add `pending`, `expired`, and `outdated` when its recorded criteria revision differs from the current requirement revision. Pre-F05 submissions have an unknown (`null`) revision; they remain available under the initial tracked baseline (revision 1) for a Coordinator's explicit review/selection, but become outdated after a criteria revision. Revision 1 names the criteria present when tracking began; it does not reconstruct earlier revisions. Outdated submissions cannot be reviewed or selected for a new certification; a new version must be submitted under the revised criteria. `current` indicates the latest submission for its mapping, and `can_review` describes authorized current UI actions. The server rechecks permissions and state on POST.

Requirement statuses: `draft`, `excluded`, `complete`, `ready_for_completion_review`, `missing`, `for_compliance`, `pending`. Approval does not complete a requirement. When all mandatory evidence items have approved, unexpired current submissions, the requirement is `ready_for_completion_review`. A scoped Coordinator must select the supporting submissions and provide a rationale before the append-only `complete` certification counts. Legacy completion rows without pinned evidence or criteria remain visible with `legacy:true` but are excluded from `complete` and report counts. A Coordinator may create a new auditable certification after selecting current evidence; the legacy row is never rewritten or backfilled. `formula_version` is 2 for this counting rule. A rationale-backed `reopened` row removes an effective completion. For incomplete requirements, all missing means missing; any missing, expired, revision-requested or rejected mandatory item means for compliance; otherwise it is pending verification.

A draft version upload or later expiry does not silently remove a pinned completion. A documented reopen is required before changed criteria, activation/applicability, new evidence mapping/submission, or review decisions. Applicability decisions retain actor, reason, state, and time in append-only history. These F05/F06 rules are provisional Project Owner decisions pending formal Academic Owner and Security/Records Owner approval.

Repeated submission of the same mapping/version is rejected. Replacements must use a higher document version number. Competing decisions are serialized using cycle and mapping locks; only one decision can be recorded per submission. Replacing pending evidence makes the older submission historical and prevents reviewing it.

Errors use 400 for validation/invalid transitions, 403 for missing sessions or denied actions, 404 for inaccessible records, and 429 for login throttling. Hidden records are never returned by list endpoints. Unknown HTTP operations return 405. This first increment returns unpaginated scoped collections; add pagination before scaling to large institutional datasets.

Password recovery remains disabled unless `PASSWORD_RESET_ENABLED=1`, `DEFAULT_FROM_EMAIL`, and `EMAIL_HOST` are configured. The recovery link is built from `PASSWORD_RESET_FRONTEND_URL`; configure it with the production HTTPS application URL before enabling delivery.
