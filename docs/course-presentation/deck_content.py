"""Source-checked slide content for the MIT 007 course presentation.

Every claim is marked as a local implementation, a fictional example, an
institutional intention, or a pending decision. The original PPTX is a source,
not an instruction to claim deployment or approval.
"""

SLIDES = []


def add(title, lead, bullets=(), *, section='PROJECT', source='', status='LOCAL', image=None, caveat='', kind='standard'):
    SLIDES.append(dict(title=title, lead=lead, bullets=list(bullets), section=section,
                       source=source, status=status, image=image, caveat=caveat, kind=kind))


add('MC Accreditation Hub', 'A digital evidence and compliance platform for the Graduate School of Mabini Colleges, Inc.',
    ['MIT 007 — Cloud Computing', 'Proponent: Rainell John O. Abanto', 'Course presentation · October 2026'],
    section='TITLE', source='Original 11-slide MC_Accreditation_Hub.pptx; README.md', status='COURSE PROJECT', kind='cover')
add('The accreditation records problem', 'Evidence scattered across offices, folders, and devices takes time to verify and retrieve.',
    ['Requirements and files may be tracked separately.', 'Teams need to know which exact version was reviewed.',
     'Missing work is hard to see without a shared status view.', 'The presentation describes this problem; no time-savings study has been completed.'],
    source='Source presentation, slides 2–3', status='PROJECT RATIONALE')
add('Project objectives', 'The Hub brings requirements, files, review, monitoring, and reporting into one workflow.',
    ['Centralize accreditation-related records.', 'Classify evidence by area and requirement.',
     'Track missing and incomplete work.', 'Review submitted evidence independently.',
     'Retrieve authorized versions and produce preparation reports.'],
    source='Source presentation, slide 3; docs/MC_Accreditation_Hub.md', status='PROJECT SCOPE')
add('Scope and current state', 'A working local React and Django system supports the core evidence workflow.',
    ['Implemented locally: accounts and scoped roles, cycles, requirements, evidence versions, package review, certification, search, reports, and audit.',
     'Fictional demo data only; the sample instrument is not official PACUCOA criteria.',
     'School deployment, real-file intake, and institutional approval remain open.'],
    source='README.md; docs/PROGRESS.md; docs/D16_VERSION_1_BASELINE_PROPOSAL.md', status='LOCAL IMPLEMENTATION')
add('Users and responsibilities', 'Academic and technical duties have separate authority.',
    ['Custodian contributes assigned evidence; Reviewer makes an independent package decision.',
     'Coordinator manages requirements and deliberately certifies completion.',
     'Viewer monitors approved evidence; product Administrator has no automatic evidence authority.',
     'School IT operating roles require separate named assignments.'],
    source='README.md, Rules and access; docs/LAUNCH_ADMINISTRATION.md', status='LOCAL / PENDING POLICY')
add('End-to-end evidence workflow', 'A requirement becomes complete only after evidence review and a Coordinator decision.',
    ['Requirement and mandatory items → assigned contributor → versioned upload and mapping.',
     'Draft package → submit → independent Reviewer approval or revision request.',
     'Approved package → Coordinator certification with rationale → readiness update.',
     'History retains the pinned version, decision, and criteria context.'],
    source='backend/hub/models.py; backend/hub/views.py; docs/API.md', status='LOCAL IMPLEMENTATION')
add('Technology architecture', 'The browser uses a same-origin application API; PostgreSQL and private file storage stay behind Django.',
    ['React + Vite + TypeScript: browser interface.', 'Django REST Framework: session auth, permissions, workflow, reports.',
     'PostgreSQL: relational history and transactional constraints.', 'Protected filesystem: immutable evidence bytes; no public media route.'],
    source='README.md; backend/config/settings.py; frontend/package.json', status='LOCAL IMPLEMENTATION', kind='architecture')
add('Request and evidence data flow', 'Each request checks identity, scope, record state, and exact file availability.',
    ['Browser → /api/ session and CSRF → Django authorization.',
     'Django reads/writes PostgreSQL records and private file bytes.',
     'Upload scans the exact checksum; failed or absent verdicts quarantine the version.',
     'Approved evidence access remains scoped and audited.'],
    source='backend/hub/access.py; backend/hub/scanning.py; backend/hub/views.py', status='LOCAL IMPLEMENTATION')
