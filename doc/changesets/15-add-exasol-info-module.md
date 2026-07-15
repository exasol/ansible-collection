---
orphan: true
---

# GH-15 Add `exasol_info` Module

## Goal

Add an `exasol_info` module that gathers basic Exasol server information for playbooks.

## Scope

In scope:

* add a public `exasol_info` Ansible module
* add reusable runtime logic in `exasol/ansible_modules/`
* return Exasol version, database name, and cluster size
* keep the module read-only with `changed=false`, including in check mode
* add unit, runtime integration, and acceptance coverage

Out of scope:

* broad server fact collection beyond version, database name, and cluster size
* changes to user, role, or query module behavior
* new runtime dependencies

## Design References

* [System Requirements](../system_requirements.md)
* [Design](../design_index.md)
* [Quality Requirements](../design/quality_requirements.md)

## Strategy

Reuse the shared Exasol connection and error-sanitization helpers, implement the new module as a thin wrapper over a small runtime helper, and query only the metadata required for the MVP contract.

## Task List

### Requirements And Design

- [x] Add permanent requirements and design traceability for `exasol_info`
- [x] Record the implementation plan in this changeset

### Implementation

- [x] Add reusable `exasol_info` runtime helpers in `exasol/ansible_modules/`
- [x] Add the public `plugins/modules/exasol_info.py` wrapper and documentation
- [x] Query Exasol version, database name, and cluster size through read-only metadata access
- [x] Keep `changed=false` in normal and check mode execution

### Verification

- [x] Add unit coverage for `exasol_info`
- [x] Add backend integration coverage for the runtime helper
- [x] Add acceptance coverage matching `specs/exasol_info.feature`
- [x] Run targeted tests and feasible local verification gates
