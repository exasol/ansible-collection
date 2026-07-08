# Accountability, Compliance, and Auditability

The collection should make security-relevant actions reviewable without disclosing secrets.

## Main Threats

### Audit Output Exposes Secrets Or Sensitive Details
`thrt~audit-output-exposes-secrets-or-sensitive-details~1`

Security-relevant output intended for auditability could reveal secrets or other sensitive details in logs, CI records, or operator-visible results.

Status: draft

Needs: dsn

### Misleading Changed Reporting Obscures Security Impact
`thrt~misleading-changed-reporting-obscures-security-impact~1`

`changed` reporting that does not match emitted SQL could mislead operators about whether security-relevant state actually changed.

Status: draft

Needs: dsn

### Compliance-Relevant Integration Changes Go Unreviewed
`thrt~compliance-relevant-integration-changes-go-unreviewed~1`

If new integrations, release paths, or data-handling behavior are added without explicit compliance review, the project could miss obligations for audit, provenance, retention, or policy control.

Status: draft

Needs: dsn

### Local Reporting Competes With Authoritative Database Audit Trails
`thrt~local-reporting-competes-with-authoritative-database-audit-trails~1`

Collection-side reporting could be mistaken for the source of truth and weaken reliance on Exasol's authoritative audit trail for database actions.

Status: draft

Needs: dsn

## Required Controls

* keep `executed_queries` redacted but object-specific
* keep `changed` reporting aligned with emitted SQL so repeated runs are explainable
* preserve Exasol as the system of record for authentication, authorization, and server-side auditing
* treat secret leakage in task output, CI logs, or release logs as a release blocker

## Mitigations

### Expose Normalized Object Names Without Secret Values
`dsn~expose-normalized-object-names-without-secret-values~1`

Expose normalized object names while hiding secret values.

Status: draft

Covers:
- `scn~executed-queries-keep-object-names-but-redact-secrets~1`
- `thrt~sql-diagnostics-expose-confidential-script-content~1`
- `thrt~diffs-or-status-reporting-leak-sensitive-details~1`
- `thrt~audit-output-exposes-secrets-or-sensitive-details~1`

Needs: impl, utest

### Derive `changed` From Planned SQL
`dsn~derive-changed-from-planned-sql~1`

Set `changed=true` only when the planner has determined that the collection must emit state-changing SQL. If the requested state already matches Exasol metadata and no SQL should run, report `changed=false` so operators can trust repeated-run behavior and audit output.

Status: draft

Covers:
- `scn~repeated-runs-do-not-add-unrequested-authorization-changes~1`
- `thrt~unsafe-authorization-state-handling-changes-access~1`
- `thrt~diffs-or-status-reporting-leak-sensitive-details~1`
- `thrt~replayed-execution-repeats-destructive-effects~1`
- `thrt~misleading-changed-reporting-obscures-security-impact~1`

Needs: impl, utest, itest

### Rely On Exasol For Authoritative Audit Trails
`dsn~rely-on-exasol-for-authoritative-audit-trails~1`

Rely on Exasol for authoritative audit trails of database-side actions.

Status: draft

Covers:
- `thrt~unsafe-authorization-state-handling-changes-access~1`
- `thrt~local-reporting-competes-with-authoritative-database-audit-trails~1`

Needs: impl

### Require Explicit Compliance Review For Security-Relevant Integrations
`dsn~require-explicit-compliance-review-for-security-relevant-integrations~1`

Treat explicit compliance review as a release gate when the collection adds or changes security-relevant integrations, release services, or data-handling paths. The release workflow must require a decision on whether the change affects audit, provenance, retention, or policy scope before publication.

Status: draft

Covers:
- `thrt~compliance-relevant-integration-changes-go-unreviewed~1`

Needs: impl

## Applicable Questions

* How are privilege changes controlled and audited?
* Does the integration affect compliance scope?
* Is only the minimum required data shared or displayed?