add('Core data relationships', 'Cycles contain areas and requirements; evidence and decisions preserve exact history.',
    ['Cycle → Area → Requirement → Evidence Item.',
     'Document → immutable Document Version → scan verdict and item mapping.',
     'Requirement → Package Attempt → pinned versions → Reviewer decision.',
     'Requirement → Coordinator certification; Audit Event records actions.'],
    source='backend/hub/models.py; docs/D16_VERSION_1_BASELINE_PROPOSAL.md', status='LOCAL IMPLEMENTATION')
add('Cycles and requirements', 'Academic work is scoped to an assessment cycle and its areas.',
    ['Requirements include criteria, mandatory items, responsible office, and optional deadline.',
     'Active and applicable requirements form the readiness denominator.',
     'Closed cycles reject ordinary writes; archive is a separate reasoned lifecycle action.',
     'The demo cycle and eight requirements are fictional.'],
    source='backend/hub/models.py; backend/hub/compliance.py; backend/hub/management/commands/seed_demo.py', status='LOCAL IMPLEMENTATION')
add('Assignment and stewardship', 'A named Custodian assignment controls new requirement work.',
    ['A document records its owning area and steward.',
     'The steward replaces versions; scoped Coordinator exceptions require a reason.',
     'A team member cannot silently replace another person’s evidence.',
     'Academic owners still need to ratify this institutional role mapping.'],
    source='backend/hub/models.py; backend/hub/access.py; decision D04', status='LOCAL / PROVISIONAL')
add('Protected evidence versions', 'Replacement adds an immutable version instead of overwriting reviewed bytes.',
    ['Each version has its own checksum, uploader, timestamp, and optional validity date.',
     'A submitted package pins exact versions and criteria.',
     'Older reviews and certifications remain historical after a replacement.',
     'Downloads and inline previews require current authorization and a clean matching scan.'],
    source='backend/hub/models.py; backend/hub/scanning.py; docs/API.md', status='LOCAL IMPLEMENTATION')
add('Quarantine and scan boundary', 'A version stays unusable until a configured local scanner records a clean verdict for its checksum.',
    ['Absent, failed, infected, or mismatched scans block preview, download, mapping, review, and certification.',
     'The course demonstration uses a guarded synthetic verdict for two fictional PDFs only.',
     'School IT has not approved a real scanner or completed target tests.'],
    source='backend/hub/scanning.py; docs/DEPLOYMENT.md; decision D11', status='DEMO / PENDING APPROVAL',
    caveat='Never describe the demo fixture as malware protection for institutional files.')
add('Package attempts', 'New requirements use deliberate package drafts and immutable submitted attempts.',
    ['The owner selects exact mapped versions, adds notes, and submits the draft.',
     'A pending attempt can be withdrawn before review; revision work creates a new draft.',
     'Only one submitted attempt per requirement can await review.',
     'Older item-level submissions remain preserved as legacy history.'],
    source='backend/hub/models.py; backend/hub/views.py; decision D07', status='LOCAL / PROVISIONAL')
add('Independent review', 'Reviewers decide on submitted evidence in their assigned area.',
    ['The review dialog shows owner, submitted criteria, current criteria, exact filenames, and checksums.',
     'A Reviewer cannot approve their own upload or submission.',
     'Current new-package outcomes are Approve and Request revisions.',
     'A separate Reject outcome remains pending an Academic Owner rule.'],
    source='frontend/src/main.tsx; backend/hub/views.py; decision D07', status='LOCAL / PROVISIONAL')
add('Coordinator certification', 'Reviewer approval makes a requirement ready for completion review; it does not complete it.',
    ['The Coordinator selects approved support and records a rationale.',
     'The certification pins the package/version and criteria snapshot.',
     'Reopening adds a new reasoned record and removes the requirement from the completed count.',
     'Older unsupported certifications remain marked legacy.'],
    source='backend/hub/compliance.py; backend/hub/models.py; decision D05', status='LOCAL / PROVISIONAL')
add('Readiness calculation', 'Internal readiness uses unweighted Coordinator-certified requirements.',
    ['Readiness = 100 × complete active applicable non-archived requirements / all active applicable non-archived requirements.',
     'Draft, excluded, and archived requirements do not enter that population.',
     'Status filters change displayed rows, not the selected cycle/area readiness population.',
     'This is an internal preparation measure, never an official PACUCOA score.'],
    source='backend/hub/compliance.py; docs/API.md; decision D21', status='LOCAL / PROVISIONAL')
