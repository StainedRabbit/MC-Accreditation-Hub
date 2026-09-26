# MC Accreditation Hub

First working increment for the Graduate School of Mabini Colleges, Inc. React + Vite + TypeScript, Django REST Framework, and PostgreSQL. The supplied Figma screenshots guide the login, sidebar, dashboard, area cards, requirements table, and repository. Upload and review screens extend that design.

## Local preview on this computer

Open **http://127.0.0.1:5173** after starting the services. The isolated development PostgreSQL cluster is under `.local/postgres`, bound to `127.0.0.1:55432`. It does not use the existing PostgreSQL service or its databases. Use fictional data and local-only accounts; do not upload institutional evidence.

```powershell
cd 'C:\Projects\My Projects\Graduate School Accreditation Hub'
& 'C:\Program Files\PostgreSQL\18\bin\postgres.exe' -D '.local\postgres' -p 55432 -h 127.0.0.1
```

Leave that PostgreSQL window open. In a second PowerShell window, activate the project environment and run:

```powershell
cd 'C:\Projects\My Projects\Graduate School Accreditation Hub'
$env:PGHOST='127.0.0.1'; $env:PGPORT='55432'; $env:PASSWORD_RESET_ENABLED='0'
py backend/manage.py migrate
py backend/manage.py runserver 127.0.0.1:8000
```

In a third PowerShell window, run `npm.cmd run dev --prefix frontend -- --host 127.0.0.1` from the project root. These commands are for this computer's isolated local cluster; use the Fresh installation steps below on other machines. `scripts/start-local.ps1` now fails explicitly because the previous launcher contained only comments and started nothing.

Use `.local/demo-credentials.txt` for the generated local passwords. Demo users are `demo.coordinator`, `demo.custodian`, `demo.reviewer`, `demo.viewer`, and `demo.administrator`. The administrator manages accounts at `/api/admin/`, and deliberately has no implicit accreditation access. Other demo users have sample scope assignments. All seeded records are fictional.

The three terminal windows show service output directly. Stop each service with **Ctrl+C** after testing.

## Fresh installation

Requirements: Python 3.13+, Node 22.12+, PostgreSQL 17+. No SQLite fallback is configured.

