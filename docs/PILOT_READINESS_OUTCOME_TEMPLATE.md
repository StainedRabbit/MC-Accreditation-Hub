# Pilot Readiness Workshop Outcome and Baseline

**Status:** Working template. Not an approval, acceptance baseline, or authorization to accept institutional evidence.

Use this record during and after the joint workshop described in [Production Acceptance Workshop Brief](PRODUCTION_ACCEPTANCE_WORKSHOP_BRIEF.md). The [Production Acceptance Decision Register](PRODUCTION_ACCEPTANCE_DECISION_REGISTER.md) is the source of truth for decision wording, options, and required approvers. Copy this file for the workshop record; keep the untouched template available for later cycles.

## Record identity

| Field | Value |
|---|---|
| Baseline version | Not assigned |
| Status | Draft — not approved |
| Workshop date / timezone | Not recorded |
| Project Owner | Not assigned |
| Decision recorder | Not assigned |
| Source release commit reviewed | Not recorded |
| Decision register revision / commit | Not recorded |
| Approval evidence location | Not assigned |

## Approval and scope

| Approver role | Name | Decision scope confirmed | Approval date / evidence |
|---|---|---|---|
| Project Owner | Not assigned | Release scope and baseline | Not recorded |
| Academic Owner | Not assigned | Academic workflow, instrument, and reports | Not recorded |
| Security/Records Owner | Not assigned | Security and records scope | Not recorded |
| School IT | Not assigned | Environment, operations, and acceptance evidence | Not recorded |

**Approved instrument, cycle, and program scope:** Not recorded.  
**Explicitly out of scope:** Not recorded.  
**Approval status:** Pending until each required approver's evidence is entered above and the decision records below are complete.

## Decision outcomes

Copy one complete record per decision from the register. “Provisional” selections remain unapproved until the listed approvers record approval evidence. A deferred or unresolved decision stays open with an owner and checkpoint.

| ID | Status | Selected option / amendment / deferral | Required approvers | Names, date, and evidence reference | Conditions / accepted requirement changes | Follow-up owner and checkpoint |
|---|---|---|---|---|---|---|
| D01 | Not recorded | Not recorded | As listed in register | Not recorded | Not recorded | Not assigned |
| D02 | Not recorded | Not recorded | As listed in register | Not recorded | Not recorded | Not assigned |
| D03 | Not recorded | Not recorded | As listed in register | Not recorded | Not recorded | Not assigned |
| D04 | Not recorded | Not recorded | As listed in register | Not recorded | Not recorded | Not assigned |
| D05 | Not recorded | Not recorded | As listed in register | Not recorded | Not recorded | Not assigned |
| D06 | Not recorded | Not recorded | As listed in register | Not recorded | Not recorded | Not assigned |
| D07 | Not recorded | Not recorded | As listed in register | Not recorded | Not recorded | Not assigned |
| D08 | Not recorded | Not recorded | As listed in register | Not recorded | Not recorded | Not assigned |
| D09 | Not recorded | Not recorded | As listed in register | Not recorded | Not recorded | Not assigned |
| D10 | Not recorded | Not recorded | As listed in register | Not recorded | Not recorded | Not assigned |
| D11 | Not recorded | Not recorded | As listed in register | Not recorded | Not recorded | Not assigned |
| D12 | Not recorded | Not recorded | As listed in register | Not recorded | Not recorded | Not assigned |
| D13 | Not recorded | Not recorded | As listed in register | Not recorded | Not recorded | Not assigned |
| D14 | Not recorded | Not recorded | As listed in register | Not recorded | Not recorded | Not assigned |
| D15 | Not recorded | Not recorded | As listed in register | Not recorded | Not recorded | Not assigned |
| D16 | Not recorded | Not recorded | As listed in register | Not recorded | Not recorded | Not assigned |
| D17 | Not recorded | Not recorded | As listed in register | Not recorded | Not recorded | Not assigned |
| D18 | Not recorded | Not recorded | As listed in register | Not recorded | Not recorded | Not assigned |
| D19 | Not recorded | Not recorded | As listed in register | Not recorded | Not recorded | Not assigned |
| D20 | Not recorded | Not recorded | As listed in register | Not recorded | Not recorded | Not assigned |
| D21 | Not recorded | Not recorded | As listed in register | Not recorded | Not recorded | Not assigned |
| D22 | Not recorded | Not recorded | As listed in register | Not recorded | Not recorded | Not assigned |

