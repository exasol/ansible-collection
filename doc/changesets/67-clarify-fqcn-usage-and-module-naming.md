---
orphan: true
---

# GH-67 Clarify FQCN Usage And Module Naming In User Guide

## Goal

Explain why examples use fully qualified collection names such as `exasol.exasol.exasol_query`, when short module names are acceptable, and how the namespace, collection, and module-name parts map to Ansible conventions.

## Scope

In scope:

* add traced user-facing documentation requirements for FQCN guidance
* update the user guide with FQCN terminology, the expected `exasol` repetition, and short-name usage with `collections`
* review existing user-guide examples for consistency with the FQCN recommendation
* update the unreleased changelog

Out of scope:

* changing module names, collection metadata, or runtime behavior
* converting integration-test playbook fragments or module documentation examples

## Design References

* [System Requirements](../system_requirements.md)
* [Design](../design_index.md)
* [Quality Requirements](../design/quality_requirements.md)
* [User Guide](../user_guide.rst)

## Strategy

Keep FQCNs as the recommended default for reusable and shared examples, and document the short form as valid only when the playbook declares `collections: [exasol.exasol]`.

## Task List

### Requirements And Design

- [x] Add traced requirement and scenario coverage for FQCN guidance
- [x] Record the documentation plan in this changeset

### Implementation

- [x] Add a user-guide section explaining namespace, collection, and module-name parts
- [x] Include examples for both `exasol.exasol.exasol_query` and short `exasol_query` usage
- [x] Review user-guide examples for consistency with the FQCN recommendation

### Verification

- [x] Run `poetry run nox -s requirements:trace`
- [x] Run focused OFT trace for `feat,req,scn,uman` coverage in `doc/system_requirements.md`
- [x] Run `poetry run nox -s collection:doc`
- [x] Run `poetry run nox -s docs:build`

### Update user documentation

- [x] Update the unreleased changelog entry
