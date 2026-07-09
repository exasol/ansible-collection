# Building Block View

This chapter describes the static decomposition of the collection runtime and the responsibilities relevant to user and role administration.

## Component Overview

The collection is split into:

* Ansible module entry points in `plugins/modules/` that declare the public contract and delegate runtime work.
* Shared runtime helpers in `exasol/ansible_modules/` that validate parameters, quote identifiers, sanitize errors, connect through `pyexasol`, and plan SQL statements.
* Acceptance and unit tests that validate SQL planning, idempotency, and backend behavior.

## Component Design Items

### Exact Principal Identifier Handling
`dsn~exact-principal-identifier-handling~1`

The shared runtime identifier helper is responsible for parsing exact user and role identifiers from either raw values or delimited SQL identifier syntax and for rendering those values back into escaped delimited SQL identifiers. The `exasol_user` and `exasol_role` runtimes reuse that helper for metadata probes and lifecycle SQL planning so both modules preserve the same identifier semantics.

Status: draft

Covers:
- `scn~exact-principal-identifiers-are-preserved~1`

Needs: impl

## Open Issues

* Extend the same exact-identifier handling model to future modules that manage additional Exasol object types.
