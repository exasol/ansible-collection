# Introduces or Modifies Sensitive Data Handling, Security-Relevant Processing, or Data Access Behavior

Yes.

The change processes passwords, usernames, role names, privileges, and possibly SQL scripts that may embed sensitive values.

## Main Threats

### Secrets Leak Through Logs, Results, Or Tracebacks
`thrt~secrets-leak-through-logs-results-or-tracebacks~1`

Secret values could be exposed through task output, returned fields, exception traces, or test diagnostics.

Status: draft

Needs: dsn

### SQL Diagnostics Expose Confidential Script Content
`thrt~sql-diagnostics-expose-confidential-script-content~1`

Returned SQL or surfaced diagnostics could reveal confidential values embedded in administrative statements or operator-supplied scripts.

Status: draft

Needs: dsn

### Unsafe Authorization-State Handling Changes Access
`thrt~unsafe-authorization-state-handling-changes-access~1`

Incorrect handling of user, role, or grant state could create unauthorized access changes or fail to preserve the intended security posture.

Status: draft

Needs: dsn

### Diffs Or Status Reporting Leak Sensitive Details
`thrt~diffs-or-status-reporting-leak-sensitive-details~1`

Task diffs, `changed` reporting, or debug output could reveal sensitive information or mislead operators about security-relevant actions.

Status: draft

Needs: dsn

### Replayed Execution Repeats Destructive Effects
`thrt~replayed-execution-repeats-destructive-effects~1`

Repeated or replayed execution could reapply destructive or privilege-changing actions beyond the operator's intent.

Status: draft

Needs: dsn

## Required Controls

* reuse shared secret-redaction helpers for parameters and exceptions
* avoid storing secrets locally in the collection
* keep module outputs minimal and free of raw credentials or script contents
* add tests for redaction and authorization-state correctness
* ensure replayed runs do not expose additional data or corrupt state

## Mitigations

### Mark Secret-Bearing Parameters With `no_log=True`
`dsn~mark-secret-bearing-parameters-no-log~1`

Mark secret-bearing module parameters with `no_log=True`.

Status: draft

Covers:
- `scn~password-not-exposed-in-failure-output~1`
- `thrt~secrets-leak-through-logs-results-or-tracebacks~1`

Needs: impl, utest

### Redact Secrets From SQL And Surfaced Failures
`dsn~redact-secrets-from-sql-and-surfaced-failures~1`

Redact passwords and LDAP distinguished names from returned SQL and surfaced failures.

Status: draft

Covers:
- `scn~executed-queries-keep-object-names-but-redact-secrets~1`
- `thrt~secrets-leak-through-logs-results-or-tracebacks~1`
- `thrt~sql-diagnostics-expose-confidential-script-content~1`

Needs: impl, utest

## Applicable Questions

* Are secrets ever exposed in logs, monitoring systems, or configuration files?
* Is PII exposure in logs, monitoring, or error messages prevented?
* Is only the minimum required data shared or displayed?
