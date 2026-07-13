# Crosscutting Concepts

This chapter captures concepts that affect multiple parts of the architecture.

## Domain Model

The collection treats Exasol as the source of truth for users, roles, grants, authentication, authorization, and password state. An Ansible task supplies connection credentials and the desired administration state, while Exasol decides whether the authenticated account may perform the requested operation.

## Configuration

Connection credentials and user passwords are supplied through Ansible module parameters. The broader administration surface also carries role, grant-target, schema, and trusted-operator SQL inputs through module parameters, including the current `exasol_query` interface and any future `exasol_script` surface. The user guide recommends storing secret values in Ansible Vault instead of plain playbook variables.

Password update behavior is controlled by `update_password`:

* `on_create` sets a password only while creating a user.
* `always` attempts a password update for an existing user.

## Error Handling

Authentication failures and module errors must be sanitized before they are returned to Ansible. Error messages must not include connection passwords, user passwords, or other secret values.

## Logging and Observability

Secret values are marked with Ansible `no_log=True` where module parameters carry credentials or passwords. The collection does not add telemetry and must not emit credential material through task output.

## Security and Privacy

The collection does not bypass Exasol's authorization model. All operations execute using the permissions of the authenticated Exasol account.

The `exasol_user` module requires the connected account to already possess the corresponding administrative privileges. The collection does not implement privilege elevation.

Benefits:

* Existing Exasol authorization rules remain authoritative.
* Administrative boundaries are enforced by the database.
* Playbooks cannot grant permissions unavailable to the authenticated account.

Credentials and passwords are treated as sensitive values:

* `login_password` is marked with `no_log=True`.
* User passwords are marked with `no_log=True`.
* Authentication failures must not expose credentials.
* Error messages are sanitized before being returned to Ansible.

Exasol does not allow existing passwords to be retrieved or compared. This avoids exposing sensitive credential material through database introspection, but it intentionally limits idempotency for password updates. With `update_password=always`, an existing user password update can result in `changed=true` even when the submitted password value is unchanged.

### Exasol Authorization Enforcement
`dsn~exasol-authorization-enforcement~1`

The collection delegates authorization to Exasol and performs user administration using only the privileges of the authenticated Exasol account.

Status: draft

Covers:
- `scn~operation-uses-authenticated-exasol-permissions~1`

Needs: impl

### Secret Redaction
`dsn~secret-redaction~1`

The collection marks password-bearing parameters as `no_log=True`, redacts secret-bearing SQL before returning `executed_queries`, and sanitizes authentication failures before returning module results to Ansible.

Status: draft

Covers:
- `scn~password-not-exposed-in-failure-output~1`
- `scn~executed-queries-keep-object-names-but-redact-secrets~1`

Needs: impl, utest

### Password Update Semantics
`dsn~password-update-semantics~1`

The collection models Exasol's password comparison limitation explicitly: `update_password=on_create` avoids password updates for existing users, while `update_password=always` always sends a password update for existing users.

Status: draft

Covers:
- `scn~creation-only-password-update~1`
- `scn~forced-password-update~1`

Needs: impl, utest

### Authorization State Reconciliation
`dsn~authorization-state-reconciliation~1`

The collection reads current Exasol metadata before planning user, role, or grant lifecycle SQL and emits statements only when the requested security-relevant state differs from the current state. Password changes are an explicit exception: when `update_password=always`, the collection must still plan `ALTER USER` for existing users because Exasol does not expose the current password for comparison.

Status: draft

Covers:
- `scn~repeated-runs-do-not-add-unrequested-authorization-changes~1`

Needs: impl, utest, itest

### Encrypted Transport By Default
`dsn~encrypted-transport-by-default~2`

Shared connection handling always enables pyexasol encryption. Certificate
validation remains enabled by default. When operators disable CA validation for
self-signed deployments, they must provide a certificate fingerprint so the
connection still uses an explicit trust anchor instead of allowing an
untrusted TLS session.

Status: draft

Covers:
- `scn~exasol-connections-use-encrypted-transport-by-default~2`
- `scn~fingerprint-pinning-keeps-trust-explicit~1`
- `scn~untrusted-tls-overrides-are-rejected~1`

Needs: impl, utest

## Open Issues
