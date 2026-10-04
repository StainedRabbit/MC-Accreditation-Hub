# D16 — Version 1 Reconciled Baseline Proposal

**Status:** Review draft for D16 Option B. **D16 remains Pending Decision.** This is not an approved, numbered acceptance baseline, an authorization for institutional evidence, or a School IT target acceptance record.

**Repository reviewed:** commit 394696364146da968de9098af2c60d6720ae87a4, clean working tree before this documentation update, 2026-10-04. The [decision register](PRODUCTION_ACCEPTANCE_DECISION_REGISTER.md) is authoritative for options, statuses, and required approvers. The [workshop outcome template](PILOT_READINESS_OUTCOME_TEMPLATE.md) remains blank and unapproved. The [proposed plan](MC_Accreditation_Hub.md) describes intended behavior; the 2026-09-17 [system review](SYSTEM_REVIEW_AND_IMPROVEMENT_PLAN.md) is historical and predates later fixes. Current behavior below was checked against [models](../backend/hub/models.py), [access policy](../backend/hub/access.py), [readiness calculation](../backend/hub/compliance.py), [API views](../backend/hub/views.py), [API contract](API.md), and the [progress record](PROGRESS.md). Historical local test results were read from that record; no application tests were run for this proposal.

## Decision dependency and candidate version 1 scope

Every disposition in this table is a **proposal conditional on the required approvals**. “Implemented” describes repository code, not an accepted institutional policy. If an upstream choice changes, update the code/backlog and this draft before D16 ratification. Required owner evidence belongs in the approved evidence repository; put only its reference in the [tracker](PILOT_READINESS_WORKSHOP_TRACKER.md).

| Decision and register status | Repository behavior at this commit | Conditional version 1 disposition | Required authority and missing input/evidence |
|---|---|---|---|
| D01 — Provisional A | A cycle-wide Coordinator grant, rather than an area-only grant, controls close/reopen and cycle archive/restore. | Propose required: explicit whole-cycle authority and reasoned transitions. | Academic Owner; Project Owner. Confirm delegation and target negative-scope checks. |
| D02 — Provisional A | Scoped version, metadata, history, search, and download visibility distinguishes Coordinators, Reviewers, Custodians, and Viewers. | Propose required: the current default-deny role/state boundary. | Security/Records Owner; Academic Owner. Approve visibility for drafts, withdrawn/revision history, and mixed document versions; verify on target. |
| D03 — Provisional A | New cross-area/cross-cycle mapping and submission are denied; preserved legacy links retain only their applicable historical visibility. | Propose required: same-area/cycle new work, with an explicit legacy-history rule. | Security/Records Owner; Academic Owner. Decide permitted legacy retrieval and confirm metadata/search/download parity. |
| D04 — Provisional A | Active requirement assignees and document stewards control contributor work; scoped Coordinator overrides require a reason. | Propose required: named assignment, stewardship, and audited exceptions. | Academic Owner; Project Owner. Confirm Contributor-to-Custodian mapping and target assignment/delegation cases. |
| D05 — Provisional A | Completion is a Coordinator certification with rationale, criteria snapshot, and exact approved package or legacy submission support; older unsupported completions do not silently count. | Propose required: deliberate, pinned completion and preserved legacy distinction. | Academic Owner; Security/Records Owner for history. Approve support and historical-record treatment; verify exact-version context. |
| D06 — Provisional A | Substantive criteria/support changes require reopen; criteria revisions and reasoned applicability decisions preserve history. | Propose required: explicit reopen and applicability governance. | Academic Owner; Security/Records Owner for record treatment. Confirm material-change boundary and target history. |
| D07 — Provisional A | New requirements use package attempts with drafts, pinned items, submission, withdrawal, review, and new-attempt resubmission; preserved legacy requirements use item submissions. | Propose required: package lifecycle, independent review, and explicit legacy path. | Academic Owner. Approve outcomes/status vocabulary and target workflow evidence. |
| D08 — Pending | Validity dates currently gate submission, approval/readiness and package readiness; recorded supported completion remains until reopen. Closed-cycle checks use its closure date. | Propose the register's Option A for owner review: validity as metadata without automatic expiry gates. **Code and tests would be required** if A is approved. Option B would instead retain the basic gate with approved wording. No choice is accepted here. | Academic Owner; Security/Records Owner. Supply validity policy and boundary/closed-cycle examples; resolve the current code mismatch before D16 approval. |
| D09 — Provisional A | Academic audit is Coordinator-scoped; a separate Django security-audit permission exposes area-less account/grant/authentication history without file access. | Propose required: separate security and academic audit authority. | Security/Records Owner; School IT; Academic Owner for academic history. Approve fields, readers, preservation and target retrieval/log evidence. |
| D10 — Pending | PDF, DOCX, XLSX, PNG, and JPEG content validation uses a fixed 25 × 1024 × 1024 byte ceiling; the current error calls this “25 MB.” PPTX is unsupported. Scope is checked before costly parsing, then rechecked in the write transaction. | Propose Option A as a candidate: these formats and a 25 MiB ceiling. **Configurability, unit wording, and target resource limits remain work** if A is approved. PPTX is a proposed deferral only if owners accept A. | Academic Owner; School IT; Security/Records Owner. Approve types, units, proxy/body and storage/rate limits from target measurements. |
| D11 — Pending | Append-only scan verdicts quarantine versions; missing, failed, infected, or checksum-mismatched scans block use and file access. | Propose required Option A for real evidence; synthetic-only until scanner approval and target verification. | Security/Records Owner; School IT. Supply approved local scanner, operator, failure/retry procedure and target tests. |
| D12 — Pending | Evidence/history is preserved; archive is not disposal. No class-based retention or automatic purge schedule is configured. | Propose required Option A: owner-approved permitted classes, access, retention, holds, and disposal across live data, audit, logs, and backups. No period is guessed. | Security/Records Owner; School IT for backups/logs; Academic Owner for evidence needs. Complete the [records schedule input](RECORDS_SCHEDULE_INPUT.md). |
| D13 — Pending | Overdue is a separate flag, using the Asia/Manila next-day boundary and closure-date freeze; it does not change readiness. | Propose required Option A subject to rule approval. | Academic Owner; Project Owner. Confirm undated, draft, excluded, completed, reopened and closed cases; review target displays/exports. |
| D14 — Pending | Separate, reasoned archive/restore exists for closed cycles and active-cycle requirements; current counts exclude archives while scoped history remains visible. | Propose required Option A subject to lifecycle and records approval; no disposal authority follows. | Project Owner; Academic Owner; Security/Records Owner for preservation/retention. Confirm transition, access, report, and history rules. |
| D15 — Pending | Constrained Django account admin, separate permissioned grant/cycle commands, and a reasoned credential route are implemented. Product roles do not confer Django staff or evidence access. | Propose Option A as a launch substitution; full product administration screens are a proposed deferral only if owners approve that substitution. | Project Owner; School IT; Academic Owner. Approve operator matrix, assignments, shell/actor correlation, management network, audit and break-glass target evidence; D17 recovery procedure remains separate. |

