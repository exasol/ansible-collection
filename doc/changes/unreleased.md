# Unreleased

## Summary

* Improved end-user and embedded module documentation for all public modules.
* Implemented exasol_script module
* Made `login_schema` the canonical Exasol connection schema parameter; the
  deprecated `login_db` alias remains compatible.
* Minimized metadata privileges and schema-qualified Exasol system-table queries

## Documentation

* #107: Improved end-user and embedded module documentation for all public modules.
* #133: Ansible confd: Define confd access-spike evaluation contract

## Security

* #129: Fix 16 Security Vulnerabilities

## Features

* #79: Implement exasol_script module
* #114: Make login_schema the canonical connection parameter

## Refactorings

* #116: Establish Traceability Between Gherkin Scenarios and Domain Design

## Bug Fixes

* #94: Minimize metadata privileges and schema-qualify Exasol system-table queries
* #101: Use SQL_IDENTIFIER_COMPARISON parameter for schema identifier comparison rule
* #102: exasol_schema: Support clearing an existing raw_size_limit

