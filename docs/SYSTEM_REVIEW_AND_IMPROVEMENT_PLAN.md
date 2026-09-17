# System Review and Improvement Plan

Review date: 2026-09-17  
Project: Graduate School Accreditation Hub / MC Accreditation Hub  
Reviewed commit: `c14e36dea311c3b9b04f16f2e6f4e83a23c4dad4`  
Verdict: **Not ready, with listed blockers**

## Review basis and limits

This is a repository-wide review of the plan, progress record, README, API contract, all backend domain and API modules, migrations, administration and management commands, React application and styles, dependency manifests, backend and browser tests, configuration examples, local scripts, and deployment/recovery/evaluation artifacts. No `AGENTS.md` was found in the repository or its containing project directories; the implementation instructions in `docs/MC_Accreditation_Hub.md` were read first and used as the proposed requirements baseline.

The starting Git worktree was clean. The only intended repository change from this review is this report. Application code, configuration files, evidence, database records, secrets, and infrastructure were not changed. No commit was created. Actual secret values and private evidence were not opened or reproduced.

Evidence classifications used below:

- **Confirmed:** directly established by source/configuration inspection, sometimes supported by a read-only diagnostic. This does not imply an endpoint was exercised against a running database.
- **Confirmed plan deviation:** implemented behavior differs from the proposed plan. Institutional acceptance of that deviation has not been established by this repository.
- **Unverified acceptance item:** required evidence is absent from the reviewed repository; this is not a claim that school IT has failed the task elsewhere.
- **Recommendation:** a proposed improvement, not an assertion that an unobserved incident has occurred.

Backend integration and Playwright suites were inspected but not run: they create database records, and browser tests retain demonstration history. No deployment, login, audited download, migration application, restore, or infrastructure change was performed. Historical results in `PROGRESS.md` are distinguished from checks performed during this review. This was not an external penetration test, dependency vulnerability audit, visual reproduction review of Figma, or legal/privacy approval.

## 1. Executive Summary

The Hub is a substantial functional prototype with a connected React/Django/PostgreSQL workflow and useful operational reference materials. It appears suitable for continued synthetic-data demonstrations and remediation work. It should not yet be accepted for real institutional evidence under the current plan.

The strongest implemented components are session/CSRF authentication, area-scoped API queries, private attachment downloads, format validation, immutable document versions and review records, independent-review checks, transaction-protected competing decisions, Coordinator-only completion/reopening, a shared dashboard/report calculation, scoped metadata search, formula-safe CSV, and closed-cycle write guards. Tests demonstrate meaningful intent rather than only isolated CRUD behavior. The recovery and evaluation documentation correctly avoids fabricating restore or participant results.

However, “all planned slices are implemented” in `PROGRESS.md` is broader than the code supports. Requirement-specific assignments, package draft/withdraw/resubmit states, certification evidence/criteria snapshots, archive operations, overdue monitoring, and several administration/audit interactions from the plan are absent or materially simplified. These are distinct from explicitly deferred AI, OCR, SSO, reminders, external accounts, and integrations.

The most important risks are:

1. An area-only Coordinator can close or reopen the whole cycle. Readers in an owning area can see every document version, including other users' drafts, regardless of role. Shared-document search can match inaccessible future filenames.
2. Completion does not pin the submissions and criteria used for certification. Acceptance text and supporting current submissions can change while an existing certification continues to count.
3. Backup checksums contain original absolute paths, so verification is not portable and can check the wrong files on the source host. No actual isolated restoration or target-server release result is recorded.
4. Enabling recovery using the documented SMTP values leaves the default console email backend selected; reset links can be logged instead of emailed. Authentication throttling is weak across the proposed multi-worker/proxy deployment.
5. Production ownership, storage/scanning policy, capacity, backup replication/retention, and release evidence still require school IT decisions and verification.

There is no confirmed Critical finding from this review. Several High findings block production acceptance. “Not ready” refers to production acceptance and the claimed plan coverage; it does not negate the working prototype or prevent school IT from reviewing this report and the deployment proposal.

## 2. End-to-End Workflow Review

| Stage | What is implemented | Assessment / remaining gap |
|---|---|---|
| Accounts and roles | Custom user; case-insensitive email uniqueness; Django password handling; session login/logout; scoped `RoleAssignment`; administration through Django admin | Administrator assignments do not themselves grant account administration; staff/model permissions are a separate mechanism. Account and scope changes lack unified audit coverage. No public registration is exposed. |
| Cycles and areas | Scoped read screens; active cycle creation from JSON; close/reopen controls with reasons; transaction locks | Creation requires server access. No full configuration UI, archive action, or cycle period dates. Area-only Coordinator authority can affect the entire cycle (F01). |
| Requirements | Coordinator creation/editing; code uniqueness; descriptions; mandatory evidence criteria; applicability reason; active/draft flag | Evidence checklist is immutable through the API after creation. Description is presented as acceptance criteria but can change without revision tracking or reopening (F06). |
| Assignments and deadlines | Free-text responsible office/person and stored date; displayed in lists/details/reports | No user-linked requirement assignment, assignee validation/filter, assigned-contributor enforcement, or overdue calculation (F04, F23). |
| Upload and versioning | PDF/DOCX/XLSX/PNG/JPEG validation; 25 MiB maximum in code; random private keys; SHA-256; new immutable version per upload | Owning-area readers can access all drafts. Hard-coded upload policy differs from the plan. No malware scanning, crash reconciliation, or verified storage durability procedure (F02, F19, F20). |
| Mapping and submission | Exact version selection; source/destination write checks; immutable mapping/version submission history; newer replacements | Each submission covers one mapping/version, not a requirement package. No draft package, withdraw, or explicit resubmit operation; pending work can be superseded (F07). Controlled cross-area/cycle reuse is implemented despite the unresolved sharing policy. |
| Review | Current submissions; pinned download; approve/revision/reject; comments for non-approval; uploader/submitter self-review denial; locks and one decision per submission | Review dialog does not show criteria or filename/checksum. Criteria revisions are not tracked. Concurrency test exists for two decisions (F06, F22). |
| Certification | Coordinator-only, rationale-backed append-only complete/reopened decisions; all mandatory current evidence must be approved and unexpired at completion | No selected-submission relationship or criteria snapshot. Certification persists through later uploads, replacements, or expiry by explicit current design; replacement while complete needs reconciliation with the plan (F05, F06). |
| Dashboard | Actual scoped counts; distinct complete/ready/pending/attention/missing groups; N/A denominator; per-area totals | Shared calculation is a strength. No overdue or in-progress state; current status precedence differs from the plan. Stale data can remain during cycle changes/failures (F07, F16, F23). |
| Search | Scoped requirement/document metadata; bounded search term; up to 50 results of each type | Hidden version filenames can influence results. Cross-cycle shared documents are treated inconsistently between Search and Repository. No continuation/truncation notice (F03, F15). |
| Reports | Area/status filters; shared calculation; printable UI; formula-safe CSV | Export omits cycle/filter/time/denominator metadata. Report requests can race and display old data under new controls (F14, F16). |
| Audit history | Append-only application events; area-scoped last-200 view; API text/action filters | Account/grant/logout history and area-less auth events are unavailable in the user-facing audit API. UI omits details/filter controls; no older-event pagination (F13). |

## 3. Findings

Severity expresses impact in this project: High findings affect confidentiality, authority, accreditation-history integrity, recovery, or required acceptance evidence; Medium findings affect meaningful reliability/usability/control gaps; Low findings are improvements that do not by themselves prevent a controlled launch. Acceptance decisions below apply to real institutional evidence, not a fictional demonstration.

### F01 — Area-only Coordinator can close or reopen an entire cycle

