---
orphan: true
---

# GH-56 Implement E2E Tests For `exasol_query`, `exasol_user`, And `exasol_role`

## Goal

Add end-to-end smoke coverage that proves the built Galaxy collection and the installed Python runtime package work together against a real Exasol backend.

## Scope

In scope:

* build the Ansible collection into a temporary local Galaxy archive
* install the collection into an isolated temporary collections path
* install the Python runtime package into a temporary Python environment
* run one smoke playbook each for `exasol_query`, `exasol_user`, and `exasol_role` through the installed artifacts
* reuse the existing backend-backed acceptance harness where possible

Out of scope:

* changes to user-facing requirements or architecture behavior
* expanding the full backend acceptance matrix for all modules
* release-process changes beyond automated verification

## Design References

* [System Requirements](../system_requirements.md)
* [Design](../design_index.md)
* [Quality Requirements](../design/quality_requirements.md)

## Strategy

Keep the existing source-checkout acceptance tests for broad backend coverage, and add a separate installed-artifact E2E path that validates the packaging boundary with minimal smoke scenarios.

## Task List

### Requirements And Design

- [x] Confirm that GH-56 is a verification and packaging concern, not a requirements or design behavior change
- [x] Record the implementation plan in the issue changeset

### Implementation

- [x] Create reusable test setup that builds and installs the collection into a temporary Galaxy path
- [x] Install the runtime package into a temporary Python environment used by the playbook run
- [x] Add one installed-artifact smoke test for `exasol_query`
- [x] Add one installed-artifact smoke test for `exasol_user`
- [x] Add one installed-artifact smoke test for `exasol_role`

### Verification

- [x] Run the targeted E2E smoke tests
- [x] Run `poetry run nox -s requirements:trace`
- [x] Run required collection validation gates that are feasible in the local environment
