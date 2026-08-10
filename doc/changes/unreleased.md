# Unreleased

## Summary

* Improved end-user and embedded module documentation for all public modules.
* Implemented exasol_script module
* Made `login_schema` the canonical Exasol connection schema parameter; the
  deprecated `login_db` alias remains compatible.
* Minimized metadata privileges and schema-qualified Exasol system-table queries

## Documentation

* #107: Improved end-user and embedded module documentation for all public modules.

## Features

* #79: Implement exasol_script module
* #114: Make login_schema the canonical connection parameter

## Bug Fixes

* #94: Minimize metadata privileges and schema-qualify Exasol system-table queries