- **Severity:** High. **Classification:** Confirmed access-control weakness.
- **Affected files:** `backend/hub/views.py:233–266`; `backend/hub/models.py:45–64`; `backend/hub/tests.py:374–387`.
- **Evidence / explanation:** The permission test is whether *any* Coordinator-authorized area exists in the cycle. An area-scoped Coordinator passes it, then the code changes the global cycle and writes events for all areas. `RoleAssignment` allows area-scoped Coordinators. The UI permission flags use the same broad test.
- **Likely impact:** A person responsible for one area can stop or resume unrelated areas' work and record a cycle-wide rationale in their audit history.
- **Recommended fix:** Require an explicit cycle-wide Coordinator grant, or a separately specified cycle-management capability. Test area-only Coordinators, cycle-wide Coordinators, ordinary administrators, and unrelated users.
- **Blocks school IT production acceptance:** Yes, unless cycle-wide lifecycle authority for every area Coordinator is explicitly approved and documented.

### F02 — Draft and evidence visibility does not implement the planned role policy

- **Severity:** High. **Classification:** Confirmed plan deviation with confidentiality implications.
- **Affected files:** `backend/hub/access.py:5–31`; `backend/hub/views.py:193–230,341–418,439–472`; README role matrix; plan §5.
- **Evidence / explanation:** `documents_for()` grants every read role all documents in an owning area. `can_version()` grants them all source versions without checking owner, submission, or approval. Submission/history endpoints likewise expose all scoped work. The plan limits Viewers to approved evidence, Reviewers to submitted work, and Contributors to their own drafts/submissions plus approved shared evidence.
- **Likely impact:** Viewers can download unsubmitted or rejected evidence; Reviewers and other Custodians can read private drafts. This is broader than the proposed access policy even though unrelated-area denial works.
- **Recommended fix:** Agree the state/ownership visibility matrix, then apply one shared policy to document lists, versions, search, history, counts, and downloads. Recheck revoked grants on each request; add role-by-state tests.
- **Blocks school IT production acceptance:** Yes, pending enforcement or explicit approval of the broader visibility model.

### F03 — Search reveals matches against inaccessible future filenames

- **Severity:** High. **Classification:** Confirmed metadata-disclosure path by source tracing.
- **Affected files:** `backend/hub/views.py:595–618`; `backend/hub/access.py:20–31`; `backend/hub/tests.py:202–212`.
- **Evidence / explanation:** A document shared by a submitted v1 is visible to the recipient. The separate version policy hides an unshared v2. Search nevertheless filters on `versions__original_name` across *all* versions. A term unique to v2 can return the document even though v2 is absent from detail/history and its download is denied. The existing shared-version test does not exercise Search.
- **Likely impact:** A recipient can infer hidden future-version filename information through repeated searches. No hidden file bytes are returned by this path.
- **Recommended fix:** Restrict the filename join to versions visible to that requester, preferably using a shared visible-version queryset/`Exists` predicate. Add a regression covering visible v1 and uniquely named hidden v2.
- **Blocks school IT production acceptance:** Yes.

### F04 — Requirement-specific assignments and ownership enforcement are missing

- **Severity:** High. **Classification:** Confirmed missing planned feature.
- **Affected files:** `backend/hub/models.py:67–91`; `backend/hub/access.py`; `backend/hub/views.py:168–183,426–466`; `frontend/src/main.tsx:1713–1923`; plan slices 3 and 5.
- **Evidence / explanation:** `responsible` is free text; there is no `RequirementAssignment` entity/API/UI. Write authority is area-based. Any Custodian with source/destination area authority can upload to an existing document or submit against any requirement in that area; document custodian/submitter ownership is not an additional restriction.
- **Likely impact:** Assignment is not enforceable or linked to active authorized users. Staff can replace colleagues' current work, and assignee-based accountability/filters from the plan cannot work.
- **Recommended fix:** Implement user-linked assignments and scope validation, with explicit rules for Coordinator overrides, ownership, deactivation, and reassignment. If area-wide teamwork is intended instead, approve that requirements change and revise the plan before acceptance.
- **Blocks school IT production acceptance:** Yes for the current plan; an approved team-work policy can change the required remediation.

### F05 — Certification does not preserve its chosen evidence and criteria

- **Severity:** High. **Classification:** Confirmed history-integrity gap against the plan.
- **Affected files:** `backend/hub/models.py:164–173`; `backend/hub/migrations/0003_requirementcertification.py`; `backend/hub/views.py:493–520`; `frontend/src/main.tsx:2241–2319`; plan §6–7.
- **Evidence / explanation:** A certification stores requirement, coordinator, outcome, rationale, and time. It has no criteria snapshot or relationships to the approved submissions/versions supporting that certification. The form submits only outcome/rationale. Later current mappings can differ; reconstructing contemporaneous evidence would require inference from separate histories rather than a recorded selection.
- **Likely impact:** The completion record cannot directly show exactly what was certified. This weakens accreditation preparation and restoration acceptance evidence.
- **Recommended fix:** Add immutable supporting-submission references and a requirement/criteria snapshot. Show the exact criteria and selected approved versions in the form. Preserve old certifications; represent missing historical selections honestly during migration.
- **Blocks school IT production acceptance:** Yes under the planned certification workflow.

### F06 — Substantive requirement changes and evidence replacement can bypass reopening

- **Severity:** High. **Classification:** Confirmed plan deviation / workflow-integrity weakness.
- **Affected files:** `backend/hub/serializers.py:16–46`; `backend/hub/views.py:317–330,448–466`; `backend/hub/compliance.py:20–43`; `frontend/src/main.tsx:1804–1810`; `backend/hub/tests.py:123–130`.
- **Evidence / explanation:** Description is labelled “Description / acceptance criteria” in the form and used when item criteria are empty. PATCH can change it while a requirement remains Complete. There is no revision/snapshot check before review. A new current replacement can also be submitted while certification remains effective; this is explicitly tested. Activation/applicability are mutable metadata rather than append-only assessment actions.
- **Likely impact:** Old approvals/certification can be presented alongside changed acceptance text or new pending/rejected current evidence. Draft/excluded toggles can hide a completion and restoring the flags can reactivate it without a fresh assessment. Reopen is unavailable while the computed status is draft/excluded.
- **Recommended fix:** Separate editorial changes from substantive criteria changes, add revision/snapshot tracking, require reopening before changing certified criteria or replacing certification-supporting evidence, and record applicability decisions with reasons/history. Preserve harmless new repository drafts and old approvals.
- **Blocks school IT production acceptance:** Yes, unless the materially different workflow is explicitly approved and its historical evidence remains pinned as in F05.

### F07 — The implemented submission/state workflow is narrower than the planned package workflow

- **Severity:** High. **Classification:** Confirmed plan deviation requiring a requirements decision.
- **Affected files:** `backend/hub/models.py:132–161`; `backend/hub/views.py:426–490`; `backend/hub/compliance.py`; `backend/config/urls.py`; plan slices 5–7.
- **Evidence / explanation:** Each immutable submission is one mapping/version. No package draft, notes/items, withdraw action, requirement-level attempt number, or explicit resubmit action exists. A newer version supersedes a pending submission rather than rejecting another pending attempt. Multiple mappings can await review for one requirement. Draft work has no In progress status, and a requirement with pending plus missing items becomes For Compliance rather than the plan's higher-priority For verification state.
- **Likely impact:** Users cannot follow the planned draft/withdraw/package-review flow. Reports and training may use different meanings for the same workflow concepts.
- **Recommended fix:** Either deliver the planned package/attempt transitions and status precedence or formally adopt the item-level workflow and revise acceptance criteria, screens, and tests. Do not claim slice 5's original checkpoint is satisfied by version replacement alone.
- **Blocks school IT production acceptance:** Yes until the workflow baseline is approved and verified; the differences are not all independently security defects.

### F08 — Recovery configuration can log reset links instead of delivering them