add('Live demonstration route', 'The fictional Faculty requirement shows the complete role handoff.',
    ['Start with 0 of 8 demo requirements complete.', 'Custodian maps two known fictional PDFs and submits one package.',
     'Reviewer approves; Coordinator certifies with a rationale.',
     'Report then shows 1 of 8 complete = 12.5%; Viewer package history is denied.'],
    source='docs/course-presentation/screenshots; frontend/course-demo-capture.mjs', status='FICTIONAL DEMO')
add('Dashboard before certification', 'The fictional cycle starts with eight active applicable requirements and no completions.',
    ['The initial internal readiness is 0%.', 'The sample data contains no official instrument or institutional evidence.'],
    section='APP WALKTHROUGH', source='screenshots/02-dashboard-before.png', status='FICTIONAL DEMO', image='02-dashboard-before.png')
add('Requirement and assignment', 'The Faculty requirement has two mandatory evidence items and an assigned Custodian.',
    ['The assignment narrows who may contribute new evidence.', 'Other seeded requirements remain Missing.'],
    section='APP WALKTHROUGH', source='screenshots/03-requirement-before.png; screenshots/04-assignment.png',
    status='FICTIONAL DEMO', image='03-requirement-before.png')
add('Evidence mapping and scan state', 'The Custodian uploads fictional PDFs and maps them to the two required items.',
    ['Versions remain immutable and checksum-linked.', 'The demo-only scan verdict is simulated and local.'],
    section='APP WALKTHROUGH', source='screenshots/05-evidence-mapped.png; screenshots/06-repository-and-scan.png',
    status='FICTIONAL DEMO', image='05-evidence-mapped.png')
add('Version history and simulated scan', 'The Repository displays the exact file version, its history, and the local scan state.',
    ['The known generated PDF received a simulated clean verdict in this isolated fixture.',
     'A later upload would add a version rather than overwrite these bytes.'],
    section='APP WALKTHROUGH', source='screenshots/06b-version-history-and-scan.png; scripts/course_demo_scanner.py',
    status='FICTIONAL DEMO', image='06b-version-history-and-scan.png',
    caveat='This simulated verdict is not an institutional malware scan.')
add('Package submission', 'The Custodian deliberately selects both item versions and submits a package.',
    ['Package status becomes For Verification.', 'The selected version and criteria context are retained.'],
    section='APP WALKTHROUGH', source='screenshots/07-package-draft.png; screenshots/08-package-submitted.png',
    status='FICTIONAL DEMO', image='08-package-submitted.png')
add('Reviewer context', 'The Reviewer sees the submitted criteria and exact pinned evidence before approving.',
    ['The Reviewer is a separate fictional account.', 'The new package Reject outcome is currently unavailable.'],
    section='APP WALKTHROUGH', source='screenshots/10-review-context.png', status='FICTIONAL DEMO', image='10-review-context.png')
add('Completion decision', 'After review, the Coordinator selects the approved package and records a rationale.',
    ['The requirement becomes Complete only after this step.', 'The history retains the earlier submitted and review records.'],
    section='APP WALKTHROUGH', source='screenshots/12-certification-dialog.png; screenshots/13-requirement-complete.png',
    status='FICTIONAL DEMO', image='13-requirement-complete.png')
add('Dashboard after certification', 'One of eight fictional requirements is complete: 12.5% internal readiness.',
    ['The calculation matches the report’s unfiltered cycle population.', 'This figure is a demo result, not an institutional accreditation rating.'],
    section='APP WALKTHROUGH', source='screenshots/14-dashboard-after.png', status='FICTIONAL DEMO', image='14-dashboard-after.png')
add('Reports and provenance', 'The report states its cycle, instrument, scope, population, formula version, and calculation time.',
    ['The captured fictional report shows 1 / 8 = 12.5%.', 'Area/status filters, print output, and formula-safe CSV are available.'],
    section='APP WALKTHROUGH', source='screenshots/15-compliance-report.png; docs/API.md',
    status='FICTIONAL DEMO', image='15-compliance-report.png')