D01–D07 and D09 are **provisional**, not approved. D08 and D10–D15 are **Pending Decision**. D16 cannot become an approved baseline by choosing this draft's candidate rows; the required authorities first record the upstream outcomes and evidence in the decision register and workshop outcome record.

## Implemented entity relationships

These diagrams describe current Django models. A line is a model relationship, not a claim that a user can retrieve its records; [access policy](../backend/hub/access.py) and scan state still govern retrieval. Most models use Django integer primary keys; Document uses a UUID primary key. AuditEvent.record is a string reference, not a foreign key. AuthRateBucket is an independent operational throttle table.

~~~mermaid
erDiagram
    USER ||--o{ ROLE_ASSIGNMENT : receives
    CYCLE ||--o{ ROLE_ASSIGNMENT : scopes
    AREA o|--o{ ROLE_ASSIGNMENT : narrows
    CYCLE ||--o{ AREA : contains
    AREA ||--o{ REQUIREMENT : contains
    REQUIREMENT ||--o{ REQUIREMENT_ASSIGNMENT : assigns
    USER ||--o{ REQUIREMENT_ASSIGNMENT : serves
    REQUIREMENT ||--o{ EVIDENCE_ITEM : defines
    AREA ||--o{ DOCUMENT : owns
    USER ||--o{ DOCUMENT : custodians
    USER o|--o{ DOCUMENT : stewards
    DOCUMENT ||--o{ DOCUMENT_VERSION : versions
    DOCUMENT_VERSION ||--o{ DOCUMENT_SCAN : scan_history
    EVIDENCE_ITEM ||--o{ EVIDENCE_MAPPING : accepts
    DOCUMENT ||--o{ EVIDENCE_MAPPING : mapped
    CYCLE {
        int id PK
        string status
        datetime closed_at
        datetime archived_at
    }
    REQUIREMENT {
        int id PK
        bool active
        bool applicable
        int criteria_revision
        datetime archived_at
    }
    DOCUMENT {
        uuid id PK
        int area_id FK
        int steward_id FK
    }
    DOCUMENT_VERSION {
        int id PK
        uuid document_id FK
        string checksum
        date valid_until
    }
~~~

~~~mermaid
erDiagram
    EVIDENCE_MAPPING ||--o{ SUBMISSION : legacy_submissions
    DOCUMENT_VERSION ||--o{ SUBMISSION : pins
    SUBMISSION ||--o| REVIEW_DECISION : receives
    REQUIREMENT ||--o{ PACKAGE_ATTEMPT : attempts
    PACKAGE_ATTEMPT ||--o{ PACKAGE_ITEM : pins
    EVIDENCE_MAPPING ||--o{ PACKAGE_ITEM : identifies_item
    DOCUMENT_VERSION ||--o{ PACKAGE_ITEM : identifies_version
    PACKAGE_ATTEMPT ||--o| PACKAGE_DECISION : receives
    REQUIREMENT ||--o{ REQUIREMENT_CERTIFICATION : history
    REQUIREMENT_CERTIFICATION ||--o{ CERTIFICATION_EVIDENCE : legacy_support
    SUBMISSION ||--o{ CERTIFICATION_EVIDENCE : selected
    REQUIREMENT_CERTIFICATION ||--o{ CERTIFICATION_PACKAGE : package_support
    PACKAGE_ATTEMPT ||--o{ CERTIFICATION_PACKAGE : selected
    REQUIREMENT ||--o{ APPLICABILITY_DECISION : history
    USER o|--o{ AUDIT_EVENT : actor
    AREA o|--o{ AUDIT_EVENT : scope
    PACKAGE_ATTEMPT {
        int id PK
        int requirement_id FK
        string status
        int criteria_revision
        json criteria_snapshot
    }
    REQUIREMENT_CERTIFICATION {
        int id PK
        string outcome
        json criteria_snapshot
    }
    AUDIT_EVENT {
        int id PK
        string action
        string record
        uuid request_id
    }
~~~

The diagrams show the core workflow joins; repeated User actor links are omitted for legibility. User is also referenced by Cycle.archived_by, Requirement.created_by/archived_by, RequirementAssignment.assigned_by, EvidenceMapping.created_by, DocumentVersion.uploaded_by, Submission.submitted_by, both review-decision reviewer fields, PackageAttempt.owner, RequirementCertification.coordinator, and ApplicabilityDecision.coordinator. PackageAttempt.source_attempt optionally links an earlier attempt to a resubmission. Document.custodian is required while steward is nullable for preserved older records. Submitted package items retain exact version metadata in snapshots; legacy Submission records retain version and criteria revision, with unknown historical revision represented as unknown. CertificationEvidence and CertificationPackage pin separate legacy and package support. DocumentVersion, DocumentScan, Submission, review decisions, certifications, applicability decisions, and audit events are append-only through model/API behavior; this is not database-administrator tamper proofing.

## Current authority and lifecycle reference

The following is an **implemented-behavior reference**, conditional on D01–D15 approvals. Roles are additive only within explicit cycle/area grants. File preview/download additionally requires a clean matching scan verdict. An approved version may be visible to a role without exposing another person's review history.

| Product grant | Draft/unsubmitted evidence | Submitted evidence/history | Approved evidence | Writes and decisions |
|---|---|---|---|---|
| Coordinator | All versions in granted scope | Submission/package history in scope | In scope | Manage scoped requirements/areas, reasoned overrides, independent review, applicability, and certification; only an explicit cycle-wide grant manages whole-cycle transitions. |
| Reviewer | No unrelated drafts | Submitted versions and reviewable package/legacy history in granted area | In scope | Independent package or legacy review in scope; no upload/certification authority from Reviewer alone. |
| Custodian (proposed Contributor mapping) | Own documents, uploads, and package drafts in granted area | Own submitted work/history; not every peer's review history | Approved shared versions in granted area | Assigned requirement work and stewarded version replacement; no approval. |
| Viewer | None | No raw submission/review history | Approved versions in granted scope | Read-only monitoring and reports; no decisions. |
| Product Administrator | None from that label alone | None from that label alone | None from that label alone | No Django staff, security-audit, or academic authority without separate assignment. |

| Separate Django authority | Current purpose | Boundary requiring owner confirmation |
|---|---|---|
| Account admin: hub.add_user, hub.change_user, hub.view_user | Reasoned ordinary account creation/edit/activation; new users have unusable passwords. | No self or privileged-target edits, grant/password/permission changes; School IT assigns named staff. |
| Grant operator: hub.manage_role_grants | Reasoned add/revoke of allowed scoped academic grants through the named-operator command. | No self-grants or new product Administrator grants; target shell actor correlation required. |
| Cycle operator: hub.provision_cycle | Reasoned atomic initial active cycle/area creation from JSON. | Separate from a Coordinator's scoped area management and cycle transitions. |
| Credential operator: hub.reset_user_password | Reasoned ordinary-user password route. | D17 identity verification and secure delivery must be supplied before real assisted recovery. |
| Security audit reader: hub.view_security_audit | Institution security-event feed. | Does not grant academic files; D09/D12 readers and preservation need approval. |
| Superuser | Controlled break-glass administration. | Not a routine launch role; School IT must define custody, assignment, and review. |

| Record or calculation | Implemented state and transition rule |
|---|---|
| Cycle | Draft exists in the model; named CLI provisions Active. A cycle-wide Coordinator may close Active to Closed with a reason, reopen Closed to Active with a reason, archive Closed, or restore an archived cycle to Closed. Archive does not reopen. |
| Requirement | Draft is active=false; exclusion is applicable=false with reason. These are independent from certification and archive. A scoped Coordinator may archive/restore only while the cycle is Active. Archived records are read-only and omitted from current monitoring. |
| Document version and scan | Replacement creates a new immutable version. A new/unscanned version is quarantined; only a clean latest verdict for the stored checksum releases file access and workflow use. Failure/unavailability leaves it blocked. |
| Package attempt | Draft may be edited or deleted by its owner; Draft → Submitted, Submitted → Approved or Revisions requested by independent review, or Submitted → Withdrawn by the submitter before decision. Terminal attempts remain immutable; resubmission creates a new Draft linked to its source. One Submitted attempt per requirement is enforced. |
| Preserved legacy review | Each item-level Submission pins one mapped version; one immutable ReviewDecision can approve, request revision, or reject. New requirements use package attempts instead. |
| Completion and readiness | An independent review alone does not complete a requirement. A Coordinator appends Complete with rationale and approved pinned support, or Reopened with rationale. Current mutually exclusive status precedence is Draft, Excluded, Complete, For verification, Needs revision, Ready for completion review, In progress, Missing. The percentage is unweighted: 100 × complete active applicable non-archived requirements / all active applicable non-archived requirements. It is internal readiness, not an official PACUCOA score. |
| Overdue | Separate flag for active, applicable, non-archived, incomplete, dated requirements. It begins the day after the deadline in Asia/Manila, uses today for Active cycles and the closure date for Closed cycles, and does not change readiness numerator/denominator. |

## Proposed amendments and acceptance evidence

| Candidate amendment or gate | Recommendation for owner review | Acceptance consequence |
|---|---|---|
| Contributor name and scope | Treat current area-scoped Custodian plus explicit RequirementAssignment/stewardship as the proposed Contributor implementation under D04/D16. | Academic Owner and Project Owner must approve role terminology and delegation. |
| Product administration | Accept D15 Option A as a conditional launch substitution for full product account/grant/cycle screens; keep scoped area controls in the application. | Full screens may be deferred only by an explicit D15/D16 amendment. School IT must assign and test separate operators. |
| API path and identifiers | Propose existing /api/ paths, document UUIDs, and integer IDs for most other records as a compatibility amendment; do not claim that ID shape grants security. | Project Owner and School IT must accept this external contract before naming a version 1 baseline; changing it would require a separate API migration plan. |
| Internal code layout | Retain the current Django hub app and TypeScript React layout as an implementation detail if the required behavior and evidence are accepted. | No blanket rewrite of folders is proposed solely to match the original sketch. |
| Format and expiry differences | Candidate D10 A excludes PPTX but requires the 25 MiB limit to be configurable and labelled correctly. Candidate D08 A would remove current automatic expiry gates. | Neither deferral nor behavior change is approved yet; record implementation work and tests after the owners choose. |
| Original plan's deferred features | Continue to propose deferring AI/OCR, external accreditor accounts, public registration, SSO, automatic reminders, bulk ZIP export, mobile apps, and integrations. | Do not label an unapproved D01–D15 requirement deferred by grouping it with these original deferrals. |

The acceptance matrix separates **historically recorded local synthetic results** from missing owner and target evidence. The linked [progress record](PROGRESS.md#verified-behavior) contains dates and limits of past runs; this documentation task does not repeat them. Test source links indicate coverage to review, not a new pass at this commit.

| Candidate baseline evidence group | Local repository evidence already recorded | Missing owner decision or policy | Required target or acceptance evidence |
|---|---|---|---|
| D01–D03 scope and visibility | [Access policy](../backend/hub/access.py), [workflow tests](../backend/hub/tests.py), local F01–F03 history in progress. | Academic/Security approval of whole-cycle authority, role/state visibility, and legacy sharing. | Same- and cross-scope list, search, detail, and download checks with grant revocation on target. |
| D04–D07 assignments, package/legacy review, certification | [Models](../backend/hub/models.py), [API contract](API.md), local F04–F07 and Reviewer-dialog results in progress. | Academic and records approvals for assignee/steward, exact support, criteria, states and history. | Full submit/withdraw/review/resubmit/complete/reopen path with exact pinned versions and denial cases. |
| D08 validity | [Readiness code](../backend/hub/compliance.py), [expiry tests](../backend/hub/tests.py). | Choose A or B and approve dates, closure behavior, and effect on completion. | Boundary and closed-cycle examples after any required code change. |
| D09 and D15 security/administration | [Admin controls](../backend/hub/admin.py), [admin tests](../backend/hub/test_admin_hardening.py), [operator runbook](LAUNCH_ADMINISTRATION.md), local D15 results in progress. | Approve audit readers/fields, operator matrix, break-glass, and D17 recovery procedure. | Management-network denial, forged admin form, grant loss, CLI actor/log correlation, audit preservation, credential procedure. |
| D10–D12 file and records gates | [Upload validator](../backend/hub/files.py), [scan logic](../backend/hub/scanning.py), [schedule input](RECORDS_SCHEDULE_INPUT.md), local quarantine results in progress. | Format/limit, approved scanner and permitted classes/retention/holds/disposal. | Proxy/resource bounds, clean/infected/outage/checksum tests, approved records and backup/log handling. Synthetic-only until resolved. |
| D13–D14 monitoring and archive | [Readiness code](../backend/hub/compliance.py), [API contract](API.md), local D13–D14 results in progress. | Academic/Project overdue rule and Project/Academic/Records archive rule. | Manila boundary, closure freeze, archived/current populations, direct history, restore authorization, CSV/JSON parity. |
| D16 and reports | This proposal, [report API contract](API.md), local report-provenance results in progress. | Resolve D01–D15 first; approve instrument, area/criteria scope, D16 amendments, and D21 reporting semantics. | Numbered approved baseline, current release identity, report/print/CSV comparison against authorized population. |
| D17–D20, D22 operating gates | [Deployment guide](DEPLOYMENT.md), [release checklist](RELEASE_CHECKLIST.md), local synthetic restore/restricted-boundary history in progress. | School IT supplies recovery, network, backup, capacity, operators, reviewers, and acceptance target. | Target HTTPS/proxy/admin, shared throttle, protected storage, measured load, isolated restore of an approved version and its decision/certification history, signed acceptance record. |

## Inputs and ratification rule

The Project Owner supplies the approved program/cycle scope, named approvers and recorder, workshop logistics, decision evidence repository, and release intent. The Academic Owner supplies the approved instrument, areas, criteria, validity and workflow decisions. The Security/Records Owner supplies permitted evidence classes, visibility, audit, retention, holds, and disposal policy. School IT supplies actual named operator assignments, management/proxy values, scanner, recovery procedure, backup/log handling, capacity envelope, and target results. None of these values is inferred from synthetic fixtures or repository defaults.

At the workshop, resolve D01–D08 and D09–D15 with their listed authorities. If a decision lacks approval or evidence, leave it pending with an owner and checkpoint, and keep its candidate D16 item conditional. Ratify D16 only after those dependencies are recorded. Use a copy of the [outcome/baseline template](PILOT_READINESS_OUTCOME_TEMPLATE.md) during the workshop to record actual decision outcomes, leaving its version 1 baseline section unfilled while D16 is pending. After D16 approval, assign a baseline version and record exact approved amendments, deferrals, approver evidence, and required implementation/verification backlog. D11/D12 still gate real evidence; D18–D20 and D22 still gate target acceptance.
