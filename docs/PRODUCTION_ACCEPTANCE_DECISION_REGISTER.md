# Production Acceptance Decision Register

Prepared: 2026-09-17

Status: **D01–D06 are Provisional Project Owner Decision — formal approval pending. All other decisions remain Pending Decision.**

Formal approver names, approval dates and sign-off evidence: **Not recorded**. D01–D06's selected options are recorded below as provisional Project Owner direction only.

## Purpose and authority

This register translates the P0 blockers and conditional acceptance decisions in [the system review](SYSTEM_REVIEW_AND_IMPROVEMENT_PLAN.md) into choices for the project owner and school IT. It also covers the specifically requested F19/F23 decisions. The sources are [the proposed implementation plan](MC_Accreditation_Hub.md) and [the progress record](PROGRESS.md). Existing-system descriptions come from the review; this document is not a new code audit or a claim that a finding has been fixed.

Recommendations are proposals, not approved school policy. The Project Owner coordinates scope and delivery; the Academic Owner approves academic workflow and instrument requirements; School IT approves operating environments and release evidence; the Security/Records Owner approves evidence visibility, sensitivity, retention and security controls. Where multiple approvers are listed, each must approve their part. These are required approval roles proposed by this register, not claims about named officials or an established school approval process.

An approved option resolves a choice, not the underlying implementation or acceptance test. Findings remain open until the selected behavior is implemented and verified, or an explicit scope amendment defines an acceptable substitute. Real institutional uploads and production acceptance remain blocked by the review's unresolved gates. No application, deployment, database or infrastructure change is authorized by this documentation-only checkpoint.

## Decision index

| Decision | Question | Review findings | Status |
|---|---|---|---|
| D01 | Who can close/reopen the entire cycle? | F01 | Provisional Project Owner Decision — formal approval pending |
| D02 | Who can read drafts, submitted work and approved evidence? | F02, F04 | Provisional Project Owner Decision — formal approval pending |
| D03 | May evidence cross area/cycle boundaries, and which versions may be searched? | F03, F02, F27 | Provisional Project Owner Decision — formal approval pending |
| D04 | Are submissions assigned to specific people or an area team? | F04 | Provisional Project Owner Decision — formal approval pending |
| D05 | What evidence and criteria must a certification preserve? | F05, F22 | Provisional Project Owner Decision — formal approval pending |
| D06 | What requires reopening or a new criteria/applicability decision? | F06, F05 | Provisional Project Owner Decision — formal approval pending |
| D07 | Are submissions requirement packages or individual mapped versions? | F07, F04, F22 | Provisional Project Owner Decision — formal approval pending |
| D08 | What does evidence validity/expiry affect? | F06, F07, F27 | Pending Decision |
| D09 | Who may inspect academic and security audit history? | F13 | Pending Decision |
| D10 | Which file formats, size units and resource limits are accepted? | F19 | Pending Decision |
| D11 | How are real files scanned/quarantined? | F21, F19 | Pending Decision |
| D12 | Which records may be accepted, retained and eventually disposed of? | F21, F13, F20 | Pending Decision |
| D13 | How are overdue deadlines and timestamps calculated/displayed? | F23 | Pending Decision |
| D14 | Is archive distinct from closure, draft and non-applicability? | F27, F23 | Pending Decision |
| D15 | Which account/cycle/area administration tools are required at launch? | F27, F13, F09 | Pending Decision |
| D16 | Which revised requirements constitute the acceptance baseline? | F27, F01–F07 | Pending Decision |
| D17 | Is recovery administrator-assisted or institutionally emailed? | F08, F25 | Pending Decision |
| D18 | What network/proxy/admin exposure model will IT operate? | F09, F28 | Pending Decision |
| D19 | Who owns recurring backups, recovery and operational records? | F11, F20, F28 | Pending Decision |
| D20 | What pilot capacity and operating controls must be proven? | F15, F28 | Pending Decision |
| D21 | What population does a filtered readiness report measure? | F14, F16 | Pending Decision |
| D22 | Where and how will acceptance evidence be collected? | F11, F25, F28 | Pending Decision |

F10/F12 are policy-independent technical fixes listed separately below. F22's decision context is covered by D05/D07. F16's stale-response defect is not an option to accept misleading reports: D21 determines report semantics, while correctness must be repaired whichever option is chosen. Similarly, D03 does not permit search to match inaccessible versions under any option.

## Access and academic workflow decisions

### D01 — Cycle-wide lifecycle authority

**Status:** Provisional Project Owner Decision — formal approval pending. **Selected provisional option:** A. **Finding:** F01. **Decision to make:** Who may change the state of the entire cycle, including areas outside their own grant?

| Option | Effect on the existing system | Code changes required? |
|---|---|---|
| A. Require a cycle-wide Coordinator grant | Area-only Coordinators keep their area duties but lose global close/reopen controls. Reasons and auditing remain mandatory. | Yes: API/UI permission flags and negative scope tests. |
| B. Introduce a separate cycle-management capability | Explicitly designated managers can close/reopen without inheriting academic review powers; Coordinator alone is insufficient. | Yes: capability/grant design, administration and checks. |
| C. Give every area Coordinator cycle-wide lifecycle authority | Retains the reviewed behavior; the scope matrix and training must explicitly warn that one area's Coordinator can halt/resume all areas. | No permission restriction; documentation and explicit acceptance tests required. |