add('Search, audit, and Viewer boundary', 'Search returns only authorized metadata; audit records actions with scoped access.',
    ['The Viewer can access approved evidence but cannot retrieve package history.',
     'A direct Viewer request for the demo package returned HTTP 404 in the local capture.'],
    section='APP WALKTHROUGH', source='screenshots/16-scoped-search.png; screenshots/17-audit-trail.png; screenshots/19-scoped-denial.png',
    status='FICTIONAL DEMO', image='16-scoped-search.png')
add('Security boundaries', 'Local controls cover login, sessions, CSRF, scoped queries, protected files, and audit history.',
    ['New accounts and grants require separate named operations and reasons.',
     'Recovery email stays disabled until school SMTP and HTTPS settings are approved.',
     'Target proxy, networks, scanner, retention, and restore checks remain open.'],
    section='VALIDATION', source='README.md; docs/DEPLOYMENT.md; docs/PROGRESS.md', status='LOCAL / TARGET PENDING')
add('Accessibility work', 'Shared dialogs, navigation, focus behavior, contrast, and named compliance meters received focused checks.',
    ['Keyboard dialog behavior and mobile navigation were tested locally.',
     'This does not claim a complete accessibility certification or replace screen-reader evaluation.'],
    section='VALIDATION', source='docs/PROGRESS.md, F24 checkpoint; frontend/e2e/accessibility-core.spec.ts', status='LOCAL TESTED')
add('Current verification evidence', 'Tests and the demo rehearsal provide dated local evidence for this checkout.',
    ['Django system check and migration dry run: passed.', 'Frontend TypeScript/Vite build: record current result in the evidence sheet.',
     'Backend PostgreSQL suite: record current count and result in the evidence sheet.',
     'The fictional browser capture completed the full role handoff and Viewer denial.'],
    section='VALIDATION', source='docs/course-presentation/EVIDENCE.md', status='LOCAL TESTED',
    caveat='Do not convert a local test pass into School IT target acceptance.')
add('Evaluation protocol', 'The thesis packet defines repeatable tasks but contains no participant results.',
    ['Retrieve an approved version and identify missing work.',
     'Submit/review fictional evidence and certify completion.',
     'Record elapsed time, success, errors, help needed, and participant feedback.',
     'Use consent and anonymous participant codes before any study.'],
    section='EVALUATION', source='docs/THESIS_EVALUATION.md', status='METHOD READY')
add('Results and limitations', 'Observed participant outcomes and target operations remain pending.',
    ['No usability sample size, comparison timing, or participant scores have been collected.',
     'No real institutional evidence, official instrument, or School IT server has been verified here.',
     'Performance and scalability are design goals until measured against an approved capacity target.'],
    section='EVALUATION', source='docs/THESIS_EVALUATION.md; docs/PROGRESS.md', status='PENDING EVIDENCE')
add('Institution-owned hosting intent', 'The source presentation proposes a school-owned, on-premises private-cloud model.',
    ['A Linux reference uses Nginx, Gunicorn, Django, PostgreSQL, and protected evidence storage.',
     'Actual server, proxy, networks, TLS, service owner, and private-cloud characteristics require School IT confirmation.',
     'The course demo runs only on the presenter’s loopback Windows laptop.'],
    section='OPERATIONS', source='Source presentation, slide 4; docs/DEPLOYMENT.md; decision D18', status='PROPOSED')
add('Backup and recovery', 'The repository contains backup, archive verification, and restore procedures.',
    ['A recoverable set includes database, evidence bytes, and required configuration.',
     'A separate-environment rehearsal must prove file and history restoration on the target.',
     'School IT must choose operators, backup destinations, retention, and recovery targets.'],
    section='OPERATIONS', source='docs/RESTORE.md; docs/RELEASE_CHECKLIST.md; decision D19', status='TARGET PENDING')
add('Sustainable development alignment', 'The project proposes contributions to education and institutional recordkeeping.',
    ['SDG 4: supports quality assurance preparation through organized evidence.',
     'SDG 9: applies digital infrastructure to institutional workflows.',
     'SDG 16: supports traceable decisions and records.',
     'These are intended alignments, not measured SDG outcomes.'],
    section='CONCLUSION', source='Source presentation, slide 9', status='PROJECT RATIONALE')