## Version 1 requirement baseline

Only populate this section after D01–D15 outcomes are approved and D16 is ratified. Include the accepted instrument/scope and make every changed or deferred requirement traceable to its decision ID. Do not infer approval from implemented behavior.

| Baseline item | Requirement / behavior | Source decision(s) | Disposition: required / deferred | Rationale and conditions | Approver evidence | Acceptance evidence |
|---|---|---|---|---|---|---|
| Not recorded | Not recorded | Not recorded | Not recorded | Not recorded | Not recorded | Not recorded |

**Baseline approval date:** Not recorded.  
**Baseline approvers and evidence:** Not recorded.  
**Prior version superseded:** Not recorded.

## Implementation backlog

Create one row per approved change needed to meet the version 1 baseline. A code change is not complete until its verification evidence and release commit are recorded. Record explicit deferrals with an owner, reason, and reconsideration checkpoint.

| Item | Source decision / baseline item | Change or operational action | Required / deferred | Dependencies / gate | Owner | Verification method and evidence location | Status / checkpoint | Release commit |
|---|---|---|---|---|---|---|---|---|
| Not recorded | Not recorded | Not recorded | Not recorded | Not recorded | Not assigned | Not recorded | Not started | Not recorded |

## Pilot and acceptance gates

Keep each gate pending until the required decision, control, and evidence are recorded. A local synthetic result does not satisfy a School IT target check.

| Gate | Required evidence | Status | Owner / checkpoint |
|---|---|---|---|
| D11 — scanning and quarantine | Approved scanner/control or expressly approved bounded-pilot intake process; failure handling and verification evidence | Pending | Not assigned |
| D12 — permitted records and handling | Approved data scope, sensitivity, retention, legal-hold, backup/log, and disposal rules | Pending | Not assigned |
| D16 — version 1 baseline | Recorded approval by required roles, with decisions and deferrals traceable | Pending | Not assigned |
| D18 — network and administration | School IT-approved topology and actual values; target verification evidence | Pending | Not assigned |
| D19 — backup and recovery | Named operator/platform, protected destinations, encryption/key recovery, retention, targets, alerts, and isolated restore evidence | Pending | Not assigned |
| D20 — capacity and operations | Measured pilot envelope, service owners, thresholds, incident/patch/rollback/log controls | Pending | Not assigned |
| D22 — acceptance record | Approved target, named reviewers, current release identity, and completed target checklist evidence | Pending | Not assigned |

**Real institutional evidence authorized:** No. Change only after the applicable approved decision and required controls/evidence are recorded.  
**School IT acceptance claimed:** No. Change only after D22 target evidence is complete and approved.

## Workshop actions and unresolved items

| Action / unresolved question | Related decision(s) | Owner | Due checkpoint | Evidence / closure condition | Status |
|---|---|---|---|---|---|
| Not recorded | Not recorded | Not assigned | Not scheduled | Not recorded | Open |

## Verification and release record

| Check / scenario | Expected result from approved baseline | Result and evidence location | Release commit | Reviewer / date |
|---|---|---|---|---|
| Authorization and cross-scope denial | Not recorded until baseline approved | Not run | Not recorded | Not assigned |
| Workflow transitions and history | Not recorded until baseline approved | Not run | Not recorded | Not assigned |
| Reports, filters, and exported provenance | Not recorded until baseline approved | Not run | Not recorded | Not assigned |
| File validation/scanning and failure handling | Not recorded until D10–D12 approved | Not run | Not recorded | Not assigned |
| Closed-cycle writes and authorized lifecycle actions | Not recorded until baseline approved | Not run | Not recorded | Not assigned |
| Target HTTPS, proxy, scoped access, and admin boundary | School IT-approved behavior | Not run | Not recorded | Not assigned |
| Isolated restoration and approved-version history | Exact approved file plus associated review/certification history restored and verified | Not run | Not recorded | Not assigned |

Do not mark a gate complete from a build, test, archive listing, or provisional choice alone. Keep local synthetic verification, implementation verification, and target acceptance results separately attributable to their environment and release commit.