- **Severity:** High. **Classification:** Confirmed configuration/documentation defect; conditional on enabling recovery.
- **Affected files:** `backend/config/settings.py:64–72`; `backend/hub/views.py:121–156`; `deploy/env/mc-accreditation-hub.env.example`; README Account recovery; reset email template; systemd/Nginx logging configuration.
- **Evidence / explanation:** `EMAIL_BACKEND` defaults to Django's console backend. Neither the production example nor the documented enablement values sets `DJANGO_EMAIL_BACKEND` to SMTP. The enabled endpoint checks host/sender/flag, calls `form.save()`, and says a link was sent. Console mail writes the link to stdout, captured by the reference service. Frontend reset links also put uid/token in a query string that normal Nginx request logging can retain.
- **Likely impact:** Users may receive no recovery email while usable tokens appear in operational logs. SMTP and token confidentiality are not proven by the locmem test.
- **Recommended fix:** Explicitly select and verify SMTP; make enablement fail closed for console/dummy delivery in production; redact reset-link queries from access logs; define token expiry and administrator-assisted recovery. Add failure/delivery tests and consume-token reuse checks. Serialize token verification/password update if concurrent confirmations must be strictly one-time.
- **Blocks school IT production acceptance:** Yes if email recovery is enabled. Keeping it disabled is acceptable only with a tested administrator recovery procedure.

### F09 — Authentication rate limiting does not match the production proxy/worker model

- **Severity:** High. **Classification:** Confirmed security-control weakness.
- **Affected files:** `backend/hub/views.py:79–100,121–156`; `backend/config/settings.py:57–62`; Nginx and systemd examples; installed DRF throttle implementation.
- **Evidence / explanation:** Only application login uses an anonymous throttle, which skips requests from an already authenticated user. Django's default cache is process-local, while Gunicorn runs three workers. No trusted-proxy count is set. DRF uses the full incoming forwarded-for value by default, and Nginx appends to a client-supplied `X-Forwarded-For`; changing the supplied prefix can change the throttle key. Reset request/confirmation and Django admin login have no equivalent application throttle here.
- **Likely impact:** Login limits can vary by worker and be evaded through forwarded-header variation. Enabled recovery can be abused for repeated email requests; admin login is outside this protection.
- **Recommended fix:** Establish the actual trusted proxy chain, sanitize incoming forwarding headers, configure trusted-hop handling, and enforce consistent limits at the proxy and/or a shared backend. Cover application/admin login and recovery; balance shared school-network users against abuse protection.
- **Blocks school IT production acceptance:** Yes for an exposed production login without compensating verified controls.

### F10 — Backup checksums verify original absolute paths, not restored payloads

- **Severity:** High. **Classification:** Confirmed recovery-tool defect.
- **Affected files:** `deploy/scripts/backup.sh` checksum command; `deploy/scripts/restore-verify.sh` checksum check; `docs/RESTORE.md`.
- **Evidence / explanation:** `sha256sum` receives paths such as `$BACKUP_ROOT/.<run>.working/database.dump`, so `SHA256SUMS` contains source absolute filenames when using the production example. Restore runs the checker inside the extracted payload, but absolute entries ignore that directory. Backup cleanup removes the original working directory. On another host verification fails; on the source host, if old source files happen to remain, it can verify them instead of the extracted files.
- **Likely impact:** The documented isolated archive verification cannot reliably validate the recovery set. A success could refer to the wrong bytes.
- **Recommended fix:** Generate checksums inside the payload using relative filenames; reject absolute/traversing checksum entries; verify the extracted files and expected bundle layout; test copying a bundle to a completely different path/host and detecting altered extracted content.
- **Blocks school IT production acceptance:** Yes.

### F11 — Target release and actual restoration have no recorded acceptance evidence

- **Severity:** High. **Classification:** Unverified acceptance items, explicitly acknowledged in documentation.
- **Affected files:** `docs/RESTORE.md`; `docs/RELEASE_CHECKLIST.md`; `docs/DEPLOYMENT.md`; `docs/PROGRESS.md`; `docs/THESIS_EVALUATION.md`.
- **Evidence / explanation:** The restore document explicitly says no school-server restoration has been performed; all release boxes are unchecked. Archive listing/checksums are correctly distinguished from recovery. Slice 10's original checkpoint requires target-like workflow and verified restoration, not only reference artifacts.
- **Likely impact:** Recoverable protected downloads, history, permissions, target migrations, HTTPS/session behavior, and operational ownership remain unproven.
- **Recommended fix:** After fixing F10/F12, perform and record an isolated restore and a target-like full workflow, including unauthorized access and revoked-grant checks. Record actual dates/operators/archive/release identifiers and measured RPO/RTO.
- **Blocks school IT production acceptance:** Yes. Lack of repository evidence does not rule out separately retained school IT records; obtain and verify any such records.

### F12 — Deployment scripts are not executable in Git

- **Severity:** Medium. **Classification:** Confirmed packaging/documentation defect.
- **Affected files:** `deploy/scripts/backup.sh`, `restore-verify.sh`, `release-check.sh`; deployment/restore run commands.
- **Evidence / explanation:** `git ls-files --stage deploy` reports mode `100644` for all three scripts. Documentation invokes them directly and supplies no chmod step. Their line endings are LF, which is appropriate for Linux.
- **Likely impact:** A fresh Linux checkout normally returns Permission denied for the documented commands; backup scheduling can fail immediately.
- **Recommended fix:** Track executable modes or consistently invoke `bash` and document installation permissions. Verify from a fresh Linux checkout.
- **Blocks school IT production acceptance:** Yes until the documented release/backup commands run successfully; remediation is small.

### F13 — Audit coverage and user-facing history are incomplete

- **Severity:** Medium. **Classification:** Confirmed audit/documentation gap.
- **Affected files:** `backend/hub/admin.py`; `backend/hub/views.py:30–31,99–117,155,414,621–637`; `backend/hub/models.py:176–188`; `frontend/src/main.tsx:1603–1644`; management commands.
- **Evidence / explanation:** Account/role changes rely on Django admin logging, not the Hub audit helper. Logout has no Hub event. Auth/password events have `area=None`, so `AuditView` excludes them; Administrator is not an audit read role. A shared-document download is logged against the source area, not the recipient area. Each event gets a new random request ID rather than an actual shared request correlation ID. The UI displays only actor/action/record/time and has no filter controls or access to older than 200 results. CLI close omits a rationale and its help incorrectly says it cannot be reversed in the app; cycle creation is not audited.
- **Likely impact:** Administrators cannot obtain a complete security/access history through the Hub; users cannot inspect action reasons in Audit Trail, and multi-area/request investigation is fragmented.
- **Recommended fix:** Define and implement security-event access separately from academic visibility; unify account/grant/lifecycle logging with safe before/after data, stable entity references and request correlation; handle shared downloads deliberately; expose scoped details, actor/date/entity filters and pagination. Preserve Django admin logs as additional evidence.
- **Blocks school IT production acceptance:** Yes for access-administration/security-event accountability; richer academic UI filters can follow after launch if a documented complete audit access path exists.

### F14 — Compliance exports lack enough context to reproduce the result

- **Severity:** Medium. **Classification:** Confirmed report gap against plan §7.
- **Affected files:** `backend/hub/views.py:534–592`; `frontend/src/main.tsx:1554–1600`; `frontend/src/types.ts`.
- **Evidence / explanation:** CSV includes percentage/completed count and “Your authorized areas,” but not cycle identity, area/status filters, calculated timestamp, total denominator, exclusions, or formula/version. JSON also does not identify applied filters/cycle. Print hides filter controls without adding a filter description. Status filtering changes the summarized population: a Complete-only report naturally shows 100%, which must not be mistaken for whole-cycle readiness. The dashboard accepts only a cycle filter, so it cannot be compared under the same area/status filters directly.
- **Likely impact:** A saved report can be misinterpreted or cannot be reconciled later without remembering the UI state.
- **Recommended fix:** Export and print cycle/instrument, authorized scope, exact filters, numerator/denominator, exclusions, formula version, calculation time/timezone, and a filtered-population label. Add multi-status/area reconciliation tests and explicit same-filter comparison semantics.
- **Blocks school IT production acceptance:** Conditional: yes if exported/printed reports are used as readiness evidence; otherwise fix before that use.

### F15 — Collections are unbounded or silently truncated, with expensive nested queries