add('Next work after the class demo', 'The class package documents what works locally and what remains for institutional use.',
    ['Gather real evaluation results under the school’s research rules.',
     'Approve instrument, roles, file policy, and the D16 version 1 baseline.',
     'School IT must verify target scanning, HTTPS/proxy, capacity, backup, and restore.',
     'Keep real-evidence intake and production acceptance pending until those gates close.'],
    section='CONCLUSION', source='docs/PROGRESS.md; docs/PRODUCTION_ACCEPTANCE_DECISION_REGISTER.md', status='NEXT STEPS')
add('MC Accreditation Hub', 'Organized requirements, exact evidence versions, deliberate review, and traceable internal readiness.',
    ['Working fictional local demonstration.', 'School deployment and institutional approval remain future work.',
     'Questions and discussion'], section='CONCLUSION', source='Source presentation, slide 11; README.md',
    status='COURSE PROJECT', kind='closing')

# Appendix: readable detail that a presenter can open without crowding the main story.
add('Role and access matrix', 'Product roles are additive only inside explicit cycle/area grants.',
    ['Role | Draft | Submitted | Approved | Other authority',
     'Coordinator | Read/manage in grant | Read/review in grant | Read/download in grant | Certifies; cycle-wide grant for lifecycle',
     'Reviewer | Hidden | Read/review in area | Read/download in area | No self-review',
     'Custodian | Own work | Own submission | Shared approved | Assigned upload/map/submit',
     'Viewer | Hidden | Hidden | Read/download in grant | No package history',
     'Administrator | No implicit access | No implicit access | No implicit access | Account label only; separate operators'],
    section='APPENDIX', source='backend/hub/access.py; docs/PRODUCTION_ACCEPTANCE_DECISION_REGISTER.md',
    status='PROVISIONAL POLICY', kind='table')
add('Workflow state reference', 'A package decision and a completion certification are distinct records.',
    ['State | Trigger | Meaning | Next action',
     'Draft package | Custodian saves | Selected versions remain editable | Submit',
     'Submitted | Custodian submits | Attempt frozen; For Verification | Reviewer decision',
     'Approved | Reviewer approves | Evidence accepted; not Complete | Coordinator certification',
     'Revisions requested | Reviewer decides | Attempt closed; rationale retained | New draft and resubmit',
     'Withdrawn | Owner withdraws | Attempt closed before decision | New draft',
     'Complete | Coordinator certifies | Rationale and support pinned | Reasoned reopen if needed'],
    section='APPENDIX', source='backend/hub/compliance.py; backend/hub/models.py; decision D07',
    status='LOCAL / PROVISIONAL', kind='table')
add('Data and API reference', 'The current API is same-origin under /api/ and uses scoped integer and UUID identifiers.',
    ['Main entities: User, RoleAssignment, Cycle, Area, Requirement, EvidenceItem, Document, DocumentVersion.',
     'History: PackageAttempt/Item/Decision, RequirementCertification, DocumentScan, AuditEvent.',
     'Django owns permissions and transitions; the browser displays returned capabilities.',
     'API routes and data shapes are documented separately.'],
    section='APPENDIX', source='docs/API.md; backend/hub/models.py; backend/config/urls.py', status='LOCAL IMPLEMENTATION')
add('File and scan policy', 'Current local validation accepts PDF, DOCX, XLSX, PNG, and JPEG up to 25 MiB.',
    ['The application checks file content and bounds archive expansion.',
     'It quarantines unscanned, infected, failed, or checksum-mismatched versions.',
     'The course fixture simulates a clean verdict only for two known fictional PDFs.',
     'Accepted formats, resources, scanner, and records classes still need owner approval.'],
    section='APPENDIX', source='README.md; backend/hub/files.py; backend/hub/scanning.py; decisions D10–D12',
    status='LOCAL / PENDING POLICY')
add('Report calculation reference', 'Readiness and filtered row count answer different questions.',
    ['Numerator: complete active applicable non-archived requirements in the selected authorized cycle/area.',
     'Denominator: all active applicable non-archived requirements in that population.',
     'Status filters affect rows only; JSON, CSV, and print state the provenance.',
     'Fictional demo: 1 / 8 = 12.5%. The source deck’s 94 / 120 would equal 78.3%, not 87%.'],
    section='APPENDIX', source='backend/hub/compliance.py; docs/API.md; source presentation, slide 7',
    status='LOCAL / SAMPLE CORRECTED')