**Recommended option:** A. It uses existing cycle-wide grants and keeps lifecycle authority aligned with its impact. **Required approver:** Academic Owner; Project Owner. **Production-acceptance impact:** F01 remains a blocker until the authority is approved and tested. Option C is a substantive delegation of global authority, not merely a technical convenience.

### D02 — Evidence visibility by role, state and ownership

**Status:** Provisional Project Owner Decision — formal approval pending. **Selected provisional option:** A. **Finding:** F02, with F04. **Decision to make:** Which drafts/history/files may each role see within its authorized scope?

| Option | Effect on the existing system | Code changes required? |
|---|---|---|
| A. Use the plan's visibility boundaries | Contributors/Custodians read their own drafts/submissions and approved shared evidence; Reviewers read submitted review/history context; Viewers read approved evidence; scoped Coordinators manage/review their scope. Academic Administrator access still requires explicit grants. | Yes: one policy for lists, versions, history, search, counts and downloads. |
| B. Allow area-team draft collaboration but keep Viewers approval-only | Authorized team writers can read/edit team drafts under D04; Reviewers see submitted work, not arbitrary private drafts. | Yes: team/ownership checks and role-state filtering. |
| C. Allow every area reader to inspect all versions and decisions | Retains broad owning-area read access, including unsubmitted/rejected documents. School approval must explicitly cover sensitive drafts and reviewer/Viewer exposure. | No state restriction for source-area reads; scope/search consistency and tests still required. |

**Recommended option:** A, because it matches the proposed privacy boundary. **Required approver:** Security/Records Owner; Academic Owner. **Production-acceptance impact:** Blocks real evidence until an approved visibility matrix is enforced. Define visibility of withdrawn/revision-requested history and mixed approved/draft versions explicitly; no recommendation grants global evidence access to administrators.

### D03 — Sharing boundaries and search visibility

**Status:** Provisional Project Owner Decision — formal approval pending. **Selected provisional option:** A. **Findings:** F03, F02, F27. **Decision to make:** May selected evidence be reused outside its owning area/cycle?

| Option | Effect on the existing system | Code changes required? |
|---|---|---|
| A. Same-area, same-cycle reuse only | Brings new mapping/submission actions back to the proposed version-1 boundary. Existing cross-scope history must be preserved and its continued read access decided explicitly, not deleted. | Yes: mapping/submission restrictions, legacy handling and search regression fix. |
| B. Same-cycle cross-area reuse of explicitly submitted versions | Retains controlled sharing within a cycle; requires write authority at source/destination and recipient visibility under D02. Future drafts never inherit access. | Yes: cross-cycle rejection, shared-version search filtering and consistent repository/search scope. |
| C. Cross-area and cross-cycle reuse of explicitly selected versions | Retains the broadest current reuse capability, but new-cycle review/certification remains independent; old decisions never transfer. | Yes: search filtering/consistency and fully tested sharing rules, even if current mapping checks are retained. |

**Recommended option:** A until sharing is expressly needed and approved. **Required approver:** Security/Records Owner; Academic Owner. **Production-acceptance impact:** Sharing policy is unresolved. F03's hidden-filename leak must be fixed for every option; its correctness requirement needs no permission to expose hidden metadata. Metadata, search matches and downloads must have the same selected-version boundary.

### Provisional D01–D03 access-control matrix

This is the single implementation matrix for the current F01–F03 checkpoint. It is a Project Owner direction, **not** formal Academic Owner or Security/Records Owner sign-off. Grants are additive; multiple grants provide the union of the applicable rows. An Administrator has no implicit academic evidence access.

| Role within its explicit grant scope | Draft / unsubmitted version | Submitted version | Approved version | Submission/review history | Lifecycle and new reuse |
|---|---|---|---|---|---|
| Cycle-wide Coordinator | Read, download, and manage | Read, download, and review | Read and download | Read in scope | Only a grant with `area=null` may close/reopen the cycle; new mappings/submissions stay in the same area/cycle. |
| Area Coordinator | Read, download, and manage in the area | Read, download, and review in the area | Read and download in the area | Read in area | Cannot close/reopen the whole cycle; new mappings/submissions stay in the same area/cycle. |
| Reviewer | Hidden | Read/download only once submitted to the reviewer’s area | Read/download | Read submitted-review context in area | Cannot create mappings/submissions or change lifecycle. |
| Custodian (current Contributor role) | Own document, upload, or own submission only | Own document/submission | Own work plus approved shared evidence | Own document/submission only | D04's assignment and stewardship boundaries are provisional; new mappings/submissions must be same-area/same-cycle. |
| Viewer | Hidden | Hidden | Read/download approved evidence only | Hidden | Read-only; cannot create mappings/submissions or change lifecycle. |

