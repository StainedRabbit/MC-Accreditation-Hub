# Production Acceptance Workshop Brief

Prepared: 2026-10-02  
Status: Internal preparation draft. No workshop date, named approvers, approval evidence, or School IT target values are recorded.

## Purpose and authority

Use this brief to prepare one joint decision workshop for the Academic Owner, Project Owner, School IT, and Security/Records Owner. The [Production Acceptance Decision Register](PRODUCTION_ACCEPTANCE_DECISION_REGISTER.md) remains the source of truth for decision wording, options, recommendations, and required approvers. This brief does not record an approval, authorize real institutional evidence, or establish production acceptance.

The Project Owner coordinates scope and delivery. The Academic Owner approves academic workflow and instrument requirements. School IT approves operating environments and release evidence. The Security/Records Owner approves evidence visibility, sensitivity, retention, and security controls. Where the register names multiple approvers, each approves their part. The register does not name individuals; assign names at the workshop and do not infer sign-off from a provisional choice or implementation already in the repository.

## Workspace handoff checkpoint

At preparation review, `main` matched `origin/main` at `7c9703f` and the working tree was clean. That commit contains the audit search continuation, dashboard/audit polish, workflow verification, and this workshop brief. The progress record describes the current local slice as dashboard/compliance/audit presentation and interaction polish, including audit search/date filters and cursor continuation. This is a committed local checkpoint; it does not demonstrate School IT target acceptance.

The earlier seven-file uncommitted checkpoint note is superseded. The tracked files in that checkpoint were committed, with the workshop brief also included in `7c9703f`; the current working tree no longer contains that pending patch. Existing local verification notes remain repository records, not target-environment acceptance evidence. Unresolved capacity/operations work (D20), target restore and operating controls (D18–D19), and policy/owner decisions below remain open.

## Workshop logistics and ownership

Complete the role-to-person assignments and meeting details before circulating an invitation. The Project Owner owns scheduling, confirming decision authority, and maintaining the outcome record. No names, date, meeting mode, or target values are inferred here.

| Role / function | Named attendee | Workshop responsibility | Pre-read complete |
|---|---|---|---|
| Project Owner / facilitator | Not assigned | Confirm scope, facilitate decisions, own baseline and action tracking | Not recorded |
| Decision recorder | Not assigned | Capture exact outcomes, conditions, approvers, evidence, and actions | Not recorded |
| Academic Owner | Not assigned | Approve academic workflow, instrument, and reporting requirements | Not recorded |
| Security/Records Owner | Not assigned | Approve visibility, file security, sensitivity, records, and audit requirements | Not recorded |
| School IT | Not assigned | Approve environment, operations, recovery, and target acceptance controls | Not recorded |

| Workshop date/time and timezone | Not scheduled |
| Meeting mode / location | Not recorded |
| Decision evidence repository or ticket | Not assigned |
| Follow-up checkpoint | Not scheduled |

Use [the pilot readiness outcome template](PILOT_READINESS_OUTCOME_TEMPLATE.md) to record workshop outcomes and the resulting versioned baseline/backlog. Keep this brief and the decision register as preparation/source material; do not record approval by filling a template before the required approvers have approved it.

## Pre-read

- Project Owner: review the complete register and identify which provisional choices to recommend, with reasons and any conditions; recommendations remain proposals.
- Academic Owner: review D01–D08, D13–D16, and D21, including role/scope, certification, status, deadline, archive, administration, baseline, and readiness-report semantics.
- Security/Records Owner: review D02–D03, D05–D06, D09–D12, and the security/records portions of D16–D20; bring the institution's sensitivity, scanning, retention, legal-hold, audit, and log requirements.
- School IT: prepare actual (not example) values or identify who will provide them for D17–D20 and D22: proxy/network boundaries, management sources, TLS/log path, shared throttling, recovery operations, backup/recovery, capacity, target environment, and evidence owners.
- All approvers: review D16 baseline dependencies and mark questions requiring a separate policy owner or missing evidence. No real institutional file is needed or permitted for this workshop.

## Proposed agenda

