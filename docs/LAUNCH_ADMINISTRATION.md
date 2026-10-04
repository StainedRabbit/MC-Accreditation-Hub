# Launch administration runbook (D15 Option A, pending approval)

**Status:** Local implementation only. D15 remains **Pending Decision** until the Project Owner, School IT, and Academic Owner approve this launch substitution. D17 administrator-assisted recovery is provisional; School IT has not supplied its identity-verification or secure-delivery procedure. Use synthetic data until the separate D11/D12 approvals and target checks are complete.

## Separate operator assignments

School IT must record the actual named account, duties, grant date, revocation owner, management-network eligibility, and change ticket in its approved evidence repository. Put only the evidence reference in the [workshop tracker](PILOT_READINESS_WORKSHOP_TRACKER.md). Never enter passwords, reset credentials, unrestricted network details, or real operator names in this repository.

| Duty | Django permission | Allowed operation |
|---|---|---|
| Routine account administrator | hub.add_user, hub.change_user, hub.view_user | Create an ordinary user with an unusable password; edit ordinary account details; activate/deactivate other ordinary users with a reason. No self or privileged-target edits. |
| Academic grant operator | hub.manage_role_grants | Add or revoke one scoped Coordinator, Reviewer, Custodian, or Viewer grant through manage_grant. Cannot grant themselves or create a product Administrator grant. |
| Initial cycle provisioning operator | hub.provision_cycle | Create one active cycle and validated areas from approved JSON through create_cycle. |
| Credential operator | hub.reset_user_password and hub.view_user | Set an ordinary user's password through the separate reasoned admin route after the approved identity check. |
| Security audit reader | hub.view_security_audit | Read area-less institution security history; cannot read evidence without an academic grant. |

Every operator must be active Django staff. Assign each permission separately by a controlled School IT superuser process. One person may hold several only when the assignment record says so. Staff/model permissions do not create academic scope. Product roles do not create Django staff/model permissions. Keep superuser access for controlled break-glass work, and record its use and review outside this repository. The fictional seed_demo superuser is never a real assignment model.

## Routine account changes

Use /api/admin/hub/user/ from the approved management network. Enter a non-empty reason on every add or edit. New ordinary accounts start with an unusable password. The routine form cannot change staff/superuser flags, Django groups, permissions, passwords, or academic grants, and cannot edit the operator's own account or a staff/superuser/product Administrator target. Deactivate accounts rather than deleting them. The application writes one reasoned security audit event per successful account save. Failed form submissions do not write a change event.

School IT must define the identity and credential delivery steps for activating a new user or assisting recovery. A separate credential operator uses /api/admin/hub/user/USER_ID/password/, enters a new password and reason, and follows the approved private delivery procedure. The event contains actor, target, and reason, never the credential. This route rejects ordinary account admins and privileged targets except for break-glass superusers. Do not use it for real assisted recovery until the D17 procedure is approved and tested.

## Academic grant changes

Run from the IT-controlled application shell. The supplied --actor-id must match the named operator authenticated in the shell/operator log; correlate the command, time, and change ticket on the target host. The CLI ID alone is not proof of shell identity. Use current numeric IDs from the approved change request.

~~~powershell
python backend/manage.py manage_grant --actor-id GRANT_OPERATOR_ID --target-id USER_ID --role coordinator --cycle-id CYCLE_ID --action add --reason "Approved scope request"
python backend/manage.py manage_grant --actor-id GRANT_OPERATOR_ID --target-id USER_ID --role reviewer --cycle-id CYCLE_ID --area-id AREA_ID --action add --reason "Approved area review request"
python backend/manage.py manage_grant --actor-id GRANT_OPERATOR_ID --target-id USER_ID --role reviewer --cycle-id CYCLE_ID --area-id AREA_ID --action revoke --reason "Approved scope withdrawal"
~~~

Reviewer and Custodian require an area in the selected cycle. Coordinator and Viewer may be cycle-wide or area-scoped. Duplicate additions, missing revocations, invalid areas, self-grants, inactive targets for additions, and new administrator product grants fail without a change event. A successful add/revoke creates one security audit event. Revocation removes subsequent academic API access immediately; existing records remain preserved.

## Initial cycle provisioning

Prepare the approved structure using the JSON example in [README](../README.md#cycles-and-administration), then run:

~~~powershell
python backend/manage.py create_cycle path/to/cycle.json --actor-id PROVISION_OPERATOR_ID --reason "Approved cycle setup request"
~~~

The command requires an active staff operator with hub.provision_cycle. It validates the cycle fields and all area codes/titles, creates the active cycle and areas in one transaction, and writes one reasoned security event with the cycle and area IDs/codes. An invalid area rolls back the whole cycle. Authorized Coordinators can manage areas within their existing scoped application permissions after provisioning. Cycle closure is a separate lifecycle action with its existing explicit cycle-wide Coordinator rule.

## Target acceptance record

Before D15 approval, Project Owner, Academic Owner, and School IT must confirm the operator matrix, privilege-assignment and revocation process, break-glass custody, and whether these tools satisfy launch needs. School IT must demonstrate account form restrictions, admin-network isolation, grant revocation, CLI shell/actor correlation, audit retrieval and preservation, and credential recovery using synthetic accounts on the target environment. Record references and owners in the tracker; leave D15 Pending Decision and D17 provisional until their required authorities act.
