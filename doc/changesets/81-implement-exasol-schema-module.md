---
orphan: true
---

# GH-81 Implement The Exasol Schema Module

## Goal

Provide idempotent Exasol schema lifecycle management through both Ansible
playbooks and the reusable Python runtime package.

## Scope

In scope:

* manage schema creation, unchanged state, removal, and check-mode prediction
* preserve exact schema identifier values in generated SQL
* keep playbook-backed and runtime-package integration scenarios synchronized
  with their respective Gherkin feature files

Out of scope:

* managing objects contained within schemas
* changing the existing schema lifecycle behavior

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

### Implementation

- [x] Move the playbook schema specification and test into the suite-specific layout
- [x] Align the playbook schema test with the shared scenario-ID and helper conventions
- [x] Add a high-level schema runtime entry point matching the other runtime modules
- [x] Add basic schema runtime scenarios and backend integration tests

### Verification

- [x] Run the scenario synchronization contract tests
- [x] Run targeted schema unit tests and collect the integration tests
- [ ] Run the schema integration tests against an Exasol backend
- [x] Run formatting checks
- [x] Run `poetry run nox -s requirements:trace`