add('Test and screenshot inventory', 'Current test outputs belong in the evidence sheet with date, checkout, and environment.',
    ['Backend: workflow, permissions, scan quarantine, audit, and reporting checks.',
     'Frontend: TypeScript/Vite build and isolated browser workflows.',
     'Course capture: 19 viewport screenshots plus full-page copies, all fictional.',
     'The local checks do not substitute for a school HTTPS or restore rehearsal.'],
    section='APPENDIX', source='docs/course-presentation/EVIDENCE.md; frontend/course-demo-capture.mjs', status='LOCAL EVIDENCE')
add('Participant evaluation worksheet', 'Use comparable tasks and record actual results after consent.',
    ['Participant code, role, date, and environment.',
     'Task success, time, errors, assistance, and observed feedback.',
     'Compare like-for-like baseline and Hub tasks; report sample size and exclusions.',
     'No participant findings have been supplied for this deck.'],
    section='APPENDIX', source='docs/THESIS_EVALUATION.md', status='RESULTS PENDING')
add('Deployment and recovery gates', 'Real evidence requires more than a working local application.',
    ['D11 scanner and D12 records handling must be approved and verified.',
     'D18 network/admin boundary, D19 backup/restore, D20 capacity/operations, and D22 acceptance require School IT evidence.',
     'A synthetic browser test or archive checksum does not establish target acceptance.'],
    section='APPENDIX', source='docs/RELEASE_CHECKLIST.md; docs/PRODUCTION_ACCEPTANCE_DECISION_REGISTER.md',
    status='TARGET PENDING')
add('Corrections to the source deck', 'The presentation’s 11 slides supply the project concept; this course deck reports actual local behavior.',
    ['Slide 5 mentions Reject; new package Reject is unavailable pending an Academic Owner rule.',
     'Slide 6 says Coordinator review; the implementation separates Reviewer approval and Coordinator certification.',
     'Slide 7 shows 87% with 94 of 120 complete; that fraction is 78.3%.',
     'Slide 4 describes private cloud; school infrastructure has not been verified.'],
    section='APPENDIX', source='docs/MC_Accreditation_Hub.pptx; docs/PROGRESS.md', status='SOURCE RECONCILIATION')