1. **Opening and authority (10 min):** confirm roles, scope, decision-recording method, and that recommendations are not approvals.
2. **Academic/access decisions (45–60 min):** decide or ratify D01–D08 and D09–D15 in register order. Give each decision its required approver(s); record dissent, conditions, or deferral without converting silence into consent.
3. **Acceptance baseline (20–30 min):** use outcomes from the prior decisions to resolve and ratify D16. Record any requirement changes and their owner.
4. **School IT and operations (45–60 min):** resolve D17–D20; confirm actual values, operating owners, and evidence needed for target checks. Treat D17–D18 provisional selections as unapproved until their listed approvers confirm them.
5. **Reports and acceptance evidence (20 min):** ratify D21 and resolve D22's environment, reviewers, and evidence record. D22 target acceptance depends on the approved D16 baseline and D18–D20 target/operating criteria.
6. **Read-back and actions (10 min):** read back each decision status, conditions, approvers, evidence gaps, accountable owner, and next checkpoint. Keep pending any decision without its required approval evidence.

The timeboxes are planning estimates, not a scheduled meeting length. Split a topic for follow-up if owners lack evidence; do not force a decision to meet the agenda.

## Decision matrix

The status and provisional selection below reflect the register and progress notes. “Evidence to bring/require” identifies decision inputs and later acceptance proof; it does not claim the evidence exists. For full alternatives and constraints, use the register section linked by decision ID.

| ID | Current status; provisional choice | Required approver roles | Workshop question and evidence to bring/require |
|---|---|---|---|
| D01 | Provisional; A | Academic Owner; Project Owner | Who may close/reopen a whole cycle? Bring the approved authority/scope matrix; later verify permissions and negative scope tests. |
| D02 | Provisional; A | Security/Records Owner; Academic Owner | Which role/state/ownership boundaries govern drafts, submissions, approved files, histories, search, and downloads? Bring an approved visibility matrix; later verify consistent enforcement. |
| D03 | Provisional; A | Security/Records Owner; Academic Owner | Which area/cycle sharing boundaries apply, including legacy mappings and searchable versions? Bring the sharing rule and legacy-access decision; later verify search and download scope. |
| D04 | Provisional; A | Academic Owner; Project Owner | Are submitters individually assigned or an area team, and who may replace another person's evidence? Bring role/assignment expectations; later verify assignment, delegation, and stewardship cases. |
| D05 | Provisional; A | Academic Owner; Security/Records Owner for historical-record handling | What exact approved evidence and criteria must completion preserve, including legacy certifications? Bring recordkeeping requirements; later verify immutable version/support references and legacy treatment. |
| D06 | Provisional; A | Academic Owner; Security/Records Owner | Which changes require reopening or new applicability decisions? Bring criteria/applicability governance; later verify rationale-backed, append-only history and transition rules. |
| D07 | Provisional; A | Academic Owner; Project Owner | Is the submission a requirement package or an individual mapped version, and which transitions/states are required? Bring the intended lifecycle and status vocabulary; later verify complete submit/review/withdraw/resubmit paths. |
| D08 | Pending; none recorded in index | Academic Owner; Security/Records Owner | What does expiry/validity change (warning, eligibility, completion, or other behavior)? Bring instrument-specific validity rules and examples; later verify boundary dates, time zones, and effects on existing certifications. |
| D09 | Provisional; A | Project Owner; Security/Records Owner | Who may inspect academic/security audit history, and what fields are appropriate? Bring role/access and audit-field requirements; later verify scoped access, immutable events, and sensitive-field exclusions. |
| D10 | Pending; none recorded in index | Project Owner; School IT; Security/Records Owner | Which formats, size units, and resource limits are accepted? Bring expected file types/sizes and target resource constraints; later verify matching validation, upload limits, and error behavior. |
| D11 | Pending; none recorded in index | School IT; Security/Records Owner | How are incoming real files scanned, quarantined, released, or rejected? Bring the selected scanning service/operator, failure path, and audit requirements; later prove clean, malicious, unavailable-scanner, and quarantine handling in the approved environment. |
| D12 | Pending; none recorded in index | Security/Records Owner; Academic Owner | Which records may be accepted and how are sensitivity, retention, legal holds, and disposal governed? Bring approved records schedule and handling rules; later verify access, hold, retention, and disposal controls before real evidence use. |
| D13 | Pending; none recorded in index | Academic Owner; Project Owner | How are deadlines, overdue states, and timestamps calculated and displayed? Bring authoritative deadline/time-zone rules and representative cases; later verify date boundaries, inclusive filters, and displayed zone. |
| D14 | Pending; none recorded in index | Academic Owner; Project Owner | Is archival distinct from closure, draft, and non-applicability? Bring lifecycle definitions and required retrieval behavior; later verify statuses, permissions, counts, and history. |
| D15 | Pending; none recorded in index | Project Owner; Academic Owner; School IT | Which account, cycle, and area administration functions are launch requirements? Bring operator tasks, role boundaries, and explicit deferrals; later verify least privilege and auditability of required administration. |
| D16 | Pending; none recorded in index | Project Owner; Academic Owner; School IT; Security/Records Owner for security/records scope | Which revised requirements and explicit deferrals form the acceptance baseline? Bring outcomes from D01–D15 and agreed instrument/scope; record versioned baseline, requirement changes, and corresponding acceptance evidence. |
| D17 | Provisional; A for pilot | School IT; Security/Records Owner | Is pilot recovery administrator-assisted or institutionally emailed? Bring identity-verification/reset procedure or actual SMTP/logging controls; later prove target behavior, safe logs, rate limits, and one-time expiry if email recovery is enabled. |
| D18 | Provisional; A restricted internal test only | School IT; Security/Records Owner | Which network/proxy/admin exposure model will be operated? Bring exact approved proxy hops/addresses, hostnames/TLS/log behavior, admin CIDRs, exposure boundary, and shared throttle plan; later verify those controls end to end. |
| D19 | Pending; none recorded in index | School IT; Security/Records Owner | Who owns backup/recovery and operational records, and what targets apply? Bring operator/platform, separate destinations, encryption/key custody, retention/holds, RPO/RTO, alerts, and rehearsal owner/frequency; later restore an approved file plus review/certification history in isolation. |
| D20 | Pending; none recorded in index | School IT; Project Owner; Security/Records Owner for logs | What pilot scale and operating controls must be proven? Bring expected users/concurrency/evidence volume, target stack/resources/storage, capacity thresholds, incident/patch/rollback/log owners; later run representative capacity and operational checks. |
| D21 | Provisional; B | Academic Owner; Project Owner | Does a status filter change only table rows while readiness remains for the selected authorized cycle/area? Bring report population/formula and provenance expectations; later verify JSON/CSV/print consistency and stale-response safety. |
| D22 | Provisional; B local synthetic stage only | School IT; Academic Owner for workflow outcomes; Project Owner for release scope | Where/how will acceptance evidence be collected and who reviews it? Bring target environment, reviewer roles, checklist/record owner, and commit/archive identity requirements; later collect current target HTTPS/access/restore/workflow evidence. |

