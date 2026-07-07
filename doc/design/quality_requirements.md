# Quality Requirements

This chapter documents architecture-relevant quality requirements and technical quality goals.

User-facing acceptance scenarios are defined in [System Requirements](../system_requirements.md).

## Requirement Quality

Use this OFT hierarchy unless the project already defines a different one:

1. `feat`: top-level feature
2. `req`: user requirement
3. `scn`: Given-When-Then acceptance scenario
4. `constr`: architecture constraint
5. `dsn`: design requirement covering scenarios and constraints
6. `impl`: implementation
7. `utest`: unit test
8. `itest`: integration test

Runtime design requirements `dsn` should cover one scenario or constraint at a time. Use OFT forwarding notation if a design layer adds no new information.

## Code Quality

Collection modules must validate inputs before generating SQL, reuse shared connection and redaction helpers, and keep secret-bearing parameters under `no_log=True`.

Python code targets 3.11+, uses Black line length 88, isort's Black profile, Ruff for selected lint rules, Pylint, and mypy with explicit package bases.

Security-sensitive behavior such as connection setup, SQL rendering, and error sanitization belongs in reusable runtime helpers so user and role modules do not drift.

## Test Quality

Use `pytest` for unit and integration coverage.

Unit tests should exercise SQL planning, input validation, error sanitization, check mode, and `changed` / `exists` reporting with fake connections.

Acceptance tests in `test/integration/acceptance/` should prove backend behavior for repeated-run safety, secret redaction, and security-relevant state transitions against a real Exasol backend.

## Dependency Policy

Keep runtime dependencies minimal. The current runtime package depends on `pyexasol` and `sqlglot`; collection modules require `exasol-ansible-modules` in the Ansible execution environment.

New dependencies must be justified by implementation need, versioned in project metadata, and reviewed for security impact on authentication, transport, or SQL handling paths.

## Static Analysis and Security Gates

Required local verification consists of:

* `nox -s requirements:trace` for OFT consistency
* `nox -s collection:sanity` for Ansible sanity checks
* `nox -s collection:doc` for module documentation validity

Secret leakage in module output, tests, or release automation is a release blocker. SonarQube secrets scanning are part of the expected static-analysis and security review flow.

## Testability and Coverage

Coverage should focus on security-relevant decision points rather than line totals.

Required verification for this administration surface includes:

* unit tests for redaction, transport-option mapping, identifier validation, and idempotent SQL planning
* backend acceptance tests for repeated-run safety, password-update behavior, and role/user lifecycle transitions
* manual or automated confirmation that release artifacts install the runtime dependency set needed by collection modules

## Open Issues

* The repo does not yet trace `impl`, `utest`, or `itest` items into code and tests.
