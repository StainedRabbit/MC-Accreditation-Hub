# MIT 007 fictional Windows demonstration

This is a disposable **local course demonstration**, not a school deployment. Every account, requirement, and PDF is fictional. The synthetic scanner only recognizes the two generated demo PDFs and reports a **simulated** clean verdict; it is not institutional malware scanning.

## Laptop preparation and preflight

Use the repository's Windows laptop with Python 3.13+, Node 22+, frontend dependencies, Google Chrome, and its ignored `.local/postgres` PostgreSQL 18 cluster. The script verifies that the server on `127.0.0.1:55432` reports this repository's exact `.local/postgres` data directory before touching a database. It only creates `mc_course_demo` and `.local/course-demo`; it does not change the existing `mc_demo` database.

In PowerShell from the project root:

```powershell
cd 'C:\Projects\My Projects\Graduate School Accreditation Hub'
python -B scripts/course_demo.py prepare
python -B scripts/course_demo.py status
python -B scripts/verify_course_demo_guards.py
```

`prepare` creates the dedicated database, private media directory, generated secret/password, two fictional source PDFs, seeded roles and requirements, and the Faculty Custodian assignment. Repeating it preserves the prepared state. The password stays in ignored `.local/course-demo/state.json`; read it locally just before presenting:

```powershell
(Get-Content .local/course-demo/state.json -Raw | ConvertFrom-Json).password
```

Do not put that password in slides, screenshots, source control, or a class handout. Confirm the course deck PDF and the offline screenshot folder open without services. Close any other servers on ports 8000 and 5173.

## Start and stop

```powershell
python -B scripts/course_demo.py run
```

Leave that PowerShell window open. Open `http://127.0.0.1:5173/` in Chrome. The backend runs at loopback port 8000; Vite at loopback port 5173. In a second PowerShell window, run `python -B scripts/course_demo.py stop` to close both services. The database remains available for a repeat until reset.

## Reset for a clean presentation

Stop the demo services first. Then run:

```powershell
python -B scripts/course_demo.py reset
python -B scripts/course_demo.py prepare
python -B scripts/course_demo.py run
```

`reset` requires the exact course-demo state marker and verified local PostgreSQL cluster; it removes only `mc_course_demo` and `.local/course-demo`. It regenerates the password. Do not point this tooling at a school server or use real evidence.

## Live sequence from the reset state

Use separate Chrome profiles/incognito windows or sign out between roles. All four usernames use the generated password: `demo.coordinator`, `demo.custodian`, `demo.reviewer`, `demo.viewer`.

1. **Coordinator:** Sign in. Dashboard starts with **0 of 8 complete (0%)**. Open **Requirements**, then **Faculty Documentation**. Show the two mandatory items and the separate missing requirements. Open **Manage assignments** to show `demo.custodian` as the assigned contributor. The assignment is pre-staged so the upload path is dependable.
2. **Custodian:** Open **Requirements → Faculty Documentation**. For each mandatory item, choose **Upload evidence**, give it a title, and use **Upload & Map** with the PDFs in `.local/course-demo/source/`: `fictional-faculty-plan.pdf` and `fictional-implementation-report.pdf`. Show the mapped versions and Repository history/scan state. Explain aloud that “clean” is a simulated verdict for these bytes only.
3. **Custodian:** Return to Faculty Documentation; choose **New package draft**. Add fictional notes, select both exact versions, save, and **Submit package**. The requirement becomes **For Verification**. Submission does not make it complete.
4. **Reviewer:** Sign in as `demo.reviewer`; open **Evidence Verification** and **Review package**. Inspect the submitted item names and exact version/checksum context. Use the protected preview/download if desired. Choose **Approve**, then **Record package decision**. This Reviewer is separate from the Custodian.
5. **Coordinator:** Reload Faculty Documentation. It is **Ready for Completion Review**. Choose **Mark Complete**, select the approved package, enter a rationale, and confirm. Only this separate Coordinator action makes it **Complete**.
6. **Coordinator:** Return to Dashboard: **1 of 8 = 12.5%**. Open **Reports** and show the cycle, area, timestamp, formula/provenance, and CSV/print options. Open **Search** for `Faculty`; open **Audit Trail** for the recorded events.
7. **Viewer:** Sign in as `demo.viewer`. Repository shows approved evidence only. A direct request for the package detail is denied (`404` in the captured rehearsal); use screenshot `19-scoped-denial.png` to show the boundary without constructing an ID live.

Optional after the core path: as Custodian upload a new fictional version and resubmit a new package. Explain that prior approvals remain historical while the newer submission needs its own decision. Do this only after the main 12.5% ending has been shown, because it changes the live state. Reset before repeating the core demo.

## Offline recovery

Open `SCREENSHOT_SEQUENCE.html` for a local-file walkthrough or use `PRESENTER_CUE_SHEET.md` and `screenshots/01-login.png` through `19-scoped-denial.png` in order. `screenshots/full/` holds full-page copies for zooming. Each screenshot is visibly labeled **fictional local demonstration**. The deck already embeds selected real app captures, so the PDF remains usable without PostgreSQL, Django, Vite, or network access.

If the live service fails, state that the screenshot sequence came from a completed local rehearsal. Continue with the screenshot sequence and the test record in `EVIDENCE.md`; do not call the screenshots a live result.

