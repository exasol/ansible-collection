---
orphan: true
---

# GH-59 Add Python Package Integration Tests And Move Reusable Module Logic

## Goal

Add backend-backed integration tests for the `exasol-ansible-modules` Python runtime package and move reusable module logic out of the Ansible wrappers so runtime behavior can be debugged directly and measured by Python coverage tools without going through playbook execution.

## Scope

In scope:

* add direct pytest integration coverage for the runtime package APIs against a real Exasol backend
* cover representative query, user, and role lifecycle operations through the Python package
* reuse the existing backend fixture and cleanup model
* move reusable argument-spec, check-mode, and execution helpers from `plugins/modules/` into `exasol/ansible_modules/`
* keep the collection entrypoints in `plugins/modules/` as thin Ansible-facing wrappers

Out of scope:

* changes to user-facing requirements or architecture behavior
* replacing the existing playbook-backed acceptance coverage
* release or packaging workflow changes

## Design References

* [System Requirements](../system_requirements.md)
* [Design](../design_index.md)
* [Quality Requirements](../design/quality_requirements.md)

## Strategy

Keep the current playbook-backed acceptance tests for collection-level behavior, add a narrower integration layer that calls the Python runtime package directly through `pytest`, and reduce the collection modules to thin wrappers around the runtime package.

## Task List

### Requirements And Design

- [x] Confirm that GH-59 is a verification concern and does not require requirements or design changes
- [x] Record the implementation plan in the issue changeset

### Implementation

- [x] Move reusable query-module argument-spec, check-mode, and execution helpers into the Python runtime package
- [x] Move reusable user-module argument-spec and execution helpers into the Python runtime package
- [x] Move reusable role-module argument-spec and execution helpers into the Python runtime package
- [x] Keep the collection modules as thin Ansible-facing wrappers over the Python runtime package
- [x] Add direct backend integration coverage for the query runtime helpers
- [x] Add direct backend integration coverage for the user runtime lifecycle
- [x] Add direct backend integration coverage for the role runtime lifecycle

### Verification

- [ ] Run the targeted Python package integration tests
- [x] Run the targeted runtime unit tests for the extracted helpers
- [x] Run `poetry run nox -s requirements:trace`
