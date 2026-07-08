# Data At Rest, PII, and Local Persistence

The collection is not intended to become a secret store. Passwords, LDAP distinguished names, and connection credentials enter through Ansible variables and are forwarded to Exasol or `pyexasol` only for the lifetime of a task.

## Main Threats

### Persisted Credentials Or SQL Leak Secrets At Rest
`thrt~persisted-credentials-or-sql-leak-secrets-at-rest~1`

Locally persisted credentials, secret-bearing SQL, or cached identity data could expose secrets outside the task lifetime through files, caches, or artifacts.

Status: draft

Needs: dsn

### Sensitive Identifiers Leak Directory Or Personal Data
`thrt~sensitive-identifiers-leak-directory-or-personal-data~1`

LDAP distinguished names or similar identifiers could reveal directory structure, personal data, or sensitive organizational details if exposed unnecessarily.

Status: draft

Needs: dsn

## Required Controls

* keep secret values in Vault or equivalent external secret management
* do not persist credentials, raw SQL containing secrets, or cached identity data in collection-owned files
* keep returned data limited to object identifiers and redacted statements
* treat LDAP distinguished names as sensitive because they can expose directory structure and personal identifiers

## Mitigations

### Redact Sensitive Identifiers Unless Auditability Requires Them
`dsn~redact-sensitive-identifiers-unless-auditability-requires-them~1`

Redact sensitive identifiers from outputs where they are not needed for auditability.

Status: draft

Covers:
- `scn~executed-queries-keep-object-names-but-redact-secrets~1`
- `thrt~sql-diagnostics-expose-confidential-script-content~1`
- `thrt~sensitive-identifiers-leak-directory-or-personal-data~1`

Needs: impl, utest

### Keep Secret Handling Transient Within Task Execution
`dsn~keep-secret-handling-transient-within-task-execution~1`

Keep secret handling transient within the task lifecycle, without local credential caches or collection-owned secret stores.

Status: draft

Covers:
- `thrt~secrets-leak-through-logs-results-or-tracebacks~1`
- `thrt~persisted-credentials-or-sql-leak-secrets-at-rest~1`

Needs: impl