- **Severity:** Medium. **Classification:** Confirmed scalability/retrieval weakness.
- **Affected files:** `backend/hub/views.py:193–230,277–355,421–472,595–637`; `backend/hub/compliance.py`; `frontend/src/main.tsx:374–415`; `docs/API.md`.
- **Evidence / explanation:** Most lists return every scoped row/history. Search stops at 50 of each type and Audit at 200 without continuation. `submission_data()` queries the latest submission per serialized record and repeatedly queries area permissions; `doc_data()` runs version permission/mapping checks per record. Each workspace refresh loads all areas, requirements, documents/versions, submissions, summary and audit regardless of screen. Cycle locks serialize all writes within a cycle.
- **Likely impact:** Growing evidence history increases query count, response size and browser memory; old records cannot be reached in capped views; long uploads can delay unrelated cycle writes.
- **Recommended fix:** Add paginated server-filtered collections, visible truncation/continuation, on-demand histories, annotated current-submission IDs and cached-per-request permission scope. Measure query counts and representative data volumes before tightening lock granularity.
- **Blocks school IT production acceptance:** Conditional on expected pilot size/concurrency. At minimum establish and verify a capacity envelope before acceptance.

### F16 — UI requests can display stale data under a different cycle or filter

- **Severity:** Medium. **Classification:** Confirmed UI reliability weakness by source tracing.
- **Affected files:** `frontend/src/main.tsx:317–473,474–491,674–678,1524–1544,1554–1600`.
- **Evidence / explanation:** Workspace refresh has a generation guard, but old lists/summary remain visible until it succeeds. Search, report and detail requests lack that guard/cancellation. Switching cycle does not clear search results or report filters. A report failure retains the previous report; a slower prior report response can overwrite a newer filtered response. Search result document clicks depend on the current preloaded document list and can silently do nothing. Search filters documents by owning cycle, whereas Repository also includes destination-cycle shared documents.
- **Likely impact:** Users can print old-cycle/old-filter results under a new heading, or act on stale context. Backend scope checks still protect mutations, but the displayed state is misleading.
- **Recommended fix:** Key data by user/cycle/filter, clear or visibly mark stale data, reset incompatible filters, and cancel/ignore stale responses. Disable print/export during failed or mismatched loads; fetch search details by ID. Test delayed/error responses and cycle/account switches.
- **Blocks school IT production acceptance:** Yes for report correctness; other navigation refinements can follow once stale reporting is prevented.

### F17 — Upload/submission retry behavior cannot resolve ambiguous network success

- **Severity:** Medium. **Classification:** Confirmed reliability gap.
- **Affected files:** `frontend/src/main.tsx:1926–1975,2075–2109`; `backend/hub/views.py:363–394,448–466`.
- **Evidence / explanation:** Upload, mapping and submission are separate requests. After a known upload success, `UploadForm` remembers it and offers a retry, which is useful. If the server saves an upload/submission but its response is lost, retry can create another version or return “already submitted” without recognizing prior success. The first failure's message uses the previous render's `uploaded` value. Completion closes the modal even if a subsequent workspace refresh reports failure.
- **Likely impact:** Duplicate versions, confusing partial success, or a user repeatedly retrying already completed work. Historical records are retained rather than overwritten.
- **Recommended fix:** Introduce scoped idempotency/request identifiers or a recoverable operation lookup, pin the returned version ID, detect existing submission success, and show file-saved versus submitted versus refresh-failed states distinctly. Test response loss and post-save refresh failures.
- **Blocks school IT production acceptance:** No by itself for a controlled pilot with an explicit recovery procedure; prioritize before frequent real uploads.

### F18 — Malformed IDs can escape validation; identity and input limits need tightening

- **Severity:** Medium. **Classification:** Confirmed input-validation defects/gaps.
- **Affected files:** `backend/hub/views.py:40–50,88–94,297–298,350–354`; `backend/hub/serializers.py`; `backend/hub/models.py:9–14`; `frontend/src/api.ts`.
- **Evidence / explanation:** `query_id()` calls `int()` before its length bound and accepts Unicode `isdigit()` characters that `int()` cannot convert. Read-only direct calls confirmed `ValueError` for a superscript digit and 4,301 digits; these are not DRF validation exceptions. Login uses case-insensitive username/email OR lookup followed by `.first()`, but usernames are only case-sensitively unique and can collide with another user's email. Several search/text/item fields lack explicit application bounds. CSRF bootstrap response status is not checked before parsing in the API wrapper.
- **Likely impact:** Malformed requests can yield 500 instead of useful 400 responses; login identifiers can resolve ambiguously; oversized legitimate-looking input can consume resources; proxy errors produce confusing UI failures.
- **Recommended fix:** Validate ASCII numeric format/length before conversion; define unique login identifier rules and normalize accounts safely; bound query text, free text and item count; return stable errors; check bootstrap status and handle non-JSON/network errors. Add boundary tests. During reset confirmation, validate password similarity using the decoded user as context as password change already does.
- **Blocks school IT production acceptance:** No independently; fix before acceptance as a small reliability/security hardening task.

### F19 — File policy is hard-coded and parsing precedes write-scope validation

- **Severity:** Medium. **Classification:** Confirmed implementation/policy gap.
- **Affected files:** `backend/hub/files.py`; `backend/hub/views.py:363–379`; `backend/config/settings.py:55–56`; Nginx example; upload UI; plan §10.
- **Evidence / explanation:** Code uses 25 MiB and no PPTX, versus the proposed configurable 20 MiB/PPTX policy. UI says 25 MB. `validate_upload()` reads/parses the file before resolving the user's owning-area write permission. No upload-specific request rate or aggregate quota is configured. The application memory-size setting is not itself a complete multipart file request cap; production's Nginx cap is important.
- **Likely impact:** Even a read-only authenticated user can consume file-parser resources before being denied. Format/size expectations may differ from school policy, and storage/worker usage is not bounded per account/cycle.
- **Recommended fix:** Approve the formats/limit and units, make policy configurable, check scope before costly parsing, retain proxy/application safeguards, and set measured quotas/rates. Add valid supported-type and archive/parser-limit tests. Do not introduce PPTX without its format validation.
- **Blocks school IT production acceptance:** Conditional on policy approval and capacity verification; approval of the actual format/size list is required.

### F20 — Storage crash recovery and durable backup operations are not fully specified

- **Severity:** Medium. **Classification:** Confirmed implementation/documentation gap; operational results unverified.
- **Affected files:** `backend/hub/views.py:363–394,406–418`; `deploy/scripts/backup.sh`; `docs/RESTORE.md`; `docs/DEPLOYMENT.md`.
- **Evidence / explanation:** Upload writes directly to its final key and cleans up caught exceptions, but process termination can leave an orphaned/partial file. There is no reconciliation procedure/command comparing version rows, sizes/checksums and disk objects. Backup has second-resolution names, no run lock, and publishes the final archive directly; concurrent same-second runs share a working path, and one failed mkdir's cleanup can remove another run's working directory. The manifest records only time/database, not release/schema identity. The script sources the application credentials, despite the deployment precondition calling for a separate backup role.
- **Likely impact:** Storage defects may stay unnoticed, concurrent backups can interfere, and recovery operators lack precise release/role context. Copying sequentially dumped rows then immutable evidence is reasonable under the current append-only workflow, but concurrent uncommitted uploads may add orphan bytes to a bundle.
- **Recommended fix:** Define staged/atomic file publication and durability requirements; add non-destructive reconciliation with quarantine/reporting, never automatic deletion of referenced evidence. Use unique locked backup runs and atomic archive publication; record release/schema identity; use restricted backup credentials. Test interruption, missing/corrupt files and backup overlap.
- **Blocks school IT production acceptance:** Yes for a verified recovery/reconciliation and backup operation procedure; advanced tooling may follow if a tested safe manual procedure exists.

### F21 — Real-evidence malware/quarantine and sensitivity policy is unapproved

- **Severity:** High. **Classification:** Unverified required policy/control, documented limitation.
- **Affected files:** `backend/hub/files.py`; README; `docs/DEPLOYMENT.md` Preconditions; plan §10; `docs/RELEASE_CHECKLIST.md`.
- **Evidence / explanation:** Format validation is present; scanning/quarantine is not. Documentation correctly discloses this, but no school-approved policy/result is recorded. Downloads are attachments, which limits browser exposure but does not prevent a user opening a malicious supported file. The release checklist does not explicitly include scanning-policy sign-off.
- **Likely impact:** Real institutional files could be accepted/downloaded without the institution's agreed treatment of untrusted content and sensitive information.
- **Recommended fix:** Obtain the school's actual evidence classification, access/retention rules and scanning/quarantine decision. Implement scanning or document an explicitly approved constrained pilot workflow with suitable compensating controls; add the decision to acceptance records.
- **Blocks school IT production acceptance:** Yes before real institutional evidence, per the project's own plan. No legal/privacy approval is inferred.

