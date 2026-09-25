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
| GET `requirements/{id}/` | Requirement, criteria, status, scoped package attempt history, visible `package_choices` with exact version/checksum, Coordinator-only approved package certification candidates, legacy item-level history, certification snapshots, and applicability history |
| PATCH `requirements/{id}/` | Editorial metadata may change; changed description requires `change_reason` and increments criteria revision. Changed applicability or exclusion reason requires `applicability_reason`; exclusion also requires `exclusion_reason`. Substantive changes require a prior reopen. Cannot move areas or replace the evidence checklist. |
| GET/POST `requirements/{id}/assignments/` | Scoped Coordinator only: active assignments and eligible exact-area/cycle Custodians / `{user,reason,replace?:boolean}`. `replace:true` explicitly deactivates other active assignments and is audited. |
| GET/POST `requirements/{id}/certifications/` | Scoped append-only history / Coordinator-only `{outcome:"complete",rationale,packages:[attempt_id,...]}` for package requirements, legacy `{outcome:"complete",rationale,submissions:[id,...]}` for preserved item-level requirements, or `{outcome:"reopened",rationale}`. Completion requires selected current approved support covering mandatory items; package/submission links, exact version details, and a criteria snapshot are immutable. |
| GET/POST `packages/?requirement=id&cycle=id` | Role-scoped attempts / create editable `{requirement,notes?,items?:[{mapping,version,note?}],override_reason?}` draft. Versions must be visible, mapped to this requirement, and owned by the document steward or a reasoned Coordinator override. |
| GET/PATCH/DELETE `packages/{id}/` | Scoped attempt detail / owner-only draft edit of `notes` and `items` / owner-only unsubmitted draft deletion. Submitted and terminal contents cannot be edited or deleted. |
| POST `packages/{id}/submit/` | Draft owner `{override_reason?}`; checks assignment/stewardship, version validity, no other pending package, and no effective certification; pins evidence metadata and current criteria revision/snapshot. |
| POST `packages/{id}/withdraw/` | Submitter `{confirm:true,reason?}` while awaiting review; creates an immutable withdrawn attempt. |
| POST `packages/{id}/review/` | Scoped independent Reviewer/Coordinator `{outcome:"approved"|"revisions_requested",comment?}`; revision comment required. Approval requires current criteria, unexpired evidence and every mandatory item. Decision is immutable. |
| POST `packages/{id}/resubmit/` | Assigned contributor or reasoned Coordinator `{copy_items?:true,override_reason?}` from a terminal attempt; creates a numbered draft linked to its source. Copied evidence is revalidated. |
| GET `evidence-items/?requirement=id` | Scoped evidence-item definitions |
| GET `documents/?cycle=id&search=text` | Scoped metadata, visible versions and mappings |
| POST `documents/` | Multipart `file,title,area,requirement,category?,valid_until?,override_reason?`; assigned Custodian creates a stewarded document and immutable v1. A scoped Coordinator exception requires `override_reason`. |
| GET `documents/{uuid}/` | Document and accessible version history |
| GET/POST `documents/{uuid}/versions/` | List visible versions / steward-only multipart `file,valid_until?,override_reason?` replacement. A scoped Coordinator exception requires `override_reason`. |
| GET/POST `documents/{uuid}/stewardship/` | Scoped Coordinator only: eligible exact-area/cycle Custodians / `{steward,reason}` explicit stewardship delegation. |
| GET `document-versions/{id}/download/` | Permission-checked file attachment; no-store cache policy |
| GET/POST `evidence-mappings/` | List scoped mappings / `{item,document,override_reason?}`; assignment and stewardship are enforced; a Coordinator exception requires a reason and is audited. Existing pair returns the existing mapping. |
| GET/POST `submissions/` | Preserved item-level submission history (`?cycle=id`) / `{mapping,version,override_reason?}` only for migrated legacy requirements not yet converted to package mode. New requirements use package attempts. |
| GET/POST `review-decisions/` | List scoped decisions / `{submission,outcome,comment}` |
| GET `compliance/?cycle=id` | `{total,complete,for_verification,needs_revision,ready_for_completion_review,in_progress,missing,excluded,percentage,formula,formula_version:3,calculated_at,scope}` |
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

Requirement statuses use this precedence: `draft` or `excluded` for inactive/out-of-scope requirements; then `complete` for a supported effective certification; `for_verification` for a pending package even when mandatory evidence is missing; `needs_revision` for the latest nonwithdrawn revision-requested attempt; `ready_for_completion_review` for a current approved package covering mandatory items; `in_progress` for a draft, mapped evidence, or a reopened requirement; otherwise `missing`. Migrated item-level requirements retain equivalent legacy status evaluation until a package is started. Approval alone does not complete a requirement. A Coordinator selects approved support and provides a rationale for an append-only certification. Legacy completions without pinned evidence/criteria remain labelled `legacy:true`, excluded from compliance, and can only be superseded by a new certification. `formula_version` is 3.

Package transitions are `draft` → `submitted` → `approved` or `revisions_requested`; the submitter may instead confirm `submitted` → `withdrawn` before review. Approved, revisions-requested, and withdrawn attempts are terminal. Resubmission creates a new numbered draft linked to the prior attempt; only one submitted attempt per requirement is allowed. Drafts can be edited or deleted, and no attempt is invented for existing item-level records. Package review does not offer `rejected`: D07 proposes leaving it unavailable until the Academic Owner decides whether rejection is distinct from a revision request. Legacy item-level `rejected` decisions remain unchanged. D07 Option A is a provisional Project Owner decision pending formal Academic Owner approval.

A draft version upload or later expiry does not silently remove a pinned completion. A documented reopen is required before changed criteria, activation/applicability, new evidence mapping/submission, or review decisions. Applicability decisions retain actor, reason, state, and time in append-only history. These F05/F06 rules are provisional Project Owner decisions pending formal Academic Owner and Security/Records Owner approval.

For preserved item-level requirements, repeated submission of the same mapping/version is rejected, replacements require a higher document version, and competing decisions use cycle/mapping locks. Package actions use cycle and requirement locks plus a database uniqueness constraint for the one-submitted-attempt rule; review decisions are one-to-one, and terminal attempts and their pinned items are immutable.

Errors use 400 for validation/invalid transitions, 403 for missing sessions or denied actions, 404 for inaccessible records, and 429 for login throttling. Hidden records are never returned by list endpoints. Unknown HTTP operations return 405. This first increment returns unpaginated scoped collections; add pagination before scaling to large institutional datasets.

Password recovery remains disabled unless `PASSWORD_RESET_ENABLED=1`, `DEFAULT_FROM_EMAIL`, and `EMAIL_HOST` are configured. The recovery link is built from `PASSWORD_RESET_FRONTEND_URL`; configure it with the production HTTPS application URL before enabling delivery.