Existing cross-area/cross-cycle mappings and immutable submissions are preserved. A recipient may retain access only through the corresponding historical submitted/approved visibility rule above; no new mapping or submission may extend that legacy relationship. All document lists, document detail/version history, mapping/submission/review lists, search filename matching, download authorization, and frontend displays use this matrix. Requirement/dashboard/report scope remains area-grant based; it does not expose hidden filenames or evidence-version history.

### D04 — Requirement assignments and document stewardship

**Status:** Provisional Project Owner Decision — formal approval pending. **Selected provisional option:** A. **Finding:** F04. **Decision to make:** Who may submit work and replace another contributor's current evidence?

| Option | Effect on the existing system | Code changes required? |
|---|---|---|
| A. Assign one or more active authorized users per requirement | Only assignees submit; each document has an owner/steward. Coordinator reassignment/delegation is explicit and audited; owning-area access alone is insufficient to replace a colleague's work. | Yes: assignment model/API/UI, user-scope validation, ownership/reassignment checks and filters. |
| B. Treat all authorized area writers as the responsible team | Keeps area-wide writing/submission; free-text responsible label becomes a team label rather than an individual assignment. Define whether all team members can replace any team document. | No assignment model required; D02 checks, stewardship rules, audit and scope-documentation changes may still require code. |
| C. Assign users for accountability but retain shared team submission authority | Adds named responsibility without using it as the submission permission boundary; UI must label that distinction clearly. | Yes: assignment records/UI, while area write authority remains. |

**Selected provisional option:** A. Each requirement may have one or more active, exact-area/cycle-authorized Custodian assignees. New documents require a requirement context and record their steward; legacy documents remain honestly unassigned until a scoped Coordinator delegates stewardship. Assignees may upload, map, and submit their own stewarded work. A scoped Coordinator may explicitly assign/reassign or delegate stewardship with a required reason and audit event, and may make a one-action override only with a required reason and audit event. Area membership alone does not permit replacing another person's work. **Required approver:** Academic Owner; Project Owner. **Production-acceptance impact:** This is implemented as a provisional Project Owner direction only. Formal Academic Owner approval, target-environment testing, and confirmation of the Custodian/Contributor role mapping remain required before real evidence use.

### D05 — Certification support and historical evidence

**Status:** Provisional Project Owner Decision — formal approval pending. **Selected option:** A. **Findings:** F05, F22. **Decision:** A Coordinator deliberately selects approved supporting submissions; the certification retains immutable submission/version references and a criteria snapshot.

| Option | Effect on the existing system | Code changes required? |
|---|---|---|
| A. Coordinator selects approved supporting submissions | Completion form shows criteria and exact versions; records immutable submission references, criteria/revision snapshot, actor, rationale and time. | Yes: history relationships/migration, validation, form context and tests. |
| B. System proposes the qualifying approved set; Coordinator explicitly confirms it | Same durable snapshot/references as A, but the system assembles a visible selection covering mandatory items before confirmation. | Yes: the same persistence safeguards plus deterministic selection/confirmation. |

**Provisional legacy handling:** Preserve and label pre-F05 certification rows without pinned support. Exclude them from the compliance numerator. A scoped Coordinator may create a new auditable certification against deliberately selected current approved evidence and a current criteria snapshot; never infer or backfill old support or rewrite the old row. **Required approver:** Academic Owner; Security/Records Owner for historical record handling. **Production-acceptance impact:** This is implemented as provisional Project Owner direction only; formal approvals and target-environment verification remain required.

### D06 — Criteria changes, replacements and applicability decisions

**Status:** Provisional Project Owner Decision — formal approval pending. **Selected option:** A. **Finding:** F06, dependent on D05. **Decision:** Documented reopen before substantive criteria or supporting-evidence changes; rationale-backed applicability decisions retain history.

| Option | Effect on the existing system | Code changes required? |
|---|---|---|
| A. Reopen before substantive criteria or supporting-evidence replacement | Harmless repository drafts and editorial corrections do not invalidate certification. Substantive criteria get a revision/snapshot; stale pending work cannot be approved. Complete/Reopen/Applicable/Not Applicable are rationale-backed history actions. | Yes: guarded transitions, revision tracking, append-only applicability and UI. |
| B. Preserve completion of a pinned baseline while newer work is assessed separately | Certification stays effective for its D05 snapshot; new criteria/evidence is shown as a separate uncertified revision, not silently presented as the certified baseline. Applicability still has recorded decisions. | Yes: parallel revision/effective-baseline model and separate readiness display. |

**Provisional boundary:** Description/acceptance text, activation, applicability/exclusion reason, new mapping/submission, and review decisions require reopening while the latest certification is `complete`; title, code, responsible office, and deadline remain editorial. A draft version upload remains allowed. Description changes after reopening increment the criteria revision and retain a reason in audit history. Every applicability transition requires a Coordinator reason and an append-only decision. **Required approver:** Academic Owner; Security/Records Owner for record treatment. **Production-acceptance impact:** These semantics remain provisional until formally approved and tested in the target environment.

### D07 — Submission unit, transitions and dashboard states