### F22 — Review and completion dialogs lack the full decision context

- **Severity:** Medium. **Classification:** Confirmed usability/acceptance gap.
- **Affected files:** `backend/hub/views.py:193–207`; `frontend/src/main.tsx:2159–2319`; plan §9.
- **Evidence / explanation:** Review shows title/version/item/requirement and download, but not acceptance criteria, original filename, validity or exact file identity. It defaults to Approve. Certification shows title and consequence but no criteria or supporting-version selection, even though the underlying detail page shows a checklist.
- **Likely impact:** A reviewer starting from the queue can decide without seeing the criteria; a Coordinator can certify without a clear final record of the evidence considered.
- **Recommended fix:** Fetch/render the current criteria and exact pinned evidence, validity, previous relevant decisions and actor context within each dialog; require deliberate outcome selection. Connect completion selection to F05's persisted record.
- **Blocks school IT production acceptance:** Yes for certification context under the plan; queue review context should also be fixed before institutional use.

### F23 — Deadlines do not drive overdue monitoring; displayed timestamps use browser timezone

- **Severity:** Medium. **Classification:** Confirmed planned behavior gap.
- **Affected files:** `backend/hub/models.py:73`; `backend/hub/compliance.py`; `backend/hub/views.py:168–183,523–566`; `frontend/src/main.tsx:60–77,728–887,1632`.
- **Evidence / explanation:** Deadline is stored/displayed but no overdue flag, count, filter or dashboard list exists. Server expiry uses Asia/Manila, while timestamp formatting omits an explicit `timeZone` and uses the browser's location. Date-only deadlines are parsed locally, which avoids simple UTC-date shifts, but timestamps can differ between users.
- **Likely impact:** Staff cannot directly identify missed deadlines as planned, and audit/report timing can be confusing across devices or locations.
- **Recommended fix:** Implement overdue as a separate flag for due, incomplete applicable active work with agreed closed-cycle semantics; add filters/links and tests. Format timestamps explicitly in Asia/Manila and label report timezone.
- **Blocks school IT production acceptance:** Conditional on the approved deadline-monitoring requirements; it is a missing planned deliverable, not an automated-reminder requirement.

### F24 — Accessibility verification is incomplete and some text lacks contrast

- **Severity:** Medium. **Classification:** Confirmed markup/style concerns; assistive-device behavior unverified.
- **Affected files:** `frontend/src/main.tsx:104–131,588–615,659–665`; `frontend/src/styles.css:1–98,1039–1052`; browser layout test.
- **Evidence / explanation:** Native modal dialogs and labelled forms/focus styling are strengths. Dialog titles are not programmatically connected with `aria-labelledby`/`aria-label`; progress bars lack text-equivalent semantics; current navigation lacks `aria-current`, and mobile navigation has no expanded-state association. `small` text uses `#939eaf`: calculated contrast on white is about 2.71:1; the muted variable `#718095` is about 4.02:1. These are below 4.5:1 for ordinary small text. Browser tests check overflow/screenshots, not contrast or screen-reader operation.
- **Likely impact:** Important hints/date/history text can be difficult to read, and dialog/navigation context may be unclear to assistive technology.
- **Recommended fix:** Connect dialog headings, expose progress/state text, improve contrast and navigation semantics, then test keyboard focus/return/Escape, zoom, mobile main workflow and screen readers with representative users.
- **Blocks school IT production acceptance:** Conditional on required accessibility/user acceptance; perform basic keyboard/contrast remediation before launch.

### F25 — Current tests do not substantiate several recorded verification claims

- **Severity:** Medium. **Classification:** Confirmed test coverage/evidence gap.
- **Affected files:** `backend/hub/tests.py`; `frontend/e2e/workflow.spec.ts`; `frontend/playwright.config.ts`; `docs/PROGRESS.md`.
- **Evidence / explanation:** There are 31 backend test methods and three Playwright tests. Password-change “keeps session” uses `force_authenticate`, so it does not prove a real cookie session survives. Recovery “one time” resets once without testing reuse/expiry. No inactive-user test exists despite the planned checkpoint. Health tests success but not database failure. Browser workflow mainly uses Coordinator/Reviewer, not a Custodian's assignment/ownership path. The report browser test checks controls/href, not downloaded CSV content or printed output. No shell/recovery tests or tracked CI gate exists. The oldest whole-suite result cites 24 tests, not the current full suite.
- **Likely impact:** Important edge cases and production control defects can pass unnoticed; historical results can be read as stronger or more current than their evidence.
- **Recommended fix:** Add the focused tests listed in §6, run current suites in an isolated authorized environment, and record exact commit/command/date/count. Use actual session login for cookie-continuity tests and consume/expire tokens in reset tests. Make browser fixtures reproducible in an isolated database/storage set.
- **Blocks school IT production acceptance:** Yes for current isolated regression and target acceptance evidence; not every suggested future test is a blocker.

### F26 — Local preview startup command currently does nothing

- **Severity:** Low. **Classification:** Confirmed documentation/usability defect.
- **Affected files:** `scripts/start-local.ps1`; README Local preview; latest commit `c14e36d`.
- **Evidence / explanation:** Every line of `start-local.ps1` is commented out. README still says this command starts the services and identifies logs/ports.
- **Likely impact:** A fresh demonstrator follows the documented shortcut and gets no running application. The separate Fresh installation/manual-server commands remain useful.
- **Recommended fix:** Correct the README to the manual workflow, or restore a deliberately validated launcher and verify its prerequisite/port behavior. Explain any machine-specific cluster setup separately.
- **Blocks school IT production acceptance:** No for the independent Linux deployment, but it impedes reproducible local demonstrations.

### F27 — Plan, progress, API and evaluation claims need a reconciled baseline

- **Severity:** Medium. **Classification:** Confirmed documentation/scope inconsistency.
- **Affected files:** `docs/MC_Accreditation_Hub.md`; `docs/PROGRESS.md:41–49`; README; `docs/API.md`; `docs/THESIS_EVALUATION.md`; models/routes/UI.
- **Evidence / explanation:** Progress claims all planned slices as artifacts while assignments/packages/snapshots/archive/overdue and cycle/area management screens are missing or simplified. Archive is not a separate flag/action; the UI calls Closed “Archived.” Other differences include Custodian versus Contributor, role strings versus planned Group capabilities, `/api/` versus `/api/v1/`, integer IDs for most exposed entities versus proposed UUIDs, expiration/rejection policies, and format limits. Some are reasonable implementation choices, but they are not recorded as approved changes. Evaluation asks for an audit-filter screenshot that the UI cannot supply. Original source presentations/screenshots/ERD and actual participant results are not included in the tracked repository.
- **Likely impact:** School IT/thesis reviewers cannot tell accepted requirements from implementation omissions. Official acceptance criteria and role expectations may be inconsistent with training.
- **Recommended fix:** Record a requirements/decision matrix, distinguishing approved substitutions, unfinished required scope and explicitly deferred features. Update progress and evaluation artifacts only to claims supported by actual evidence. Supply an implemented ERD, role/state matrix and workflow/acceptance record. Integer IDs alone are not a permission vulnerability; naming/folder choices need no wholesale rewrite.
- **Blocks school IT production acceptance:** Yes for an agreed acceptance baseline; cosmetic architectural differences alone do not block it.

### F28 — Production operations and release automation are incomplete

