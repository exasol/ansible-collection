# 0.3.0 - 2026-07-20

## Summary

* Removed plugin module_utils layer
* Prepare publishing to Ansible Galaxy
* Only include required files into the uploaded bundle
* Implemented exasol_role module
* Implemented exasol_grants module
* Replaced stale GPL module headers with MIT references
* Split acceptance integration tests to ansible_playbook and ansible_modules types
* Implemented exasol_schema module
* Implemented exasol_info module
* Clarified Exasol collection FQCN usage in the user guide

## Security Issues

This release fixes vulnerabilities by updating dependencies:

| Dependency | Vulnerability | Affected | Fixed in |
|------------|---------------|----------|----------|
| ansible-core | CVE-2026-11332 | 2.17.14 | 2.16.19rc1 |
| ansible | PYSEC-2026-1119 | 10.7.0 | 12.2.0 |

## Security

* #75: Made certificate validation mandatory

## Features

* #38: Support exact Exasol user and role identifiers
* #36: Implement exasol_role module
* #80: Implement exasol_grants module
* #48: Automate publishing to Ansible Galaxy
* #81: Implement exasol_schema module
* #15: Implement exasol_info module
* #67: Clarify FQCN usage and module naming in the user guide

## Refactorings

* #49: Remove plugin module_utils layer
* #55: Refactor acceptance tests to use inline playbook fragments 2
* #54: Add exasol_query missing scenarios
* #64: Refactor exasol_user acceptance tests to use inline playbook fragments
* #56: Add end-to-end tests for Ansible collection and Python module
* #24: Add tests using Exasol DB versions 2025.1.11 and 2026.1.0
* #90: Split acceptance integration tests to ansible_playbook and ansible_modules types

## Bug Fixes

* #46: Pin runtime package versions across release artifacts
* #68: Replace stale GPL license headers with MIT references

## Dependency Updates

### `main`

* Updated dependency `sqlglot:30.11.0` to `30.12.0`

### `dev`

* Updated dependency `ansible:10.7.0` to `14.1.0`
* Added dependency `distlib:0.4.3`
* Updated dependency `exasol-ansible-runner-wrapper:2.0.0` to `3.0.0`
* Updated dependency `exasol-toolbox:10.0.0` to `10.2.1`
* Updated dependency `pytest-exasol-backend:1.4.1` to `1.5.0`
