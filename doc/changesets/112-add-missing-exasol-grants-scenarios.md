---
orphan: true
---

# Add Missing exasol_grants Scenarios

## Summary

Issue 112 expands `exasol_grants` coverage and adds role-membership grants.
This change adds the missing Ansible module runtime specification/test pair,
ports the existing playbook scenarios as direct runtime coverage, implements the
`roles` option for `GRANT <role> TO <principal>` and matching `REVOKE`, and
adds the remaining scenario coverage requested by the issue.

## Requirements and Design Impact

This change refines the existing predictable authorization reconciliation
behavior covered by `req~keep-authorization-changes-predictable~1` and the
grant-management design items:

* `dsn~authorization-state-reconciliation~1`
* `dsn~plan-authorization-lifecycle-sql-from-metadata~1`
* `dsn~derive-changed-from-planned-sql~1`
* `dsn~keep-check-mode-planning-deterministic-and-side-effect-free~1`

Role-membership idempotency is checked through `EXA_DBA_ROLE_PRIVS` using the
documented `GRANTEE`, `GRANTED_ROLE`, and `ADMIN_OPTION` columns.
System-privilege idempotency uses `EXA_DBA_SYS_PRIVS` including
`ADMIN_OPTION`. The `admin_option` module option manages `WITH ADMIN OPTION`
for system privileges and role memberships, and can be overridden on individual
`system_privileges` and `roles` dictionary entries.

## Tasks

- [x] Add `roles` to the grants runtime and Ansible argument spec.
- [x] Plan role membership grants and revokes from `EXA_DBA_ROLE_PRIVS`.
- [x] Add unit coverage for role membership grant, idempotency, revoke, and
  check mode.
- [x] Add `specs/ansible_modules/exasol_grants.feature`.
- [x] Add `test/integration/ansible_modules/test_exasol_grants.py` with the
  existing seven playbook scenarios as the module-runtime baseline.
- [x] Add module-runtime role-membership scenarios.
- [x] Add role-principal, object-type, check-mode, mixed-batch,
  revoke-idempotency, validation, exact-identifier, and sanitized-error
  scenarios from issue 112.
- [x] Add task-level and per-item `admin_option` support for system privileges
  and role memberships.
- [x] Update user-facing grant documentation for role memberships.
- [x] Run requirement tracing and integration verification.