**Status:** Provisional Project Owner Decision — formal approval pending. **Selected option:** A. **Finding:** F07, dependent on D04–D06. **Decision:** New work uses requirement-level package attempts with draft editing, pinned evidence items, explicit submission, confirmed withdrawal, immutable terminal attempts, and resubmission through a new draft. Only one package per requirement may await review.

| Option | Effect on the existing system | Code changes required? |
|---|---|---|
| A. Deliver planned package attempts | Add draft editing/notes/pinned items, submit, confirmed withdrawal, immutable terminal attempts and resubmission as a new draft; one pending package per requirement. Use the plan's status order, including Needs revision and In progress. | Yes: substantial models, migrations, services, API/editor/review and tests. |
| B. Formally adopt item-level attempts with explicit history transitions | Retain mapping/version review, add deliberate withdrawal/resubmission/supersession records and a defined pending-replacement rule. Publish a complete item-to-requirement status table, including missing-plus-pending behavior and draft work. | Yes: narrower transition/history/UI work; amended plan and acceptance tests. |
| C. Retain current newer-version supersession as the accepted workflow | No package editor/withdraw action; old pending submissions become historical and unreviewable. Missing-plus-pending remains For Compliance; repository drafts do not imply In progress. Those limits must be explicit in training and scope. | No package model required; criteria/certification/visibility fixes and verification still required. |

**Provisional state and precedence rule:** Drafts may be edited or deleted by their owner before submission. Submission pins a nonempty set of exact versions and the current criteria revision. A submitted attempt may be approved or returned for revisions by an independent reviewer, or withdrawn by its submitter before review; these are terminal attempts. Resubmission starts a new draft, optionally copying pinned item choices. For active applicable requirements, the ordered status rule is Complete, For verification (any submitted package, even with missing mandatory items), Needs revision (latest non-withdrawn attempt requested revisions), Ready for completion review (qualifying approved package), In progress (draft or reopened work), then Missing. Draft and Not Applicable remain outside that ordered set.

Requirement-level readiness may reflect draft work in aggregate, while item-level detail follows the existing D02/D03 evidence visibility boundary: a Reviewer or Viewer does not see another user's hidden draft item choices.

**Reject rule proposed, Academic Owner decision pending:** Reject stays distinct from Request revisions in preserved pre-F07 item-level decisions. The proposed new-package rule is to leave Reject unavailable until the Academic Owner defines whether a rejected package can seed a new draft and how it appears in readiness counts. It is not silently mapped to `revisions_requested` or `needs_revision`. **Required approver:** Academic Owner. **Production-acceptance impact:** D07 Option A remains provisional Project Owner direction; formal Academic Owner approval and target workflow verification are required before real evidence use.

### D08 — Evidence validity and expiry

**Status:** Pending Decision. **Findings:** F06, F07, F27. **Decision to make:** Does a validity date affect submission, approval/readiness, or an already recorded completion?

| Option | Effect on the existing system | Code changes required? |
|---|---|---|
| A. No automatic expiry rules in version 1 | Validity is metadata; Coordinator review/reopening decides fitness. Removes the current automatic expiry-based submission/approval/readiness rules, while preserving recorded dates/history. | Yes: validation/status changes and tests. |
| B. Expiry gates new submission/approval/readiness, but not pinned certification | Adopts the current basic rule: valid through the inclusive date in Asia/Manila; recorded completion remains effective until a Coordinator reopens. Explain expired current evidence separately from D05's certification support. | Core expiry rule can remain; snapshot/context and policy-documentation changes required. |
| C. Expiry removes effective completion or forces recertification | Adds an automatic completion-impact rule beyond the plan; must record effective-state history and report dates rather than silently rewrite certification. | Yes: new assessment/expiry semantics, display, auditing and tests. |

**Recommended option:** A until the Academic Owner agrees a validity policy, as the plan explicitly defers automatic expiry. **Required approver:** Academic Owner; Security/Records Owner. **Production-acceptance impact:** Current expiry behavior is not an approved policy simply because it is implemented. B is a concrete lower-change alternative; whichever is chosen must reconcile dashboards, reports, closed-cycle snapshots and D06 replacement rules.

## Records, file handling and scope decisions

### D09 — Audit access, content and completeness

**Status:** Pending Decision. **Finding:** F13. **Decision to make:** Who can inspect security/account events and detailed academic decision history, including cross-area events?

| Option | Effect on the existing system | Code changes required? |
|---|---|---|
| A. Separate security audit authority from scoped academic audit access | Designated account/security administrators inspect institution-wide login/recovery/grant events without automatic evidence-file access. Coordinators see detailed academic history in scope; Viewers receive approved monitoring information, not unrestricted raw security details. | Yes: capability checks, account/grant/logout/CLI coverage, area-less events, shared-download context, request correlation and retrieval. |
| B. Give scoped Coordinators and Viewers full academic audit detail; security staff use a separate complete log path | Keeps broad scoped academic visibility, but creates a documented complete security audit channel outside ordinary area filters, with authorized retrieval/retention. | Yes for event completeness and academic details; external log tooling/configuration depends on IT. |