DECISIONS = [
    ('D01', 'Cycle-wide authority', 'Provisional A', 'Academic Owner; Project Owner', 'Approve whole-cycle delegation and scope.'),
    ('D02', 'Evidence visibility', 'Provisional A', 'Security/Records; Academic Owner', 'Approve draft/history/file boundaries.'),
    ('D03', 'Sharing boundary', 'Provisional A', 'Security/Records; Academic Owner', 'Approve cross-scope and legacy retrieval.'),
    ('D04', 'Assignments/stewards', 'Provisional A', 'Academic Owner; Project Owner', 'Approve contributor and exception model.'),
    ('D05', 'Pinned certification', 'Provisional A', 'Academic Owner; Security/Records', 'Approve exact support and legacy treatment.'),
    ('D06', 'Criteria/applicability', 'Provisional A', 'Academic Owner; Security/Records', 'Approve reopen and decision history.'),
    ('D07', 'Package workflow', 'Provisional A', 'Academic Owner', 'Approve states and separate Reject rule.'),
    ('D08', 'Validity/expiry', 'Pending', 'Academic Owner; Security/Records', 'Choose warning or eligibility effect.'),
    ('D09', 'Audit access', 'Provisional A', 'Security/Records; IT; Academic Owner', 'Approve readers, fields, preservation.'),
    ('D10', 'Formats/limits', 'Pending', 'Academic Owner; IT; Security/Records', 'Approve type, byte limit, target bounds.'),
    ('D11', 'Malware scanning', 'Pending', 'Security/Records; IT', 'Approve scanner and target failure tests.'),
    ('D12', 'Records schedule', 'Pending', 'Security/Records; IT; Academic Owner', 'Approve classes, retention, holds, disposal.'),
    ('D13', 'Overdue rule', 'Pending', 'Academic Owner; Project Owner', 'Approve deadline and Manila boundary.'),
    ('D14', 'Archive lifecycle', 'Pending', 'Project; Academic; Security/Records', 'Approve transitions and preservation.'),
    ('D15', 'Launch administration', 'Pending', 'Project; IT; Academic Owner', 'Approve separate named operators.'),
    ('D16', 'Version 1 baseline', 'Pending', 'Project; Academic; IT; Security/Records', 'Resolve D01–D15 before ratification.'),
    ('D17', 'Account recovery', 'Provisional A', 'IT; Security/Records', 'Approve assisted recovery procedure.'),
    ('D18', 'Network/admin access', 'Provisional test A', 'IT; Security/Records', 'Supply actual proxy, TLS, admin networks.'),
    ('D19', 'Backup/recovery', 'Pending', 'IT; Security/Records', 'Assign target, operators, RPO/RTO, restore.'),
    ('D20', 'Capacity/operations', 'Pending', 'IT; Project; Security/Records', 'Measure pilot scale and service controls.'),
    ('D21', 'Report population', 'Provisional B', 'Academic Owner; Project Owner', 'Ratify filter/readiness behavior.'),
    ('D22', 'Acceptance evidence', 'Provisional local B', 'IT; Academic; Project Owner', 'Name target reviewers and record.'),
]
EFFECTS = {
    'D01': 'Pilot: lifecycle authority gate.',
    'D02': 'Real evidence: visibility gate.',
    'D03': 'Real evidence: sharing/search gate.',
    'D04': 'Real evidence: assignment gate.',
    'D05': 'Pilot: certification support gate.',
    'D06': 'Pilot: criteria history gate.',
    'D07': 'Pilot: package/review gate.',
    'D08': 'Pilot: validity rule gate.',
    'D09': 'Real evidence: audit access gate.',
    'D10': 'Real evidence: file policy gate.',
    'D11': 'Real evidence: approved scan required.',
    'D12': 'Real evidence: records control required.',
    'D13': 'Pilot: overdue semantics gate.',
    'D14': 'Pilot: archive lifecycle gate.',
    'D15': 'Pilot: named operators gate.',
    'D16': 'Pilot: no version 1 baseline yet.',
    'D17': 'Pilot: recovery procedure gate.',
    'D18': 'Pilot: target network test required.',
    'D19': 'Pilot: target restore proof required.',
    'D20': 'Pilot: capacity/operations proof required.',
    'D21': 'Pilot: report semantics gate.',
    'D22': 'Pilot: target acceptance record required.',
}
for start, end in [(0, 5), (5, 10), (10, 15), (15, 19), (19, 22)]:
    ids = f'D{start+1:02}–D{end:02}'
    rows = DECISIONS[start:end]
    add(f'Decisions {ids}', 'The selected option remains provisional until every listed owner records approval evidence.',
        [f'{code}  {label}  |  {status}  |  {owners}  |  {gate} {EFFECTS[code]}'
         for code, label, status, owners, gate in rows],
        section='APPENDIX · DECISION REGISTER', source='docs/PRODUCTION_ACCEPTANCE_DECISION_REGISTER.md',
        status='APPROVAL PENDING', kind='decisions')

add('Source and reading map', 'The deck connects the original concept to the current repository and its stated limits.',
    ['Source concept: docs/MC_Accreditation_Hub.pptx (11 slides).',
     'Implementation: README.md; docs/API.md; backend/hub; frontend/src.',
     'Verification and demo: docs/PROGRESS.md; course-presentation/EVIDENCE.md; captured screenshots.',
     'Policy and target gates: production decision register, D16 baseline proposal, release checklist.',
     'Evaluation: docs/THESIS_EVALUATION.md.'],
    section='APPENDIX', source='All named local repository sources', status='SOURCE INDEX')

for i, slide in enumerate(SLIDES):
    nxt = SLIDES[i + 1]['title'] if i + 1 < len(SLIDES) else 'Questions and discussion'
    slide['notes'] = (f"Point: {slide['lead']}\n"
                      + '\n'.join(f"Explain: {bullet}" for bullet in slide['bullets'])
                      + f"\nSource: {slide['source'] or 'Project repository.'}"
                      + f"\nLimit: {slide['caveat'] or 'This status is local, provisional, or proposed as labeled on the slide; it is not institutional approval or a participant finding.'}"
                      + f"\nTransition: {nxt}.")
