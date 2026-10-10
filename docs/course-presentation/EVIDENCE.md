# MIT 007 presentation source and evidence record

Recorded **2026-10-05, Asia/Manila**, on the user's Windows laptop. Repository base commit: `55a2dc8b879a18c7798058bb24b45ab547886464`. This package and its demo helpers are working-tree additions; the commit identifies the source checkout, not a committed presentation release. The supplied 11-slide source remains at `docs/MC_Accreditation_Hub.pptx`, SHA-256 `6A755CEEB53C40F75377852687BDB51A9BDE38DBB985D7BAC2F53625A7E24A27`, and was not edited.

## Environment and claim boundary

- Windows; Python 3.13.3; Node 24.14.0; PostgreSQL 18.4 local cluster at `127.0.0.1:55432`; Google Chrome through Playwright.
- React/Vite/TypeScript frontend and Django/DRF backend are repository code. The course fixture uses a separate `mc_course_demo` database and `.local/course-demo/media` private storage. Existing `.local/demo-credentials.txt` and the persistent demo database are not changed by course-demo setup/reset.
- The synthetic scanners in `scripts/course_demo_scanner.py` and `scripts/isolated_browser_scanner.py` accept only known generated PDF hashes in guarded disposable paths and databases. Their “passed” result is **simulated for local demonstrations**, not a malware-safety finding or school-approved scanner.
- The fictional sample instrument is not an official PACUCOA instrument. `1 / 8 = 12.5%` is an internal sample readiness figure, not an official accreditation score.
- The source deck's `94 / 120` is `78.3%`, not `87%`. The new deck uses the correct fictional 1/8 example. Separate Reviewer approval and Coordinator certification are shown. New-package Reject remains undecided. Institution-owned hosting is an intent awaiting target evidence.

## Current verification

| Check | Command / method | Result |
|---|---|---|
| Django system | `python -B backend/manage.py check` | Passed, no issues. |
| Model migrations | `python -B backend/manage.py makemigrations --check --dry-run` | Passed, no changes. |
| Frontend build | `npm.cmd run build --prefix frontend` | Passed; TypeScript and Vite production build, 1,580 modules. |
| PostgreSQL-backed backend suite | `python -B backend/manage.py test hub --noinput -v 1` against verified local cluster | **107 tests passed** in 426.134 s; test database destroyed. Includes workflow, access, scan, report, and audit coverage. |
| Isolated browser workflow | `PLAYWRIGHT_CHROMIUM_EXECUTABLE=C:\Program Files\Google\Chrome\Application\chrome.exe`; `python -B scripts/run_isolated_browser.py workflow.spec.ts` | **3 tests passed** in 58.3 s in a fresh temporary database and loopback services; temporary records and files removed. The runner now has a known-PDF synthetic scanner fixture after an initial quarantined-file failure. |
| Course-demo guard | `python -B scripts/verify_course_demo_guards.py` | Passed: known file accepted; unknown file, file outside media, wrong database, wrong media path, missing demo flag, wrong cluster, and escaped demo path refused. |
| Four-role course rehearsal | Reset, prepare, run; `node frontend/course-demo-capture.mjs` | Completed Coordinator → Custodian → Reviewer → Coordinator → Viewer path; Viewer package-detail request returned **404**. Captured 20 viewport PNGs and 20 full-page copies. |
| Editable PPTX / PDF render | `python -B docs/course-presentation/build_course_deck.py`; `node frontend/render-course-pdf.mjs`; `python -B docs/course-presentation/validate_course_package.py` | 53 slides, 53 speaker-note parts, 53 PDF pages, 16:9; XML parts parse; HTML slide overflow check found none. |

The first isolated browser attempt had 1 pass and 2 failures because no scanner fixture was configured and the uploaded test PDF remained quarantined. The test-only scanner was added with an exact disposable database/path/hash guard, then the same three tests passed. This is test-fixture repair, not evidence that institutional scanning exists.

The PDF is rendered from the companion HTML built from the same slide content, because PowerPoint rendering was unavailable in this environment. Every HTML slide was rendered and visually inspected; the PowerPoint package, slide text, notes, dimensions, and relationships were checked structurally. Office may reflow some text on a machine without Aptos, so the presenter should open the PPTX once in their PowerPoint installation before class. The PDF and offline sequence provide fixed-layout fallbacks.

## Screenshot inventory

All files below are under `screenshots/` with matching `screenshots/full/` copies. They were captured from the real local UI on the fictional course fixture. Screenshots embedded in the deck are images; titles, tables, diagrams, captions, and decision rows in the PPTX remain editable.

| Files | State or action |
|---|---|
| `01-login`, `02-dashboard-before`, `03-requirement-before`, `04-assignment` | Initial 0% state and assigned fictional Faculty requirement. |
| `05-evidence-mapped`, `06-repository-and-scan`, `06b-version-history-and-scan` | Two mapped fictional PDFs, Repository, version record, simulated scan verdict. |
| `07-package-draft`, `08-package-submitted` | Exact-version package selection and submitted state. |
| `09-review-queue`, `10-review-context` | Independent Reviewer queue and exact review context. |
| `11-ready-for-certification`, `12-certification-dialog`, `13-requirement-complete` | Coordinator's separate rationale-backed completion. |
| `14-dashboard-after`, `15-compliance-report`, `16-scoped-search`, `17-audit-trail` | 12.5% sample result, report provenance, scoped lookup and audit. |
| `18-viewer-approved-only`, `19-scoped-denial` | Approved-only Viewer Repository and denied package detail. |

## Source map and pending evidence

- Original project identity and proposal: [source presentation](../MC_Accreditation_Hub.pptx) and [project plan](../MC_Accreditation_Hub.md).
- Actual implementation: `backend/hub/models.py`, `backend/hub/views.py`, `backend/hub/access.py`, `backend/hub/compliance.py`, `backend/hub/scanning.py`, `frontend/src/main.tsx`, [API reference](../API.md), and [README](../../README.md).
- Decision status and required roles: [D01–D22 register](../PRODUCTION_ACCEPTANCE_DECISION_REGISTER.md); [D16 proposal](../D16_VERSION_1_BASELINE_PROPOSAL.md). Provisional Project Owner directions are **not** institutional approvals.
- Target deployment and recovery boundary: [deployment guide](../DEPLOYMENT.md), [restore guide](../RESTORE.md), [release checklist](../RELEASE_CHECKLIST.md). No School IT target values, approved scanner, completed target restore, capacity measurement, or acceptance record were supplied.
- Participant evaluation tasks and blank fields: [thesis packet](../THESIS_EVALUATION.md) and [course worksheet](EVALUATION_WORKSHEET.md). No participant findings were supplied.

The source and test record supports local implemented behavior and a repeatable fictional demonstration. Real-evidence intake still requires D11 scanning and D12 records controls; pilot acceptance still requires D18–D20 and D22 target evidence and their required approvals.