**Recommended option:** A. **Required approver:** Security/Records Owner; School IT; Academic Owner for academic history. **Production-acceptance impact:** Must prove access-administration/security-event accountability before acceptance. Confirm fields, retention, who can search/export older records and how a shared download appears without leaking another area's evidence. Rich UI filters may follow later only if complete authorized retrieval already works.

### D10 — Accepted formats, limits and upload resources

**Status:** Pending Decision. **Finding:** F19. **Decision to make:** Which formats and byte limit are required at launch?

| Option | Effect on the existing system | Code changes required? |
|---|---|---|
| A. PDF, DOCX, XLSX, PNG/JPEG up to 25 MiB | Adopts current validated formats/size, corrects MB/MiB wording and makes limits configurable. PPTX stays unavailable. | Yes: configuration/UI consistency; authorize scope before expensive parsing. |
| B. Same formats up to 20 MiB | Uses the proposed smaller size without adding a format; existing larger historical versions remain preserved under approved read policy. | Yes: configurable application/proxy/UI limits and tests. |
| C. Plan's formats including PPTX, up to 20 MiB | Adds a school-required presentation format rather than accepting it without detection/validation. | Yes: PPTX validator, allowlists, limits/UI and tests. |

**Recommended option:** A for the initial accepted scope, unless PPTX is required by the Academic Owner. It retains existing validators; it is not an approval of the current limit. **Required approver:** Academic Owner; School IT; Security/Records Owner. **Production-acceptance impact:** Must agree formats/units and measured request/storage bounds before real uploads. IT must supply request-size, account/cycle storage and upload-rate limits from capacity evidence; no new numeric quota is invented here. All options require scope checks before costly parsing and preservation of referenced history.

### D11 — Malware scanning and quarantine

**Status:** Pending Decision. **Finding:** F21. **Decision to make:** What protects users from malicious content in otherwise valid files?

| Option | Effect on the existing system | Code changes required? |
|---|---|---|
| A. Quarantine until school-approved scanning succeeds | Uploaded files remain unavailable for ordinary submission/download until a recorded scan result permits release; failure/unavailability stays quarantined. | Yes: protected quarantine/release state, scanner integration and failure tests; IT provisions the approved scanner. |
| B. Constrained pilot using an IT-operated pre-scan intake process | Only permitted operators ingest pre-scanned, approved files with recorded provenance; suitable access/network restrictions and disclosure are required. | Possibly: enforce intake restrictions/provenance; at minimum IT procedure/configuration and acceptance evidence. |
| C. Synthetic-data demonstrations only until scanning is available | No real evidence accepted; existing demo workflow continues. | No scanning code needed for demonstrations; this is not a production solution. |

**Recommended option:** A for real institutional use; B only as an expressly approved, bounded pilot exception. **Required approver:** Security/Records Owner; School IT. **Production-acceptance impact:** Real-evidence acceptance remains blocked without an approved implemented control or constrained pilot procedure. Extension/content checks are not malware scanning; no scanner/vendor, paid service or malware-free guarantee is assumed.

### D12 — Sensitivity, retention, holds and disposal

**Status:** Pending Decision. **Findings:** F21, F13, F20. **Decision to make:** Which evidence/audit/configuration records may enter the Hub, and what retention/hold rules apply to live data and backups?

| Option | Effect on the existing system | Code changes required? |
|---|---|---|
| A. Approve a class-based records schedule and permitted evidence scope | Records Owner supplies sensitivity/access classes, retention periods, holds and disposal authority; referenced history stays protected and automatic application purge remains disabled until separately designed. Backup/log retention follows the approved schedule. | Policy approval alone requires no application change; enforcing classes or eventual purge would require scoped code work; IT backup/log configuration required. |
| B. Permit only specifically approved lower-sensitivity evidence in a bounded pilot | No general sensitive-file intake; owner defines permitted documents, pilot duration/review point and preservation/backup handling. | Possibly: intake restrictions/class labels; procedures and access configuration required. |
| C. Keep synthetic data until records policy is approved | Maintains demonstration use only. | No application change for synthetic use; no production acceptance. |

**Recommended option:** A, without assigning retention periods or authorizing deletion here. **Required approver:** Security/Records Owner; School IT for backups/logs; Academic Owner for evidence needs. **Production-acceptance impact:** Missing permitted-data/retention decisions block real evidence. Preserve history and account deactivation; archive is not disposal, and backup bundles contain secrets. No legal/privacy approval is inferred.

### D13 — Overdue monitoring and display timezone

**Status:** Pending Decision. **Finding:** F23. **Decision to make:** Is overdue monitoring required, and what date applies after cycle closure?

| Option | Effect on the existing system | Code changes required? |
|---|---|---|
| A. Show overdue as a separate flag, frozen at closure for closed-cycle reports | Active applicable non-archived incomplete work is overdue after its due date; date-only deadlines use Asia/Manila. Closed cycles calculate at closure, not today's date. Timestamps are explicitly displayed/labelled Asia/Manila. | Yes: shared calculation, dashboard/list/report filters/context and tests. |
| B. Show live overdue age even for closed cycles | Same active-cycle rule, but closed records continue aging; historic closure reports need a clearly separate as-of view. | Yes: flag/report semantics and explicit timezone. |
| C. Approve deadline display only for launch | Keeps stored dates; deadline monitoring is manual and overdue views are explicitly removed from launch scope. | No overdue feature code; timestamp labelling/consistency and scope/training correction still required. |

