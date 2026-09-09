# MC Accreditation Hub

First working increment for the Graduate School of Mabini Colleges, Inc. React + Vite + TypeScript, Django REST Framework, and PostgreSQL. The supplied Figma screenshots guide the login, sidebar, dashboard, area cards, requirements table, and repository. Upload and review screens extend that design.

## Local preview on this computer

Open **http://127.0.0.1:5173** after starting the services. The isolated development PostgreSQL cluster is under `.local/postgres`, bound to `127.0.0.1:55432`. It does not use the existing PostgreSQL service or its databases.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-local.ps1
```

Use `.local/demo-credentials.txt` for the generated local passwords. Demo users are `demo.coordinator`, `demo.custodian`, `demo.reviewer`, `demo.viewer`, and `demo.administrator`. The administrator manages accounts at `/api/admin/`, and deliberately has no implicit accreditation access. Other demo users have sample scope assignments. All seeded records are fictional.

Logs live in `.local/django-error.log` and `.local/vite.log`. Run the startup script only when the services are stopped; it does not replace processes already using the ports.

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
| Coordinator | Manage requirements, upload/map/submit and review in assigned cycle/areas |
| Reviewer | Read/download and review in assigned areas |
| Custodian | Read/download and upload/map/submit in assigned areas |
| Viewer | Read/download and monitor assigned cycle/areas |

No user can review their own upload or submission. Django scopes list, detail, search, review, and download operations. Shared documents expose only versions submitted into the recipient's areas, not future drafts. Sharing requires write authority in both the source and destination area. No public media route exists.

**Compliance:** `100 × complete active applicable requirements / total active applicable requirements`. Every mandatory item needs at least one approved, unexpired current submission across its mappings before a requirement becomes Ready for Completion Review. Only an assigned Coordinator's rationale-backed completion certification marks it Complete. Optional items do not affect completion. Non-applicable and draft requirements are excluded. An empty denominator returns `null`, displayed as N/A. Partial approved-item counts are shown separately. Status counts form mutually exclusive groups.

A new draft version does not affect an approved submission. Submitting a newer replacement makes its mapping pending. The previous approval remains historical. Expiry is inclusive of the valid-until date, evaluated in Asia/Manila. Closed cycles use their closure date.

Files are limited to 25 MB and PDF, DOCX, XLSX, PNG, JPEG. Validation checks actual format, parses PDFs/images, bounds Office archive expansion, and rejects encrypted PDFs and macro-bearing Office files. Files use random storage names and protected attachment downloads. Format validation is not malware scanning.

## Cycles and administration

Accounts and scope assignments are managed in `/api/admin/`. Deactivate users instead of deleting them. Workflow models are read-only in administration so staff cannot bypass version and review invariants.

Create a real cycle from an approved JSON structure:

```json
{"title":"Graduate School Cycle","program":"Graduate School","instrument":"Approved instrument edition","areas":[{"code":"A1","title":"Approved area title","icon":"📁"}]}
```

```powershell
python backend/manage.py create_cycle path/to/cycle.json
python backend/manage.py close_cycle 1
```

Only run `close_cycle` for the intended cycle ID. Closure is irreversible through the app, logs final summaries, and blocks further requirement, mapping, submission, review, and version changes to that cycle. Create new cycle records for subsequent assessments. Source versions can be explicitly reused in new-cycle mappings by authorized coordinators through the API; old decisions never transfer.

## Verification

```powershell
python backend/manage.py test hub --noinput
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
npm.cmd run build --prefix frontend
```

Backend tests run against a separate PostgreSQL test database. They cover authorization, protected downloads, approval/revision workflow, version history, expiry, exclusions, closed cycles, CSRF, file validation, and competing review transactions.

Browser tests require running frontend/backend services, the demo seed, and `.local/sample-evidence.pdf`. Generate that fixture with:

```powershell
python -c "from pypdf import PdfWriter; w=PdfWriter(); w.add_blank_page(width=595,height=842); w.write('.local/sample-evidence.pdf')"
cd frontend
npx playwright install chromium
npm run test:e2e
```

If using an existing compatible Chromium installation, set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to its executable path. Tests add clearly named fictional demonstration requirements and evidence to the demo cycle. They retain the history so it can be inspected. Screenshots are saved in `.local/screenshots/`.

## School-server preparation

Serve `frontend/dist` at `/` through a reverse proxy, and route `/api/` to Django. Serve Django's collected `/static/` files separately; never expose `private-media`. Use HTTPS, `DJANGO_DEBUG=0`, real host/origin settings, a dedicated database login, and a private storage path. Development servers and the local cluster are not production services.

Back up PostgreSQL and private files together, protect the backups, and verify restoration on a separate instance. Deployment sizing, hardened service configuration, malware scanning, monitoring, and backup scheduling require the school-server phase. Database administrators can alter database rows; the application audit trail is append-only through the application, not a cryptographic tamper-proof log.

Search checks only scoped requirement and document metadata. Compliance Reports provide scoped filters, printable output, and a CSV download. CSV fields that begin with spreadsheet formula characters are neutralized before export.

Notifications, advanced analytics, password recovery, two-factor authentication, and a separate readiness score are not included in this increment. Their nonfunctional navigation/controls are intentionally absent.

See [API contract](docs/API.md) and [validation record](docs/VALIDATION.md).
