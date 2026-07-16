# Unreleased

## Summary

* Removed plugin module_utils layer
* Prepare publishing to Ansible Galaxy
* Only include required files into the uploaded bundle
* Implemented exasol_role module
* Replaced stale GPL module headers with MIT references
* Implemented exasol_info module

## Security

* #75: Made certificate validation mandatory

## Features

* #38: Support exact Exasol user and role identifiers
* #36: Implement exasol_role module
* #48: Automate publishing to Ansible Galaxy
* #15: Implement exasol_info module

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