**Recommended option:** A, consistent with the plan and historical closed-cycle reporting. **Required approver:** Academic Owner; Project Owner. **Production-acceptance impact:** A/B need implementation before their acceptance checkpoint; C requires an explicit scope amendment. None includes deferred email reminders. Specify treatment of undated, draft, excluded, completed and reopened requirements in acceptance tests.

### D14 — Archive versus closure and requirement exclusion

**Status:** Pending Decision. **Finding:** F27. **Decision to make:** Is archive an independent records/lifecycle state at launch?

| Option | Effect on the existing system | Code changes required? |
|---|---|---|
| A. Implement distinct non-destructive cycle/requirement archive actions | Archive is separate from Closed, Draft and Not Applicable, with authorized actions/reasons/history and explicit list/denominator treatment. Archived history remains accessible under scope/retention rules. | Yes: models, transitions, filters/UI and tests. |
| B. Explicitly accept closure-only cycles and draft/applicability-only requirements for launch | No separate archive action; remove “Archived” labelling for Closed and document that archive remains unfinished/deferred by amendment. | UI/documentation changes; no archive schema required for the amended scope. |

**Recommended option:** A for the original version-1 requirements. **Required approver:** Project Owner; Academic Owner; Security/Records Owner for preservation/retention. **Production-acceptance impact:** Either deliver A or record B as a scope change; closure alone must not be counted as the planned archive deliverable. D12 still governs retention and forbids implied deletion authority.

### D15 — Launch administration and institutional role mapping

**Status:** Pending Decision. **Findings:** F27, F13, F09. **Decision to make:** What tools and privileges must ordinary administrators/Coordinators have for accounts, grants, cycles and areas?

| Option | Effect on the existing system | Code changes required? |
|---|---|---|
| A. Retain constrained Django admin plus audited operator cycle/area provisioning | Approve existing administration approach as a launch substitution. Real account admins receive least-privilege staff/model permissions, not routine superuser access; academic roles remain explicit. Server JSON provisioning has named operators and recorded reasons/results. | Yes where needed for privilege/grant safeguards and F13 audit; full app configuration UI is not required by this amended scope. |
| B. Deliver planned application administration screens/APIs | Account/grant and cycle/area management moves into protected product screens with explicit institution-wide versus cycle-wide capabilities. | Yes: significant API/UI and audit/permission tests. |
| C. Operator-only administration for a bounded pilot | Staff request account/scope/structure changes through approved IT operators; no ordinary staff administration. Break-glass access and accountability are defined. | No new administration UI; restrictions/audit/procedures still required. |

**Recommended option:** A for a controlled launch if academic owners accept operator provisioning; B if self-service cycle/area management remains required. **Required approver:** Project Owner; School IT; Academic Owner. **Production-acceptance impact:** Must resolve the missing planned management UI and define who may grant staff/superuser/product roles. Administrator must not silently gain evidence or independent-review powers. Demo-superuser setup is not the approved real privilege model.

### D16 — Reconciled requirements and progress baseline

**Status:** Pending Decision. **Finding:** F27, with F01–F07 and D10/D13–D15. **Decision to make:** What exactly will be accepted as version 1?

| Option | Effect on the existing system | Code changes required? |
|---|---|---|
| A. Retain the original proposed deliverables in full | Assignments, packages, snapshots, archive/overdue and management UI remain required. Correct completion claims and finish all missing required checkpoints. | Yes for required missing behavior; not for cosmetic folder/naming differences alone. |
| B. Approve a reconciled baseline with explicit per-decision amendments | Lists chosen D01–D15 options, outstanding controls and launch deliverables; records accepted substitutions such as administration tools, role names, route versioning/ID conventions and status vocabulary. Missing items are labelled required or expressly deferred. | Depends on selected options; documentation alone cannot close defects. |
| C. Declare a demonstration-only release | Keeps synthetic workflow and honest limitations; no school IT production acceptance requested yet. | No launch features required now; production blockers remain. |

**Recommended option:** B, with each substantive workflow choice separately approved rather than blanket acceptance of current behavior. **Required approver:** Project Owner; Academic Owner; School IT; Security/Records Owner for security/records scope. **Production-acceptance impact:** An agreed baseline is mandatory. Use only approved instrument/areas/criteria for real content; maintain unweighted internal readiness, not an official PACUCOA score. Supply a consistent implemented ERD, role/state matrix, workflow and evaluation evidence. Existing progress statements are not changed by this register; this checkpoint adds only its link.

## School IT release and operating decisions

### D17 — Account recovery at launch

**Status:** Pending Decision. **Findings:** F08, F25. **Decision to make:** What supported recovery channel will users have?