- **Severity:** Medium. **Classification:** Confirmed reference-tool limits; target controls unverified.
- **Affected files:** `deploy/scripts/release-check.sh`; `deploy/systemd/mc-accreditation-hub.service`; Nginx example; `backend/config/settings.py`; `docs/DEPLOYMENT.md`; `docs/RESTORE.md`.
- **Evidence / explanation:** Release checker accepts deployment warnings at the default warning exit behavior and merely prints `migrate --plan`, so unapplied migrations do not fail the gate. It reinstalls/rebuilds assets, then checks health, but does not run regression tests or prove the running service matches the release. Backup scheduling, encryption, replication verification/failure alerts, log rotation/redaction/retention and rollback steps are not supplied. Health checks the database, not storage/capacity. Admin has no restricted network location in Nginx. HSTS automatically includes subdomains whenever duration is positive, despite the documentation requiring subdomain-policy approval.
- **Likely impact:** “Release checks passed” is not sufficient evidence for the checklist. A school host may run without effective backups/alerts or a practical rollback; unintended HSTS scope and logging need review.
- **Recommended fix:** Make release gates reject unapplied migrations and unaccepted warnings, with explicit handling of approved advisories. Build a recorded release before cutover, verify its running identity, restrict admin per the actual network design, and document backup jobs/alerts/encryption/replication, storage monitoring, log management and rollback. Configure HSTS subdomain inclusion separately after approval. Actual services/accounts/paths must be proven on the target host.
- **Blocks school IT production acceptance:** Yes for these operational controls/evidence; enhanced observability beyond essential alarms can follow later.

### F29 — Maintainability and dependency reproducibility can improve

- **Severity:** Low. **Classification:** Recommendation grounded in current structure.
- **Affected files:** `frontend/src/main.tsx`; `backend/hub/views.py`; `backend/requirements.txt`; `frontend/package.json`; lockfile; repository tooling.
- **Evidence / explanation:** The client is one approximately 2,393-line file; API/workflow/reporting logic occupies one large views module with wildcard imports. Python includes ranged `python-dotenv`/`pypdf` and has no complete dependency lock; frontend has a retained npm lock. There is no lint script, unit/component harness, or tracked CI workflow. Installed dependency compatibility passed `pip check`, but no vulnerability audit was performed.
- **Likely impact:** Future policy changes are harder to review; a fresh Python installation can resolve a different dependency set. These facts do not establish an existing exploitable dependency vulnerability.
- **Recommended fix:** After correctness remediation, extract bounded feature components and domain services without changing behavior, add lint/CI, and establish reproducible Python dependency resolution with a periodic authoritative security-update process.
- **Blocks school IT production acceptance:** No independently; retain exact installed release dependency versions before acceptance.

## 4. Security and Access-Control Review

### Controls that are present

- Session authentication is configured; no frontend authentication tokens are stored in localStorage/sessionStorage. Passwords use Django hashing and validation.
- Login itself is protected by `csrf_protect`; authenticated unsafe APIs use DRF session CSRF checks. The API wrapper bootstraps a fresh CSRF token for mutations, including after login rotation.
- Secure/HTTP-only session cookies and secure CSRF cookies are selected when DEBUG is off. SameSite Lax, nosniff, frame denial, and same-origin referrer policy are configured. HTTPS redirect/HSTS remain environment-controlled.
- Scope helpers deny unrelated-area access. Workflow grants are re-read rather than copied into browser authority. Superuser/Administrator does not implicitly bypass academic review/access rules.
- Roles cannot silently become institution-wide when an area is omitted: role assignments still require a cycle. Model validation rejects an area from another cycle, and reviewer/custodian assignments require an area.
- Uploaded bytes are not publicly served. UUID storage keys, exclusive creation, format/checksum metadata, attachment disposition and private/no-store download headers are present. Proxy examples do not alias private storage.
- PDF/image/Office validation is substantive: it checks content, rejects encrypted/empty PDFs, verifies image format/size and bounds Office archive entry count/expansion with macro/path checks. It does not claim malware removal.
- Review checks the exact version uploader and submitter; one-to-one decisions and cycle/mapping/submission locks prevent competing API decisions. No decision/audit update/delete API exists; workflow models are read-only in admin.
- `.env`, local data, credentials and private-media paths are ignored by Git; those paths were not tracked in the inspected index. Production example values are placeholders. This is not a forensic claim that Git history or an external secret store was comprehensively scanned.

### Remaining boundaries requiring action

F01–F04 and F09 are the key authorization/authentication risks. State-based read policy must accompany object scope: merely belonging to an area is insufficient under the proposed plan. Test both list disclosure and guessed IDs, as well as shared versions and grant revocation during an existing session.

Administration uses Django staff/superuser/model permissions independently of the product's Administrator role. The demo administrator is a superuser. School IT should define the minimal real account-administration permissions and who can grant staff/superuser/scoped academic authority; a product role label must not be mistaken for an admin permission. Standard Django admin logging is present, but a unified auditable recovery/grant procedure is still required (F13/F27/F28).

Recovery should remain disabled until F08/F09 are resolved and delivery/token-log handling is proven. Private reset URLs must not be reproduced in acceptance reports. Format validation, HTTPS, append-only application records and UUIDs are useful controls, but do not establish malware freedom, database-administrator tamper resistance, or legal/privacy approval.

Error handling is mostly DRF validation/403/404 with readable client alerts. The confirmed ID edge cases (F18), bootstrap parsing and failed SMTP/filesystem/refresh paths need targeted handling and tests. No raw SQL based on user input or unescaped HTML rendering was found in the reviewed application; that is a code-inspection result, not a complete injection assessment.

## 5. Data, Backup, and Recovery Review

### Integrity strengths

The initial migration creates the custom user before dependent application tables. Three Hub migrations cover initial schema, cycle closure time and certification. Database constraints protect case-insensitive email uniqueness, area/requirement codes, version numbering, mapping uniqueness, mapping/version submission uniqueness, one decision per submission and required rejection/exclusion reasons. Protected foreign keys retain referenced history. API services validate version-document consistency, dual-scope mapping/submission authority, newer replacement numbering and evidence validity. Application models deny ordinary save/delete of historical records, while Django admin denies workflow edits/deletions and user deletion.

These protections are application-level rather than tamper-proof: queryset/bulk operations or database administrators can bypass model save overrides. Do not remove necessary administrator recovery powers, but control them through procedure and audit. Cross-area/cycle links are deliberately allowed by the API and therefore cannot be called inconsistent rows without first resolving the sharing policy.

Database-independent migration graph/autodetection found no model drift. The normal migration-history check timed out connecting to the configured loopback PostgreSQL database, so applied-state consistency and migrations against a live fresh/restored database remain unverified in this review.

### Required recovery work

F10 is a concrete defect to fix before trusting archive checks. F12 prevents direct documented script execution on a normal Linux checkout. F20/F28 cover safe operations, identity, credentials, reconciliation and recurring execution. The current bundle contains database dump, evidence archive, environment, checksums and a basic manifest; including environment enables recovery but makes the bundle a sensitive secret-bearing artifact. Its protection and replication must be verified, not merely recommended in text.

The restore verifier does not touch a database, which is appropriate. It also extracts the outer archive before validating checksums and only lists the evidence archive. Accept only authenticated school-generated bundles; validate expected layout/path/link safety before extraction into a fresh controlled directory, and verify any externally stored archive checksum/authenticity according to the school's threat model. Archive hashes detect accidental corruption, not authenticity against someone able to replace both files and hashes.

The isolated rehearsal should record:

1. Release commit, migration/schema/dependency versions, archive ID, creation time, integrity results and backup operator.
2. A named empty non-production database and new private storage location, with no production hostname, database or SMTP delivery enabled.
3. Actual database restoration and file extraction, correct ownership/modes, migration consistency, and storage reconciliation against row size/checksum metadata.
4. Authorized login and exact approved-version download with checksum comparison; review and certification support/history; dashboard/report reconciliation; unauthorized and revoked-access denial.
5. Measured recovered-data age/recovery duration against approved RPO/RTO, defects and remediation, operator/date, and school IT acceptance.

Do not call the rehearsal complete from `pg_restore --list`, tar listing or checksums alone. Nightly scheduling, off-host copies, encryption/key recovery, retention, storage growth, deletion/legal-hold requirements and restore-test frequency remain school-owned decisions. Current history is preserved indefinitely by design; archive/deactivation and document retention are not a complete purge policy. No automatic purge should be inferred or introduced without the approved policy.

