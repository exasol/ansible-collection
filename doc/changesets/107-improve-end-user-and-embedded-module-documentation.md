---
orphan: true
---

# GH-107 Improve End-User And Embedded Module Documentation

## Goal

Give operators accurate, task-oriented Galaxy, user-guide, and embedded module
documentation for every public Exasol collection module.

## Scope

In scope:

* replace the development-oriented Galaxy README with an installation-oriented
  quick start and user-guide link
* add a getting-started guide for execution-environment-based use
* document lifecycle, idempotency, destructive-operation safeguards, and
  check-mode behavior for all public modules
* document the direct-SQL secret-exposure risk in ``exasol_query``
* add check-mode attributes and sensitive-option markers to embedded module
  documentation

Out of scope:

* runtime behavior or public parameter changes
* standalone Galaxy documentation pages for ``module_utils`` or
  ``doc_fragments``

## Design References

* [System Requirements](../system_requirements.md)
* [Design](../design_index.md)
* [Quality Requirements](../design/quality_requirements.md)
* [User Guide](../user_guide.rst)

## Task List

### Requirements And Design

- [x] Add traced requirements and scenarios for public module workflow and
  direct-SQL secret-exposure guidance
- [x] Record the documentation plan in this changeset

### Implementation

- [x] Replace Galaxy README development material with an end-user quick start
- [x] Add an execution-environment getting-started guide based on the local
  validation-project layout
- [x] Document all public module workflows in the user guide
- [x] Add direct-SQL secret-exposure warnings to the user guide and
  ``exasol_query`` documentation
- [x] Document check-mode support in every embedded module page
- [x] Mark documented sensitive options to match the runtime argument specs
- [x] State the grant privilege-list requirement in ``exasol_grants``

### Verification

- [x] Run `poetry run nox -s requirements:trace`
- [x] Run `poetry run nox -s collection:doc`
- [x] Run `poetry run nox -s docs:build`
- [x] Run `poetry run nox -s collection:sanity`

### Update User Documentation

- [x] Update the README and user guide
- [x] Update the unreleased changelog entry
