# System Requirements

## Introduction

The Exasol Ansible Collection lets operators automate Exasol administration
through Ansible modules. The executable Given-When-Then specifications are
maintained in `specs/ansible_modules/` and `specs/ansible_playbook/`.

## Notation

This document defines product features and requirements with OpenFastTrace.
Gherkin scenarios are OpenFastTrace `scn` items: each scenario declares its ID
in an `@id:scn~...~revision` tag and its parent requirement in a `# Covers:`
comment. This keeps the normative scenario text next to the executable module
and playbook specifications instead of duplicating it here.

## Features

### Exasol Administration Through Ansible
`feat~exasol-administration-through-ansible~1`

The collection provides declarative and imperative Exasol administration
workflows through public Ansible modules.

Status: draft

Needs: req

### Secure Exasol Administration
`feat~secure-exasol-administration~1`

The collection protects administrative credentials, preserves Exasol's
authorization boundary, and reports security-sensitive work safely.

Status: draft

Needs: req

## Module Requirements

Each requirement is covered by every scenario in the corresponding module
feature files under `specs/ansible_modules/` and `specs/ansible_playbook/`.

### exasol_info Module
`req~exasol-info-module~1`

`exasol_info` must gather basic Exasol server metadata through read-only
queries and report no state change.

Status: draft

Covers:
- `feat~exasol-administration-through-ansible~1`

Needs: scn

### exasol_query Module
`req~exasol-query-module~1`

`exasol_query` must execute requested SQL and bound arguments, report results
and changes accurately, and predict write effects in check mode.

Status: draft

Covers:
- `feat~exasol-administration-through-ansible~1`

Needs: scn

### exasol_script Module
`req~exasol-script-module~1`

`exasol_script` must execute ordered SQL scripts on one connection, preserve
statement semantics, report results, and predict write effects in check mode.

Status: draft

Covers:
- `feat~exasol-administration-through-ansible~1`

Needs: scn

### exasol_user Module
`req~exasol-user-module~1`

`exasol_user` must reconcile Exasol user lifecycle and authentication state,
including predictable idempotency and check-mode results.

Status: draft

Covers:
- `feat~exasol-administration-through-ansible~1`

Needs: scn

### exasol_role Module
`req~exasol-role-module~1`

`exasol_role` must reconcile Exasol role lifecycle state with predictable
idempotency and check-mode results.

Status: draft

Covers:
- `feat~exasol-administration-through-ansible~1`

Needs: scn

### exasol_grants Module
`req~exasol-grants-module~1`

`exasol_grants` must reconcile requested system, object, and role-membership
privileges without changing privileges that already match the requested state.

Status: draft

Covers:
- `feat~exasol-administration-through-ansible~1`

Needs: scn

### exasol_schema Module
`req~exasol-schema-module~1`

`exasol_schema` must reconcile schema lifecycle and intrinsic schema metadata,
including safe removal and check-mode prediction.

Status: draft

Covers:
- `feat~exasol-administration-through-ansible~1`

Needs: scn

## Security Requirements

Security requirements remain separate because their scenarios span more than
one module. Their Given-When-Then specifications are in
`specs/ansible_modules/security_requirements.feature`.

### Respect Exasol Authorization
`req~respect-exasol-authorization~1`

Collection operations execute with the permissions of the authenticated Exasol
account; the collection must not provide local privilege elevation.

Status: draft

Covers:
- `feat~secure-exasol-administration~1`

Needs: scn

### Protect Secret Values
`req~protect-secret-values~1`

Passwords and credentials must be redacted from task output and authentication
failures.

Status: draft

Covers:
- `feat~secure-exasol-administration~1`

Needs: scn

### Protect Exasol Transport
`req~protect-exasol-transport~2`

Connections must use encrypted transport and certificate validation by default,
with explicit trust anchoring for self-signed deployments.

Status: draft

Covers:
- `feat~secure-exasol-administration~1`

Needs: scn

### Keep Authorization Changes Predictable
`req~keep-authorization-changes-predictable~1`

User, role, and grant operations must reconcile only requested authorization
state and report changes accurately.

Status: draft

Covers:
- `feat~secure-exasol-administration~1`

Needs: scn

### Minimize Exasol Metadata Privileges
`req~minimize-exasol-metadata-privileges~1`

User and role lifecycle operations must use the least-privileged catalog views
that provide the metadata required for the operation.

Status: draft

Covers:
- `feat~secure-exasol-administration~1`

Needs: scn

### Preserve Exact Exasol Principal Identifiers
`req~preserve-exact-exasol-principal-identifiers~1`

User and role management must preserve exact Exasol identifier values.

Status: draft

Covers:
- `feat~secure-exasol-administration~1`

Needs: scn

### Keep Audit Output Secret-Safe
`req~keep-audit-output-secret-safe~1`

Module results must retain useful object identity while redacting secrets and
sensitive connection details.

Status: draft

Covers:
- `feat~secure-exasol-administration~1`

Needs: scn