## 6. Testing and Quality Review

### Existing tests

`backend/hub/tests.py` contains **31 test methods**: 30 workflow tests and one PostgreSQL transaction/concurrency test. Coverage includes upload/version/revision/approval, readiness versus Coordinator completion, completion/reopening rationale and authority, certification/version immutability, anonymous/unrelated-area denial, shared submitted versions, source/destination scope checks, Administrator separation, self-review, duplicate/stale decisions, rejection reasons, mandatory items, exclusion/N/A, expiry, closed-cycle writes/downloads, login/logout CSRF, password change/reset, cycle lifecycle, invalid IDs/methods, CSV formula neutralization, scoped search/report/audit, and public health success.

`frontend/e2e/workflow.spec.ts` contains **three tests**: login/mobile overflow, search/report controls, and a create/upload/revise/new-version/approve/certify/reopen flow with Coordinator/Reviewer sessions and dashboard count changes. It depends on running services, seeded local credentials and a sample PDF, takes screenshots, and persists synthetic workflow data. Its “Figma” test name does not prove matching the inaccessible Figma site.

### Checks actually run on 2026-09-17

| Check | Result and limitation |
|---|---|
| `python -B backend/manage.py check` | Passed: no system-check issues. Does not prove workflow or database availability. |
| `python -B backend/manage.py makemigrations --check --dry-run` | Exit 0 / No changes detected, **with a PostgreSQL connection-timeout warning**. Live migration-history consistency was not verified. |
| In-memory migration loader/autodetector comparison | Passed: no model/migration drift; graph contained 21 total nodes, including Django migrations. Did not connect to or apply migrations to a database. |
| `node frontend/node_modules/typescript/bin/tsc --project frontend/tsconfig.json --noEmit --incremental false` | Passed. No emitted files or build-info update. This is a type check, not lint. |
| Vite production bundle using the installed React plugin and `build.write=false` | Passed with Vite 7.3.6; 1,580 modules transformed. Config file loading was disabled to avoid temporary config writes; equivalent React/root build inputs were supplied. No dist files written. **The exact `npm run build` command was not run.** |
| Python AST parsing | Passed for 24 backend/script Python files. Syntax verification only. |
| `python -B -m pip check` | Passed: no broken installed requirements. Not a vulnerability/security-support audit. |
| Direct `query_id()` boundary diagnostics, without database calls | Confirmed uncaught `ValueError` for superscript digit and 4,301-digit inputs (F18). |
| `check --deploy` with temporary DEBUG-off / HTTPS redirect / one-day HSTS flags | One `security.W021` HSTS-preload advisory; command exited 0. This was not a target-host test. Preload requires explicit domain/subdomain approval and should not be enabled merely to silence this advisory. |
| Django integration suite / Playwright suite / restore scripts / target Nginx/systemd | Not run in this review. Tests write data; deployment/recovery execution would exceed the read-only scope. No Linux shell was available through the inspected command inventory. |
| Lint | No lint script/configuration found; no lint result claimed. |

`PROGRESS.md` records backend/browser/build and focused checks on 2026-09-09. Those remain historical reported results, not current executions or target-school verification. During this review, failed diagnostic quoting attempts were corrected where their result mattered; they are not test failures in the application.

### Test priorities

Before acceptance, test F01–F03 against real PostgreSQL-backed API requests; add visible/hidden version search tests and a role/state/ownership matrix. Exercise real sessions for inactive-user denial, logout/password-change continuity, grant removal, admin restrictions and CSRF. Test true one-time token reuse/expiry, SMTP failure and delivery configuration without logging tokens.

After the approved workflow is settled, test requirement assignment/deactivation, criteria changes while pending/complete, pinned certification support, applicability/archive transitions, pending replacement/withdraw semantics and status precedence. Check nontrivial area/status report populations, all formula prefixes, export metadata and count reconciliation.

Use an isolated synthetic database/storage environment for browser flows including Custodian, Viewer and multi-scope users. Add delayed/error/ambiguous-success responses, stale report printing prevention, pinned review criteria, keyboard/mobile flows and basic automated accessibility checks. Backend boundary tests should include successful supported uploads, encrypted/oversized/expansion/macro/path cases, failed file/database operations and reconciliation. Linux tests should cover fresh-checkout script execution, portable checksum verification, corrupt/missing payloads, concurrent backup attempts and full recorded restoration.

An automated CI gate is recommended for isolated integration/type/build checks, migration drift and Linux shell tooling. Expand tests because these risks exist, not simply to mirror implementation details.

## 7. Deployment and School IT Acceptance Review

All twelve items in `docs/RELEASE_CHECKLIST.md` remain unchecked in the repository. Their disposition is:

| Release checklist item | Evidence needed / remaining work |
|---|---|
| School IT infrastructure/ownership approval | Actual hostname, DNS/TLS owner, firewall, service account, database/backup roles, private mount, backup target, retention, RPO/RTO and incident owner. No recorded sign-off. |
| Production secrets, DEBUG, allowed hosts/CSRF | Populate protected environment through IT's secret process; verify running values without printing secrets; ensure no development `.env` overrides/leaks. Examples alone are insufficient. |
| Deployment checks/warnings | Run on the actual release environment; fix real warnings and record deliberate HSTS-preload/subdomain decisions. Repair the gate behavior in F28. |
| Migrations/static/frontend release | Fresh/restored PostgreSQL migration evidence, collectstatic, locked npm install/build, appropriate filesystem read permissions and recorded deployed commit/dependencies. |
| Nginx/HTTPS/health | Validate actual Nginx configuration/certificates/redirects/headers; prove service startup and health. No target execution recorded. |
| Login/refresh/logout/scoped and denied URLs | Run target browser checks with the approved role/state/assignment policy, including inactive users and grant revocation. |
| Protected attachment and guessed URL denial | Verify correct pinned file, safe headers/no-store, storage mode, no public aliases and every role/state boundary. |
| Closed-cycle writes/reopen/audit | Verify all ordinary writes and authorized lifecycle scope after F01; cover cross-cycle reuse policy and audit rationale. |
| Backup/checksums/off-host replication | Fix F10/F12; verify scheduled backup, secret/evidence protection, successful checksums, separate failure-domain copy and alerts. |
| Separate-environment restoration | Perform the actual rehearsal in §5 and retain dated results; archive structure verification is not enough. |
| Recovery email or administrator recovery | Keep disabled or resolve F08/F09 and prove actual SMTP delivery, token safety and reset behavior. Record administrator identity-verification/recovery steps. |
| Limitations/evaluation briefing | Supply reconciled role/workflow limitations, synthetic-data boundaries, approved evidence policy and actual evaluation protocol; do not imply official accreditation scoring. |

Additional required inputs or missing acceptance controls:

- Approve the official cycle/area/requirement instrument, program scope and criteria; no synthetic seed is official content.
- Resolve cross-area/cycle sharing, draft visibility, Custodian versus Contributor duties, requirement assignment, who can certify, and who can control an entire cycle. Approve package versus item-level submissions and the completion/expiry/replacement semantics.
- Decide accepted formats/configurable limit, real evidence sensitivity, malware/quarantine workflow, retention/deletion/legal-hold handling, and authorized administrative access. These decisions require school authority; no legal/privacy conclusion is made here.
- Confirm actual supported OS/runtime/PostgreSQL versions, CPU/RAM/storage, mount durability, user counts/concurrency/upload volumes, domain/network exposure, admin network restriction and minimum demonstrated capacity.
- Establish environment ownership/modes and distinct application/backup/deployment privileges. The reference layout is an example, not proof that the service account can write private storage or Nginx can read builds/static files.
- Configure recurring backup, encryption and recoverable keys, off-host replication/checking, backup/storage/service failure alerts, log redaction/rotation/retention, incident escalation, patching and change/rollback procedure.
- Approve HSTS scope separately from duration/preload; configure trusted proxy handling and rate limits against the actual chain.
- Complete current isolated regressions, full target-like synthetic workflow, real cookie/HTTPS checks, representative keyboard/mobile testing and the restore evidence packet.

