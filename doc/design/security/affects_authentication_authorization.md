# Affects Authentication / Authorization

Yes.

The collection authenticates to Exasol with `login_*` parameters and performs authorization-sensitive operations through `exasol_user`, `exasol_role`, `exasol_query`, planned grant-management and schema-management workflows, and future trusted-operator modules such as `exasol_grants`, `exasol_schema`, and `exasol_script`.

## Main Threats

### Incorrect Idempotency Or Grant Logic Changes Privileges
`thrt~incorrect-idempotency-or-grant-logic-changes-privileges~1`

Incorrect planning or grant logic could add privileges or mutate authorization state that the operator did not request.

Status: draft

Needs: dsn

### Reconciliation Drift Revokes Or Changes Authorization Unexpectedly
`thrt~reconciliation-drift-revokes-or-changes-authorization-unexpectedly~1`

Blind reconciliation or incomplete metadata checks could revoke privileges or otherwise drift authorization state away from the requested target.

Status: draft

Needs: dsn

### Over-Privileged Service Accounts Expand Blast Radius
`thrt~over-privileged-service-accounts-expand-blast-radius~1`

Automation accounts with more Exasol privileges than necessary could turn routine playbook execution into broader security-impacting changes.

Status: draft

Needs: dsn

### Privilege Changes Lack Reviewable Audit Context
`thrt~privilege-changes-lack-reviewable-audit-context~1`

If authorization changes are planned or reported unclearly, operators may not be able to verify what privilege change was attempted or rely on Exasol audit records to review it.

Status: draft

Needs: dsn

### Partial Authorization Failures Leave Inconsistent State
`thrt~partial-authorization-failures-leave-inconsistent-state~1`

Multi-step authorization changes that fail midway could leave user, role, or grant state inconsistent with the requested outcome.

Status: draft

Needs: dsn

## Required Controls

* keep authentication failure handling secret-safe
* rely on Exasol authorization instead of local privilege bypass logic
* document the required least-privilege database permissions per module
* verify repeated runs do not add, revoke, or report privileges incorrectly
* make multi-step authorization changes fail predictably and visibly

## Mitigations

### Surface Exasol Authorization Rejections Without Local Privilege Logic
`dsn~surface-exasol-authorization-rejections-without-local-privilege-logic~1`

When Exasol rejects an operation because the authenticated account lacks the required privilege, surface that rejection in sanitized form and stop. The collection must not retry with alternate credentials, emulate privilege checks locally, or add fallback behavior that could bypass or reinterpret Exasol authorization decisions.

Status: draft

Covers:
- `scn~operation-uses-authenticated-exasol-permissions~1`
- `thrt~upstream-errors-surface-sensitive-data~1`

Needs: impl, utest

### Plan Authorization Lifecycle SQL From Metadata
`dsn~plan-authorization-lifecycle-sql-from-metadata~1`

Read the current Exasol state first, compare it with the requested user, role, or grant state, and generate only the SQL statements required to close that gap. This avoids blind create, alter, revoke, or drop operations and keeps repeated runs predictable across grant-management flows as well as user and role lifecycle changes.

Status: draft

Covers:
- `scn~repeated-runs-do-not-add-unrequested-authorization-changes~1`
- `thrt~incorrect-idempotency-or-grant-logic-changes-privileges~1`
- `thrt~reconciliation-drift-revokes-or-changes-authorization-unexpectedly~1`
- `thrt~partial-authorization-failures-leave-inconsistent-state~1`

Needs: impl, utest, itest

### Delegate Authorization Decisions To Exasol
`dsn~delegate-authorization-decisions-to-exasol~1`

Keep authorization decisions delegated to Exasol instead of implementing local privilege logic.

Status: draft

Covers:
- `scn~operation-uses-authenticated-exasol-permissions~1`
- `thrt~over-privileged-service-accounts-expand-blast-radius~1`

Needs: impl

### Make Privilege Changes Reviewable Through Planned SQL And Exasol Audit Trails
`dsn~make-privilege-changes-reviewable-through-planned-sql-and-exasol-audit-trails~1`

Make privilege changes reviewable by deriving authorization-changing SQL from observed metadata, surfacing sanitized object-specific statements and `changed` reporting to the operator, and treating Exasol as the authoritative audit trail for the executed database actions.

Status: draft

Covers:
- `scn~repeated-runs-do-not-add-unrequested-authorization-changes~1`
- `thrt~privilege-changes-lack-reviewable-audit-context~1`
- `thrt~local-reporting-competes-with-authoritative-database-audit-trails~1`

Needs: impl, utest, itest

## Applicable Questions

* How does the connector authenticate to the third-party system?
* Are API endpoints authenticated and authorized?
* Can the connector operate with least-privilege permissions?
* How are privilege changes controlled and audited?
* What permissions are required by the connector in the third-party system?