| Option | Effect on the existing system | Code changes required? |
|---|---|---|
| A. Keep email recovery disabled; provide verified administrator-assisted recovery | Retains disabled endpoint messaging; IT defines identity verification, who may reset, secure delivery and audit of recovery. | No enablement code required; administration/audit deficiencies may require fixes and procedure tests. |
| B. Enable institutionally managed SMTP recovery after remediation | Select actual SMTP backend, reject console/dummy production delivery, protect tokens from logs, rate-limit and prove real delivery/one-time use/expiry. IT supplies approved sender/URL/credentials securely. | Yes: configuration guard, safe logging/throttle/test fixes; IT configuration required. |

**Recommended option:** A until B is demonstrated. **Required approver:** School IT; Security/Records Owner. **Production-acceptance impact:** Email recovery must not be enabled from the current example alone. A can satisfy the recovery gate with an approved tested procedure; B blocks acceptance until SMTP/token confidentiality and real-session/token tests pass. No credentials belong in this register.

### D18 — Network exposure, trusted proxies and administration

**Status:** Pending Decision. **Findings:** F09, F28. **Decision to make:** Which network/proxy boundary will IT support, and where may administration be reached?

| Option | Effect on the existing system | Code changes required? |
|---|---|---|
| A. Controlled school-network pilot behind one IT-managed Nginx proxy | Fits the reference topology; admin is restricted to designated management sources. Forwarded headers and limits are based on the verified single trusted hop. | Yes: throttle robustness/tests; IT proxy/firewall/admin configuration. |
| B. School remote-access boundary plus documented proxy chain | Supports approved remote users; IT specifies every trusted hop and admin management network. Header sanitation/rate limiting is verified end to end. | Yes: authentication fixes and topology-specific configuration/tests. |
| C. Public application login with separately restricted administration | Expands exposure and requires explicit IT/security acceptance, consistent multi-worker abuse controls and monitoring. No public evidence access is introduced. | Yes: authentication fixes, hardened exposure configuration and tests. |

**Recommended option:** A for a controlled initial pilot, subject to actual access needs. **Required approver:** School IT; Security/Records Owner. **Production-acceptance impact:** F09 remains blocking until spoof-resistant forwarding and consistent limits cover application/admin login and enabled recovery. Supply actual hostname/DNS/TLS owner, hosts/CSRF origins and network policy. Approve HSTS subdomain inclusion independently of duration/preload; none is inferred from selecting HTTPS. This is not authority to deploy or provision a network.

### D19 — Backup, recovery and records of operation

**Status:** Pending Decision. **Findings:** F11, F20, F28. **Decision to make:** Who operates the recoverable database/evidence/configuration set and approves its recovery targets?

| Option | Effect on the existing system | Code changes required? |
|---|---|---|
| A. IT-operated repository tooling with approved schedule/off-host protection | Use corrected scripts, separate restricted backup credentials, locked/atomic publication, integrity reconciliation and recorded release/schema identity. Adopt nightly backups only if IT approves the proposed schedule; encrypt/restrict and replicate to a separate failure domain. | Yes for tooling defects/hardening; IT jobs, key recovery, permissions and alert configuration. |
| B. School-managed backup platform proving the same recoverable set | Platform protects PostgreSQL, immutable evidence and necessary protected configuration together and demonstrates matching integrity/history restoration. Repository scripts are not the sole production mechanism. | Platform integration may need no app change; F10/F12 tooling fixes remain useful and recovery evidence is mandatory. |

**Recommended option:** A when IT can operate it reliably; B is equally viable if an existing school platform meets the same acceptance evidence. **Required approver:** School IT; Security/Records Owner. **Production-acceptance impact:** IT must record backup/operator ownership, destinations, retention, encryption/key custody, RPO/RTO, alerts and rehearsal frequency; no values are approved here. Actual isolated restoration of an exact approved file plus review/certification history is mandatory under either option. Reconciliation reports must not automatically delete referenced bytes/history.

### D20 — Pilot capacity, service ownership and operational gates

**Status:** Pending Decision. **Findings:** F15, F28. **Decision to make:** Which launch scale and minimum service controls must be proven?

| Option | Effect on the existing system | Code changes required? |
|---|---|---|
| A. Measured, bounded pilot | IT supplies expected users/concurrency, evidence volumes and capacity thresholds; measured API/query/upload behavior defines a supported envelope. Establish backup/service/storage alerts, incident owner, patching, log redaction/retention and rollback. | Depends on measurements; correctness/security and minimum operating gates still require fixes. IT controls required. |
| B. Broader institutional rollout only after scale work | Pagination/on-demand histories/query reduction and representative concurrency/storage tests precede release; use the same minimum operational controls. | Yes: collection/performance work plus capacity and release tests. |

**Recommended option:** A, with measured limits rather than invented sizing promises. **Required approver:** School IT; Project Owner; Security/Records Owner for logs. **Production-acceptance impact:** No accepted capacity or reliable operations can be claimed from a successful frontend build/DB-only health probe. Record target OS/runtimes/PostgreSQL, resources, storage modes/durability, operators and rollback method. Pending migrations and unaccepted warnings must fail release gates; preload advisories need a recorded decision, not automatic enablement.

