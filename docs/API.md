# First-increment API contract

All paths below are prefixed by `/api/`. JSON unless uploading a file. All endpoints except CSRF/login require a session. Unsafe requests require `X-CSRFToken`. Retrieve a fresh token after login because Django rotates it.

| Method/path | Contract |
|---|---|
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
| POST `requirements/` | `{area,code,title,description?,responsible,deadline?,active,applicable?,exclusion_reason?,items:[{label,criteria?,mandatory?}]}` |
| GET `requirements/{id}/` | Requirement plus evidence items, mappings, version submissions and decisions |
| PATCH `requirements/{id}/` | Editable requirement metadata/applicability/activation; cannot move areas or replace the evidence checklist |
| GET/POST `requirements/{id}/certifications/` | Scoped append-only completion history / Coordinator-only `{outcome: complete|reopened, rationale}` action |
| GET `evidence-items/?requirement=id` | Scoped evidence-item definitions |
| GET `documents/?cycle=id&search=text` | Scoped metadata, visible versions and mappings |
| POST `documents/` | Multipart `file,title,area,category?,valid_until?`; creates document and immutable v1 |
| GET `documents/{uuid}/` | Document and accessible version history |
| GET/POST `documents/{uuid}/versions/` | List visible versions / upload multipart `file,valid_until?` to create a new draft |
| GET `document-versions/{id}/download/` | Permission-checked file attachment; no-store cache policy |
| GET/POST `evidence-mappings/` | List scoped mappings / `{item,document}`; existing pair returns the existing mapping |
| GET/POST `submissions/` | List scoped submission history (`?cycle=id`) / `{mapping,version}` |
| GET/POST `review-decisions/` | List scoped decisions / `{submission,outcome,comment}` |
| GET `compliance/?cycle=id` | `{total,complete,ready_for_completion_review,pending,for_compliance,missing,excluded,percentage,formula,formula_version,calculated_at,scope}` |
| GET `audit/?cycle=id&search=text&action=name` | Last 200 scoped audit events, optionally filtered by record/actor/action |
| GET `search/?cycle=id&q=text` | Scoped requirement and document metadata search (maximum 50 each) |
| GET `reports/compliance/?cycle=id&area=id&status=value` | Scoped printable compliance report data; add `download=csv` for a formula-safe CSV export |

Decision outcomes: `approved`, `revision_requested`, `rejected`. Submission display states add `pending` and `expired`. `current` indicates the latest submission for its mapping, and `can_review` describes authorized current UI actions. The server rechecks permissions and state on POST.

Requirement statuses: `draft`, `excluded`, `complete`, `ready_for_completion_review`, `missing`, `for_compliance`, `pending`. Approval does not complete a requirement. When all mandatory evidence items have approved, unexpired current submissions, the requirement is `ready_for_completion_review`. An assigned Coordinator must create an append-only `complete` certification with a rationale before the requirement counts as `complete`. A Coordinator can later add a rationale-backed `reopened` certification; evidence, versions, reviews, and prior certifications remain historical. For incomplete requirements, all missing means missing; any missing, expired, revision-requested or rejected mandatory item means for compliance; otherwise it is pending verification.

A later evidence upload, submission, or expiry does not silently remove a recorded completion certification. A Coordinator must reopen the requirement to remove it from compliance.

Repeated submission of the same mapping/version is rejected. Replacements must use a higher document version number. Competing decisions are serialized using cycle and mapping locks; only one decision can be recorded per submission. Replacing pending evidence makes the older submission historical and prevents reviewing it.

Errors use 400 for validation/invalid transitions, 403 for missing sessions or denied actions, 404 for inaccessible records, and 429 for login throttling. Hidden records are never returned by list endpoints. Unknown HTTP operations return 405. This first increment returns unpaginated scoped collections; add pagination before scaling to large institutional datasets.

Password recovery remains disabled unless `PASSWORD_RESET_ENABLED=1`, `DEFAULT_FROM_EMAIL`, and `EMAIL_HOST` are configured. The recovery link is built from `PASSWORD_RESET_FRONTEND_URL`; configure it with the production HTTPS application URL before enabling delivery.
