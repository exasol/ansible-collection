---
orphan: true
---

# GH-81 Implement The Exasol Schema Module

## Goal

Provide idempotent Exasol schema lifecycle management through both Ansible
playbooks and the reusable Python runtime package.

## Scope

In scope:

* manage schema creation, unchanged state, rename, removal, and check-mode prediction
* reconcile schema owner, comment, and raw-size limit when requested
* preserve non-cascading drop safety unless `cascade=true` is explicit
* preserve exact schema identifier values in generated SQL
* keep playbook-backed and runtime-package integration scenarios synchronized
  with their respective Gherkin feature files

Out of scope:

* managing objects contained within schemas
* additive schema privileges, which belong to grant management
* virtual schema properties and refresh behavior

## Design References

* [System Requirements](../system_requirements.md)
* [Design](../design_index.md)
* [Runtime View](../design/runtime_view.md)
* [Quality Requirements](../design/quality_requirements.md)

## Strategy

Keep the collection module as a thin Ansible entry point over the reusable
schema runtime. Verify the same lifecycle behavior separately through generated
playbooks and direct calls to the runtime package's high-level entry point.

## Task List

### Requirements And Design

- [x] Confirm that separating the acceptance specifications changes verification structure, not schema behavior
- [x] Record the verification structure and runtime entry-point alignment in this changeset
- [x] Verify schema lifecycle SQL against the Exasol SQL reference
- [x] Specify intrinsic schema-property reconciliation and safe drop behavior

### Implementation

- [x] Move the playbook schema specification and test into the suite-specific layout
- [x] Align the playbook schema test with the shared scenario-ID and helper conventions
- [x] Add a high-level schema runtime entry point matching the other runtime modules
- [x] Add basic schema runtime scenarios and backend integration tests
- [x] Centralize SQL string-literal quoting in the shared query runtime
- [x] Normalize schema identifiers before direct catalog verification
- [x] Reconcile owner through `ALTER SCHEMA ... CHANGE OWNER`
- [x] Reconcile comments through `COMMENT ON SCHEMA`
- [x] Reconcile names through `RENAME SCHEMA`
- [x] Reconcile schema quota through `ALTER SCHEMA ... SET RAW_SIZE_LIMIT`
- [x] Keep owner, comment, rename, and quota unmanaged when omitted

### Verification

- [x] Run the scenario synchronization contract tests
- [x] Run targeted schema unit tests and collect the integration tests
- [x] Run the schema integration tests against an Exasol backend
- [x] Run focused SQL-literal, schema runtime, and scenario-contract tests
- [x] Run formatting checks
- [x] Run `poetry run nox -s requirements:trace`
- [x] Add runtime integration scenarios for every new schema behavior
- [x] Add representative playbook smoke scenarios for new schema behavior
- [x] Run updated schema unit and synchronization-contract tests
- [x] Run formatting, linting, typing, and requirement tracing
