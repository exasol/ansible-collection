---
orphan: true
---

# GH-94 Minimize Metadata Privileges

## Goal

Allow password-based user operations, user removal, and role lifecycle
operations to run without `SELECT ANY DICTIONARY`, while retaining LDAP
distinguished-name reconciliation for accounts that have the required catalog
access.

## Scope

In scope:

* qualify collection-owned Exasol catalog queries with `SYS.` where the view
  is exposed in that schema
* use `SYS.EXA_ALL_USERS` and `SYS.EXA_ALL_ROLES` for existence checks
* query `SYS.EXA_DBA_USERS` only for an existing LDAP user's distinguished name
* add regression coverage for least-privilege metadata planning

Compatibility exception:

* `EXA_SYSTEM_EVENTS` is a statistical system table and must use its owning
  schema, `EXA_STATISTICS`, rather than `SYS`.

Out of scope:

* changing the Exasol privileges required to execute user or role DDL
* removing the privileged `SYS.EXA_DBA_USERS` access prerequisite for LDAP
  distinguished-name comparison; LDAP idempotency remains supported when the
  authenticated account has `SELECT ANY DICTIONARY`

## Design References

* [System Requirements](../system_requirements.md)
* [Crosscutting Concepts](../design/crosscutting_concepts.md)
* [Authorization](../design/security/affects_authentication_authorization.md)
* [Quality Requirements](../design/quality_requirements.md)

## Task List

### Requirements And Design

- [x] Specify least-privilege metadata access for user and role lifecycle
  planning.
- [x] Define the separate user-existence and LDAP distinguished-name probes.

### Implementation

- [x] Schema-qualify collection-owned system-table queries.
- [x] Use `SYS.EXA_ALL_USERS` and `SYS.EXA_ALL_ROLES` for existence checks.
- [x] Restrict `SYS.EXA_DBA_USERS` access to existing LDAP-user reconciliation.

### Verification

- [x] Add unit regression tests for password user operations and role operations
  without privileged user metadata access.
- [x] Add a separate unit regression test for LDAP metadata lookup.
- [x] Reach 100% statement coverage for the #94-affected user, role, and info
  runtime modules.
- [x] Run focused unit tests and OpenFastTrace tracing.
- [x] Run required collection documentation checks.
- [x] Run the required collection sanity check.
