# 0.4.0 - 2026-08-19

## Summary

* Improved end-user and embedded module documentation for all public modules.
* Implemented exasol_script module
* Made `login_schema` the canonical Exasol connection schema parameter; the
  deprecated `login_db` alias remains compatible.
* Minimized metadata privileges and schema-qualified Exasol system-table queries

## Security Issues

This release fixes vulnerabilities by updating dependencies:

| Dependency | Vulnerability | Affected | Fixed in |
|------------|---------------|----------|----------|
| cryptography | PYSEC-2026-3552 | 49.0.0 | 50.0.0 |
| gitpython | GHSA-3rp5-jjmw-4wv2 | 3.1.51 | 3.1.53 |
| gitpython | GHSA-fjr4-x663-mwxc | 3.1.51 | 3.1.54 |
| gitpython | GHSA-6p8h-3wgx-97gf | 3.1.51 | 3.1.54 |
| gitpython | GHSA-r9mr-m37c-5fr3 | 3.1.51 | 3.1.54 |
| gitpython | GHSA-94p4-4cq8-9g67 | 3.1.51 | 3.1.55 |
| gitpython | CVE-2026-73620 | 3.1.51 | 3.1.57 |
| gitpython | GHSA-p538-c434-8v24 | 3.1.51 | 3.1.56 |
| gitpython | GHSA-9rj7-rf2p-w77r | 3.1.51 | 3.1.58 |
| gitpython | GHSA-4gmw-gg2m-w46p | 3.1.51 | 3.1.58 |
| gitpython | GHSA-hh9p-6wh2-4mfc | 3.1.51 | 3.1.58 |
| gitpython | GHSA-wvpp-8hx9-p66j | 3.1.51 | 3.1.58 |
| gitpython | GHSA-jm78-9fvv-mhgr | 3.1.51 | 3.1.58 |

## Documentation

* #107: Improved end-user and embedded module documentation for all public modules.

## Features

* #79: Implement exasol_script module
* #114: Make login_schema the canonical connection parameter

## Bug Fixes

* #94: Minimize metadata privileges and schema-qualify Exasol system-table queries
* #101: Use SQL_IDENTIFIER_COMPARISON parameter for schema identifier comparison rule
* #102: exasol_schema: Support clearing an existing raw_size_limit

## Dependency Updates

### `main`

* Updated dependency `pyexasol:2.2.2` to `2.3.0`