1. Create a PostgreSQL database and login owned by this project. For test execution the test login needs permission to create a test database.
2. Copy `.env.example` to `.env`, generate a long random `DJANGO_SECRET_KEY`, and enter your database connection. Do not commit `.env`.
3. Install and initialize:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r backend/requirements.txt
.venv\Scripts\python backend/manage.py migrate
npm.cmd ci --prefix frontend
.venv\Scripts\python backend/manage.py createsuperuser
```

4. Optionally create fictional demo data explicitly:

```powershell
.venv\Scripts\python scripts/prepare_demo.py
```

This generates a demo-only password and writes it to ignored `.local/demo-credentials.txt`. Alternatively set `MC_DEMO_PASSWORD` securely in your shell and run `python backend/manage.py seed_demo`. The seed command refuses to overwrite existing users. Never use real institutional evidence in the demo environment.

5. In separate terminals:

```powershell
.venv\Scripts\python backend/manage.py runserver 127.0.0.1:8000
```

```powershell
npm.cmd run dev --prefix frontend
```

The browser uses port 5173. Vite proxies `/api/` to Django. Cookies and CSRF requests use the same browser origin.

## Demonstrate the first workflow

1. Sign in as Coordinator. Open Requirements and add an active requirement with mandatory evidence items.
2. Sign in as Custodian, open that requirement, and choose Upload evidence. Upload a supported file and submit it.
3. Sign in as Reviewer in another browser session. Open Evidence Verification, download the exact version, and record approval, a revision request, or rejection. Revision/rejection comments are required.
4. For revisions, return to the requirement as Custodian and use Upload new version. The previous file and decision remain in history. Submit the replacement and review it separately.
5. After all mandatory evidence is approved, sign in as Coordinator and certify the requirement with a rationale. Only this Coordinator certification marks it Complete and updates compliance; reopening also requires a rationale.

Use Existing Document maps a chosen version to an additional evidence item. Every mapping has an independent decision. Repository uploads create drafts; they do not change compliance until submitted as replacements.

## Rules and access

| Role | Access |
|---|---|
| Administrator | Django account administration; explicit extra assignments required for accreditation access |
| Coordinator | All evidence/history in explicit scope; only a cycle-wide Coordinator grant may close/reopen a cycle |
| Reviewer | Submitted evidence and its review context in assigned areas; drafts remain hidden |
| Custodian | Current Contributor implementation: own document/upload/submission plus approved shared evidence; area write behavior awaits D04 |
| Viewer | Approved evidence only; drafts, submissions, and review history remain hidden |

No user can review their own upload or submission. Django scopes list, detail, search, review, and download operations through one default-deny visibility policy; see the [provisional decision matrix](docs/PRODUCTION_ACCEPTANCE_DECISION_REGISTER.md#provisional-d01d03-access-control-matrix). New evidence mappings/submissions must remain in the document's owning area and cycle. Existing immutable cross-scope history is retained, but no new sharing is allowed. No public media route exists. D01–D03 remain provisional pending Academic Owner and Security/Records Owner sign-off.

**Compliance:** `100 × complete active applicable requirements / total active applicable requirements`. Every mandatory item needs at least one approved, unexpired current submission across its mappings before a requirement becomes Ready for Completion Review. Only an assigned Coordinator's rationale-backed completion certification marks it Complete. Optional items do not affect completion. Non-applicable and draft requirements are excluded. An empty denominator returns `null`, displayed as N/A. Partial approved-item counts are shown separately. Status counts form mutually exclusive groups.

A new draft version does not affect an approved submission. Submitting a newer replacement makes its mapping pending. The previous approval remains historical. Expiry is inclusive of the valid-until date, evaluated in Asia/Manila. Closed cycles use their closure date.

Files are limited to 25 MB and PDF, DOCX, XLSX, PNG, JPEG. Upload endpoints check the current assignment, scope, stewardship or reasoned override, and active cycle before application file-content validation; they recheck authority under the write transaction. Validation checks actual format, parses PDFs/images, bounds Office archive expansion, and rejects encrypted PDFs and macro-bearing Office files. Files use random storage names and protected attachment downloads. Format validation is not malware scanning. D10 still requires school approval of formats, size, and resource limits before real evidence use.

## Cycles and administration

Accounts and scope assignments are managed in `/api/admin/`. Deactivate users instead of deleting them. Workflow models are read-only in administration so staff cannot bypass version and review invariants.

Create a real cycle from an approved JSON structure:

```json
{"title":"Graduate School Cycle","program":"Graduate School","instrument":"Approved instrument edition","areas":[{"code":"A1","title":"Approved area title","icon":"📁"}]}
```

```powershell
python backend/manage.py create_cycle path/to/cycle.json
python backend/manage.py close_cycle CYCLE_ID --actor-id STAFF_USER_ID --reason "Operator-approved cycle close rationale"
```

Only run `close_cycle` for the intended cycle ID with a named active staff operator who also has an explicit cycle-wide Coordinator grant, and an approved reason, when operating directly from the server. In the application, an assigned Coordinator can close or reopen a cycle from the Dashboard, but both actions require a recorded reason. A closed cycle blocks further requirement, mapping, submission, review, and version changes; downloads remain available. Reopening is exceptional and fully audited. Create new cycle records for subsequent assessments. Source versions can be explicitly reused in new-cycle mappings by authorized coordinators through the API; old decisions never transfer.

## Account recovery

Signed-in users can change their own password from Account security in the sidebar. **Administrator-assisted recovery is the pilot path.** The user contacts an authorized school administrator through the established school channel. The administrator verifies identity through the school's approved process, resets the account through account administration, communicates the new credential through an approved private channel, and instructs the user to change it after sign-in. School IT must approve and test that procedure; this repository does not claim that institutional procedure has been completed.

Self-service recovery email remains disabled by default. A disabled or incomplete configuration tells users to contact an administrator. School IT must confirm an authenticated encrypted institutional SMTP service and public HTTPS URL before considering enablement. The required settings are:

```text
PASSWORD_RESET_ENABLED=1
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DEFAULT_FROM_EMAIL=accreditation@example.edu
EMAIL_HOST=smtp.example.edu
EMAIL_PORT=587
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
EMAIL_USE_TLS=1
EMAIL_USE_SSL=0
EMAIL_TIMEOUT=10
PASSWORD_RESET_FRONTEND_URL=https://accreditation.example.edu/
```

These are examples, not verified school settings. The endpoint rejects console/dummy backends, placeholders, missing credentials, unencrypted SMTP, and non-HTTPS reset URLs. It gives the same account-neutral response whether an address exists or SMTP fails, without claiming delivery. Reset links put the token in the URL fragment, which is removed from browser history on opening; the fragment is not sent to the web server. School IT must still verify actual delivery and the deployed logging policy before enabling the flag. Do not put reset links, credentials, or request bodies in logs or tickets.

## Verification

```powershell
python backend/manage.py test hub --noinput
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
npm.cmd run build --prefix frontend
```

Backend tests run against a separate PostgreSQL test database. They cover authorization, protected downloads, approval/revision workflow, version history, expiry, exclusions, closed cycles, CSRF, file validation, and competing review transactions.

For an isolated synthetic browser run on this computer, start only the repository-local PostgreSQL cluster at `127.0.0.1:55432`, install the existing frontend dependencies, then run from the project root:

```powershell
$env:PLAYWRIGHT_CHROMIUM_EXECUTABLE='C:\Program Files\Google\Chrome\Application\chrome.exe'
python -B scripts/run_isolated_browser.py
```

The runner verifies that PostgreSQL uses `.local/postgres`, creates a randomly named temporary database and private media directory, seeds only fictional accounts, starts Django and Vite on temporary loopback ports, runs the existing browser suite followed by the F25 account-changing tests, and removes the database, media, and browser artifacts afterward. To run just the new tests, pass `isolated-session.spec.ts`. Recovery remains disabled and the runner does not use ambient PostgreSQL or email passwords. This is a local development check, not a school HTTPS/proxy or database-outage rehearsal.

Direct `npm.cmd run test:e2e --prefix frontend` still uses already running frontend/backend services and the persistent demo database. It requires the demo seed and `.local/sample-evidence.pdf`; generate that fixture with:

```powershell
python -c "from pypdf import PdfWriter; w=PdfWriter(); w.add_blank_page(width=595,height=842); w.write('.local/sample-evidence.pdf')"
cd frontend
npx playwright install chromium
npm run test:e2e
```

If using an existing compatible Chromium installation, set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to its executable path. Direct runs retain their fictional workflow history; the isolated runner discards it. Playwright failure artifacts from direct runs go to the ignored `frontend/test-results/` directory.

## School-server deployment and recovery

The repository now includes a school-owned Linux reference deployment using Nginx, systemd, Gunicorn, PostgreSQL, and protected evidence storage. Follow [the deployment reference](docs/DEPLOYMENT.md), [release checklist](docs/RELEASE_CHECKLIST.md), and [backup/restore procedure](docs/RESTORE.md). The reference uses the production frontend build, never Vite, and has no public route to `private-media`.

Back up PostgreSQL and private files as one protected set, replicate it to a separately approved failure domain, and prove an isolated restoration before accepting real evidence. The deployment and restoration artifacts are ready for school IT; no school-server deployment or recovery rehearsal has been claimed from this local workspace. Database administrators can alter database rows; the application audit trail is append-only through the application, not a cryptographic tamper-proof log.

Search checks only scoped requirement and document metadata. Compliance Reports provide scoped filters, printable output, and a CSV download. CSV fields that begin with spreadsheet formula characters are neutralized before export.

Notifications, advanced analytics, two-factor authentication, and a separate readiness score are not included in this increment. Their nonfunctional navigation/controls are intentionally absent.

See [API contract](docs/API.md), [deployment guidance](docs/DEPLOYMENT.md), and [thesis evaluation packet](docs/THESIS_EVALUATION.md).