### Required gates and sequencing

- Resolve D01–D08 and D09–D15, then ratify D16. If an upstream choice remains open, mark dependent baseline items conditional or deferred.
- Prepare D17–D22 in parallel where independent. D18 values, D19 recovery ownership/evidence, and D20 capacity/operations feed D22; D16 defines the behavior against which target results are judged.
- D11 and D12 must be resolved before real institutional evidence is accepted. D18's restricted test choice is not production approval; D22's local synthetic stage is not School IT target acceptance.
- F10/F12 are policy-independent technical fixes, not a substitute for D19 policy or an actual target restore. Preserve the register's separate verification boundary.
- Record missing evidence as an action with an owner and due checkpoint, not as an approved option. No decision is approved until the listed role(s) and approval evidence are recorded.

## Blank decision outcome log

Copy one record per decision. Leave unknown fields explicitly `Not recorded`; keep approval, implementation, and acceptance distinct.

```text
Decision ID:
Status: Pending Decision
Selected option: Not recorded
Any amendments / conditions: Not recorded
Required approvers: As listed in the decision register
Approver names and roles: Not recorded
Approval date and evidence / ticket: Not recorded
Reason and accepted requirements changes: Not recorded
Implementation owner / checkpoint: Not assigned
Acceptance tests / evidence required: Not completed
Verification result and release commit: Not recorded
Target acceptance result (if applicable): Not recorded
Deferred questions / action owner / due checkpoint: Not recorded
```

## Follow-up and document validation

After the workshop, update the decision register and outcome template only from actual recorded approvals and evidence. Track implementation and verification in separate fields/checkpoints; do not treat a selected option as proof of a fix. Issue a numbered baseline only after D16 approval evidence exists. Revise progress claims only after the approved outcomes and their verification are known. Target operation, real evidence, and school acceptance remain gated by the approved environment, operating controls, and completed evidence.

Before circulation, fill the logistics and attendee fields, confirm pre-read owners, verify the decision matrix against the register, and confirm the relative links resolve. No application test run is required for this document.
