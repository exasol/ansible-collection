---
orphan: true
---

# GH-58 Document The Different Test Types In The Developer Guide

## Goal

Help contributors select and run the appropriate test layer by documenting the
collection's unit, contract, mocked collection integration, backend runtime,
playbook acceptance, and installed-artifact E2E tests.

## Scope

In scope:

* explain each existing test type and the boundary it verifies
* provide the relevant local test commands and backend-test safety guidance

Out of scope:

* changing test behavior, coverage, CI workflows, or backend configuration
* adding new product requirements or architecture behavior

## Design References

* [System Requirements](../system_requirements.md)
* [Design](../design_index.md)
* [Quality Requirements](../design/quality_requirements.md)

## Task List

### Requirements And Design

- [x] Confirm that GH-58 documents existing verification behavior and does not
  change requirements or design
- [x] Record the documentation plan in this changeset

### Implementation

- [x] Document the test types, the boundary each test layer verifies, and a
  CLI command for each type
- [x] Document focused backend-test execution and configuration in the
  developer guide

### Verification

- [x] Build the documentation
- [x] Run `poetry run nox -s requirements:trace`