SMTP, domain details and private-cloud classification are unresolved inputs, not authority to provision or deploy. The repository does not contain school-server, legal, privacy, or production approval.

## 8. Prioritized Improvement Roadmap

Priority P0 means an acceptance blocker; P1 means the next operational/correctness work; P2 means useful later improvement. Effort is relative: Small is a bounded correction/procedure, Medium spans several modules or operational checks, Large changes the domain workflow or requires coordinated implementation. These are not calendar commitments.

### Before production acceptance

| Recommendation / findings | Effort | Priority | Dependencies | Expected benefit |
|---|---|---|---|---|
| Approve and reconcile the requirements/access/workflow baseline (F04/F07/F19/F21/F27) | Medium | P0 | School academic owner and IT decisions | Prevents building/accepting the wrong workflow; clarifies required versus deferred scope. |
| Restrict lifecycle authority to explicit cycle management (F01) | Small | P0 | Agreed lifecycle capability | Stops one-area users controlling unrelated work. |
| Enforce role/state/ownership visibility and fix hidden-version search (F02/F03) | Medium | P0 | Approved visibility/sharing matrix | Protects drafts and metadata consistently across lists/search/downloads. |
| Implement assignments if retained in baseline (F04) | Large | P0 | Responsible-user/teamwork decision; visibility policy | Enforceable accountability and assigned-contributor workflow. |
| Pin certification evidence/criteria and enforce substantive-change history (F05/F06/F22) | Large | P0 | Approved completion/replacement rules | Defensible, recoverable completion decisions tied to exact evidence. |
| Complete package transitions or verify the approved item-level substitute (F07) | Large | P0 | Workflow decision; assignments/criteria revisions; an approved item-level substitute would reduce effort | Aligns user actions, status semantics and acceptance tests. |
| Correct portable checksum checks and Linux script invocation (F10/F12) | Small | P0 | No policy dependency | Makes bundle verification run against recovered bytes. |
| Establish backup execution/protection/reconciliation and perform actual isolated recovery (F11/F20/F28) | Medium | P0 | Fixed scripts; IT roles/targets/keys; RPO/RTO | Demonstrates evidence and history can be recovered safely. |
| Fix trusted proxy/rate-limit controls and restrict real admin access (F09/F28) | Medium | P0 | Actual network/proxy chain and admin policy | Consistent abuse protection and administrative boundary. |
| Keep recovery disabled or fix SMTP/token logging and prove it (F08/F25) | Medium | P0 when enabled | School SMTP/URL and log policy | Reliable recovery without reset-token leakage. |
| Make security/account/grant/lifecycle history accessible and complete (F13) | Medium | P0 | Audit access/retention policy | Investigable access changes and recovery actions. |
| Prevent stale reporting and add export/print provenance (F14/F16) | Medium | P0 for readiness reports | Approved report filter semantics | Prevents old/mislabelled readiness evidence. |
| Approve and enforce the real-file scanning/quarantine policy (F21) | Medium | P0 | School evidence/security owner; a new scanning pipeline would require separate sizing | Controlled treatment of untrusted real evidence. |
| Fix malformed identifiers, input bounds and basic decision/accessibility context (F18/F22/F24) | Medium | P1 before launch | UI and identity decisions | Useful errors, safer decisions and usable core forms. |
| Deliver agreed overdue/archive/admin gaps or explicitly amend acceptance scope (F23/F27) | Medium | P0 if required by approved baseline | Requirements owner | Honest plan completion and lifecycle/deadline behavior. |
| Run isolated current regressions and target release checklist; record actual evidence (F11/F25/F28) | Medium | P0 | All blocker fixes; IT test environment | Replaces artifact/historical claims with current acceptance evidence. |
| Verify pilot capacity and minimum operational alarms/rollback (F15/F28) | Medium | P0 | User/load/storage estimates and service owners | Prevents an unsupported launch size and unobserved service/backup failures. |

### First 30 days after launch

This phase begins only after the P0 gates are satisfied or expressly resolved by the approved requirements baseline.

| Recommendation / findings | Effort | Priority | Dependencies | Expected benefit |
|---|---|---|---|---|
| Paginate/on-demand histories and reduce permission/current-record query amplification (F15) | Medium | P1; move before launch if capacity check fails | Measured query/load profile | Stable growth and access to older records. |
| Resolve ambiguous upload/submission retries with idempotency and explicit success states (F17) | Medium | P1 | Stable submission API/workflow | Fewer duplicate versions and failed-looking successes. |
| Finish audit UI filtering/details/date/entity navigation (F13) | Medium | P1 | Complete audit data/access path | Faster support and academic history investigation. |
| Strengthen storage integrity checks and recurring restore exercises (F20/F28) | Medium | P1 | Verified backup/reconciliation procedure | Earlier detection of missing/corrupt evidence and recovery regressions. |
| Expand keyboard/mobile/accessibility and realistic role browser coverage (F24/F25) | Medium | P1 | Approved roles and working core flow | More reliable use by actual school staff. |
| Establish CI/lint/dependency reproducibility and update cadence (F25/F29) | Medium | P1 | Isolated test infrastructure and release process | Reviewable changes and repeatable future releases. |
| Correct the inactive local launcher/documentation and reproducible demo fixtures (F26/F25) | Small | P1 | Agreed local service startup approach | Dependable demonstrations and regression reproduction. |
| Collect real pilot task/usability measurements and refresh training/documentation (F27) | Medium | P1 | School evaluation approval and participants | Priorities grounded in actual user experience rather than invented scores. |

### Future enhancements

| Recommendation | Effort | Priority | Dependencies | Expected benefit |
|---|---|---|---|---|
| Incrementally extract frontend features and backend domain services (F29) | Medium | P2 | Regression gates; correctness fixes | Easier review and safer policy changes. |
| Richer cycle/area administration and analytics beyond approved version-1 scope | Large | P2 | Explicit scope extension and users' needs | Less server intervention and useful additional monitoring. |
| Two-factor/SSO or stronger identity controls if institution requires them | Large | P2, or earlier if IT mandates | Identity policy/provider and recovery design | Stronger account protection. |
| Approved reminders/notifications, cross-system integrations, or bulk exports | Large | P2 | Explicit scope, delivery/data-sharing policies | Reduced manual coordination. |
| OCR/full-document search, AI classification, inline previews, signatures or external accreditor access | Large | P2 | Explicit requirements, separate security/visibility design and evaluation | New capabilities only after core access/history/recovery is dependable. |

Deferred features are not acceptance defects merely because they are absent. Do not use this roadmap as authorization to implement or deploy them.

## 9. Final Verdict

**Not ready, with listed blockers.** The prototype is coherent enough for school IT to examine, but current code and reference artifacts do not establish production acceptance. The blocking groups are lifecycle/visibility/search authority (F01–F03/F09), an approved assignment/submission/criteria/certification baseline and its required implementation (F04–F07/F22/F27), portable and proven recovery (F10–F12/F20), security-event accountability (F13), trustworthy report context/state (F14/F16), real-file policy (F21), and current target/regression/operations evidence (F11/F25/F28). Email recovery adds F08 if enabled. Capacity, format/limit, overdue/archive and accessibility decisions must be resolved against the school's approved requirements; they cannot be silently treated as completed or deferred.

### Next actions for the project owner

- [ ] Review F01–F10 with the implementer and assign the confirmed defects for focused fixes.
- [ ] Obtain academic/IT decisions on visibility/sharing, assignments, submissions, certification criteria/evidence, formats, scanning, and required archive/deadline scope; record the accepted baseline.
- [ ] Fix portable checksum verification and script invocation, then establish restricted recurring backups and off-host replication.
- [ ] Keep recovery email disabled until SMTP delivery, rate limits, token logging and administrator recovery are verified.
- [ ] Run the current tests in an isolated authorized database/storage environment; add the blocker regression cases and preserve exact release results.
- [ ] Have school IT complete the target release checklist and actual isolated restoration with downloaded-version/history/checksum evidence and measured recovery outcomes.
- [ ] Update progress/training/thesis records to the verified baseline, resolve remaining blockers, and request school IT acceptance with that evidence packet.