### D21 — Filtered report population and readiness evidence

**Status:** Pending Decision. **Findings:** F14, F16. **Decision to make:** Does status filtering change the readiness denominator or only the rows displayed?

| Option | Effect on the existing system | Code changes required? |
|---|---|---|
| A. Summarize the filtered population, explicitly labelled | Retains current report calculation; a Complete-only subset can be 100%, labelled subset readiness rather than whole-cycle compliance. CSV/print carry cycle/instrument, filters, scope, numerator/denominator, exclusions, formula version and calculation time/timezone. | Yes: provenance/context and stale-response/print safety; core filtered calculation may remain. |
| B. Keep readiness for the selected cycle/area; status filters only table rows | Headline denominator stays fixed for the authorized cycle/area, while rows narrow by status; display filtered row count separately. | Yes: separate summary/row populations, provenance and stale-state fixes. |

**Recommended option:** B for readiness reports because a Complete-only filter should not obscure missing work in the headline. **Required approver:** Academic Owner; Project Owner. **Production-acceptance impact:** Decide before reports become readiness evidence. All options must prevent old responses being printed under new cycle/filter headings, preserve formula-safe CSV and compare dashboard/report counts using the same defined population. Mislabelled or stale reports are not an acceptable option.

### D22 — Acceptance environment, evidence and sign-off

**Status:** Pending Decision. **Findings:** F11, F25, F28. **Decision to make:** Which isolated environment and responsible reviewers will prove the selected release?

| Option | Effect on the existing system | Code changes required? |
|---|---|---|
| A. IT-controlled target-like staging plus isolated restore environment | Record current isolated PostgreSQL/browser regressions, HTTPS/session/scoped access, closed writes, exact-version history and actual restore outcomes against the chosen baseline. IT records checklist/operator/date/commit/archive and measured recovery results. | Tests/fixes required for uncovered blocker cases; no new product feature solely to choose the environment. IT prepares isolated resources. |
| B. Reproducible isolated development acceptance first, followed by IT target verification | Local synthetic workflows/restore prove readiness for handoff; production acceptance waits for actual target HTTPS/storage/permissions/recovery checks. | Test/fixture changes may be required; target checks remain mandatory. |

**Recommended option:** A. **Required approver:** School IT; Academic Owner for workflow outcomes; Project Owner for release scope. **Production-acceptance impact:** Historical tests and checksum/archive listing cannot replace current workflow and actual restore evidence. D16 defines required behavior; D18–D20 define the target and operational criteria. No checklist box, participant result, privacy/legal approval or production sign-off is completed by this register.

## Approved Technical Fixes That Can Start Now

This section classifies work already supported by the plan/review that needs no new policy choice. “Approved Technical Fixes” does **not** record institutional approval or permission to change deployment files during this documentation-only task. Both fixes are not started; they can be the subject of the next explicitly scoped technical checkpoint. All policy decisions above remain **Pending Decision**.

| Finding / fix | Bounded technical change | Verification required | Approval/acceptance boundary |
|---|---|---|---|
| F10 — Portable backup checksum verification | Produce payload-relative checksum entries; validate expected layout and reject absolute/traversing entries; check the extracted payload, never original source paths. Handle legacy unsafe bundles explicitly rather than silently treating them as verified. | Verify at a different directory/host with original paths absent; tampered/missing payload and unsafe checksum paths must fail. No live database restore is needed for the portable checksum regression itself. | No policy choice about what hashes mean. Does not approve backup retention/encryption/targets or count as an actual recovery rehearsal. |
| F12 — Linux script execution | Track executable modes for the three shell scripts, or document consistent `bash` invocation; retain LF and match the installation/run instructions. | Fresh Linux checkout runs the documented invocation under intended operator permissions; use safe syntax/fixture checks, not unapproved production backup/release actions. | No institutional role/scope decision needed. File modes/invocation are technical packaging; IT still owns installation and target acceptance. |

## Recording decisions and implementation order

First settle D01–D08 and D09–D15, then ratify the D16 baseline. School IT can prepare D17–D22 choices in parallel with those discussions. F10/F12 technical planning need not wait for policy selection; target operation/rehearsal must wait for the approved environment and operating controls. This sequencing is coordination guidance, not a request to start code or infrastructure work now.

For each decision, append an actual record using the following fields; leave it Pending Decision until the required approval evidence exists:

```text
Decision ID:
Status: Pending Decision
Selected option: Not recorded
Any amendments/conditions: Not recorded
Required approvers: As listed in the decision
Approver names and roles: Not recorded
Approval date and evidence/ticket: Not recorded
Reason and accepted requirements changes: Not recorded
Implementation owner/checkpoint: Not assigned
Acceptance tests/evidence required: Not completed
Verification result and release commit: Not recorded
```

After approval, record implementation and verification separately. Update the plan/progress/acceptance materials in a subsequent authorized task to reflect the actual chosen baseline; never infer approval from a recommendation, existing code, or this document's commit.
