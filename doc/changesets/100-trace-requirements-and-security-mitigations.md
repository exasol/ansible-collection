---
orphan: true
---

# GH-100 Trace Requirements And Security Mitigations Into Code And Tests

## Goal

Trace the requirements and implemented security mitigations through runtime
code, unit tests, integration tests, and operator documentation. The trace
must represent actual behavior: add coverage only where code or an executable
test already implements the corresponding item, and leave unimplemented items
uncovered until their implementation is added.

## Scope

In scope:

* run OpenFastTrace without filtering artifact types, so `impl`, `utest`, and
  `itest` coverage is evaluated
* establish a readable mapping from security requirement scenarios to their
  system requirement IDs and corresponding integration tests
* add `Covers:` tags to existing code, unit tests, integration tests, and user
  documentation when they demonstrably fulfill a traced item
* add the missing implementation and test coverage identified in the inventory
  below
* make requirement tracing and the scenario-to-test contract enforce the new
  traceability rules

Out of scope:

* adding coverage tags merely to make the trace report green
* changing OpenFastTrace IDs whose semantics have not changed
* claiming that a future module, external deployment control, or release
  process is implemented when it is not

## Design References

* [System Requirements](../system_requirements.md)
* [Design](../design_index.md)
* [Quality Requirements](../design/quality_requirements.md)
* [Security Considerations](../design/security_considerations.md)
* [Authentication and Authorization](../design/security/affects_authentication_authorization.md)
* [Sensitive Data Handling](../design/security/introduces_or_modifies_sensitive_data_handling_security_relevant_processing_or_data_access_behavior.md)
* [External Interfaces and APIs](../design/security/impacts_external_interfaces_apis.md)

## Strategy

Use the security design items as the trace targets. For each target, first
identify the narrow runtime helper or module that realizes it, then the unit
test(s) that prove the decision point, and finally an existing backend
integration test where the behavior is observable. A single source location
may cover several design items only when it actually implements all of them.

Extend the current Gherkin contract rather than creating duplicate prose:
security scenarios must carry both a stable `scenario_id` and a
`requirement_id`, and the contract test must verify the bidirectional mapping
between scenario, requirement, and integration test. The source requirement
IDs remain the OpenFastTrace items in `doc/system_requirements.md`.

## Coverage Inventory

### Already Implemented: Add Trace Coverage

The following items have corresponding runtime behavior today and should gain
only evidence-based coverage tags after their existing tests are reviewed:

* Connection security and parameter safety: encrypted connections, CA
  validation by default, fingerprint-pinning validation, shared connection
  parameter mapping, and secret sanitization
  (`dsn~encrypt-exasol-connections-by-default~2`,
  `dsn~encrypted-transport-by-default~2`,
  `dsn~centralize-connection-parameter-mapping-and-secret-sanitization~1`).
* Secret-safe user administration: `no_log` argument specifications, password
  and LDAP-DN redaction in planned SQL and errors, and audit-safe object
  reporting (`dsn~mark-secret-bearing-parameters-no-log~1`,
  `dsn~redact-secrets-from-sql-and-surfaced-failures~1`,
  `dsn~redact-sensitive-identifiers-unless-auditability-requires-them~1`,
  `dsn~expose-normalized-object-names-without-secret-values~1`).
* Identifier validation and exact user/role identifier handling
  (`dsn~normalize-and-validate-identifiers-before-sql-generation~1`,
  `dsn~exact-principal-identifier-handling~1`,
  `dsn~exact-principal-identifier-lifecycle~1`).
* User, role, grant, and schema reconciliation: metadata-driven planning,
  `changed` derived from planned statements, and deterministic side-effect-free
  check mode (`dsn~authorization-state-reconciliation~1`,
  `dsn~plan-authorization-lifecycle-sql-from-metadata~1`,
  `dsn~derive-changed-from-planned-sql~1`,
  `dsn~keep-check-mode-planning-deterministic-and-side-effect-free~1`,
  `dsn~intrinsic-schema-property-reconciliation~1`,
  `dsn~explicit-schema-drop-cascade~1`).
* Explicit user-password behavior and read-only info retrieval
  (`dsn~password-update-semantics~1`,
  `dsn~exasol-info-read-only-metadata-retrieval~1`).
* Transient connection-secret handling: `connect_to_exasol()` supplies the
  credentials only to `pyexasol.connect()` and closes the connection when the
  task exits; `test_connect_to_exasol_closes_connection_after_with_block`
  exercises that lifecycle. The runtime helper has the corresponding `impl`
  tag
  (`dsn~keep-secret-handling-transient-within-task-execution~1`).
* No autonomous query retry: `execute_queries()` sends each planned statement
  once, and `test_execute_queries_returns_design_doc_result_shape` asserts the
  exact calls made to the connection. The runtime function has the
  corresponding `impl` tag
  (`dsn~avoid-autonomous-retry-of-privileged-actions~1`).
* Minimal runtime dependencies: the production dependency list in
  `pyproject.toml` contains only `pyexasol` and `sqlglot`, with an `impl` tag
  on that metadata (`dsn~limit-the-runtime-dependency-set~1`).
* Runtime-package installation from a Galaxy collection is already covered:
  `test_galaxy_installed_module_uses_configured_python_runtime` has both
  `impl` and `itest` tags for
  `dsn~verify-packaging-installs-runtime-dependencies~1`; it is not a
  remaining coverage item.
* Existing operator guidance already represented as `uman` coverage: Vault
  handling, TLS guidance, trusted direct-SQL boundary, and password-update
  limitations. Preserve and extend it only where the documentation explicitly
  covers the target.

### Still Missing: Implementation And/Or Test Evidence

Do not add `Covers:` tags for these design items until the named work is
complete. The implementation should create a focused test before adding the
`impl`, `utest`, or `itest` evidence.

* Authorization-denial and partial-failure behavior: prove sanitized Exasol
  authorization rejection and define/test what remains safe and visible when a
  multi-statement authorization operation fails
  (`dsn~surface-exasol-authorization-rejections-without-local-privilege-logic~1`,
  the partial-failure portions of
  `dsn~plan-authorization-lifecycle-sql-from-metadata~1` and
  `dsn~keep-check-mode-planning-deterministic-and-side-effect-free~1`).
* Trust-boundary controls that are currently documented but lack executable
  evidence: no local authorization/privilege model, no autonomous retries, no
  credential persistence, and no additional control-plane service
  (`dsn~delegate-authorization-decisions-to-exasol~1`,
  `dsn~keep-the-trust-boundary-at-the-authenticated-account-and-operator-environment~1`,
  `dsn~avoid-autonomous-retry-of-privileged-actions~1`,
  `dsn~keep-secret-handling-transient-within-task-execution~1`,
  `dsn~avoid-extra-control-plane-services~1`).
  Decide during implementation whether each is best covered by a narrow
  structural/contract test, a packaging assertion, or a `uman` item; do not
  invent a runtime tag for an operational constraint.
* Audit-trail semantics: document and test the boundary between the redacted
  collection result and Exasol as the authoritative audit record
  (`dsn~make-privilege-changes-reviewable-through-planned-sql-and-exasol-audit-trails~1`,
  `dsn~rely-on-exasol-for-authoritative-audit-trails~1`).
* Release and supply-chain controls: dependency-set policy, installation of
  the runtime package from a built collection, dependency-change review,
  CI-log redaction/publishing-credential protection, and explicit compliance
  review. The runtime dependency-set and collection-installation evidence is
  listed above; the remaining controls need a release-process implementation
  or explicit test rather than a Python runtime tag
  (`dsn~review-dependency-changes-during-release-verification~1`,
  `dsn~treat-ci-redaction-and-publishing-credential-protection-as-release-gates~1`,
  `dsn~require-explicit-compliance-review-for-security-relevant-integrations~1`).
  Some are release-process controls and must be implemented in CI/release
  workflow or documentation, not falsely represented by Python runtime tags.
* Future-module policy (`dsn~apply-the-security-model-to-future-administrative-modules~1`):
  trace only the current `exasol_query`, `exasol_grants`, and `exasol_schema`
  behavior that exists. Keep any `exasol_script` or other future-module claims
  uncovered until those modules exist.

### Remaining Unfiltered OpenFastTrace Failures

The following is the complete list of design items that fail the unfiltered
trace because their required implementation or executable-test evidence is
missing. The feature, requirement, and scenario entries also printed by the
trace are parent relationships; they do not themselves need an `impl`,
`utest`, or `itest` tag.

* `dsn~apply-the-security-model-to-future-administrative-modules~1` — `impl`
* `dsn~avoid-extra-control-plane-services~1` — `impl`
* `dsn~delegate-authorization-decisions-to-exasol~1` — `impl`
* `dsn~exasol-authorization-enforcement~1` — `impl`
* `dsn~keep-secret-rotation-and-revocation-outside-the-collection~1` — `impl`
  (the required `uman` evidence already exists)
* `dsn~keep-the-trust-boundary-at-the-authenticated-account-and-operator-environment~1`
  — `impl`
* `dsn~make-privilege-changes-reviewable-through-planned-sql-and-exasol-audit-trails~1`
  — `impl`, `utest`, `itest`
* `dsn~rely-on-exasol-for-authoritative-audit-trails~1` — `impl`
* `dsn~require-explicit-compliance-review-for-security-relevant-integrations~1`
  — `impl`
* `dsn~review-dependency-changes-during-release-verification~1` — `impl`
* `dsn~surface-exasol-authorization-rejections-without-local-privilege-logic~1`
  — `impl`, `utest`
* `dsn~treat-ci-redaction-and-publishing-credential-protection-as-release-gates~1`
  — `impl`

### Proposed Implementation Slices

* `dsn~apply-the-security-model-to-future-administrative-modules~1` — extract
  the shared connection, error-normalization, and secret-safe result boundary
  used by `exasol_query`, `exasol_grants`, and `exasol_schema` into an explicit
  administrative-module contract. Add a narrow contract test for those current
  modules, and use the same contract as the required entry criterion for any
  future administrative module; then place the `impl` tag on that shared
  contract.
* `dsn~avoid-extra-control-plane-services~1` — make the direct-client topology
  explicit in the runtime/package manifest: modules may open a task-scoped
  Exasol connection but may not register a broker, worker, queue, daemon, or
  persistent store. Place the `impl` tag on that topology declaration and add
  a packaging/structural test only if the design item is expanded to require
  `utest` evidence.
* `dsn~delegate-authorization-decisions-to-exasol~1` — centralize all
  database connection and statement execution through the shared Exasol
  helper, without a local privilege-evaluation branch. Tag that helper as the
  implementation after reviewing every administrative runtime entry point.
* `dsn~exasol-authorization-enforcement~1` — retire this overlapping legacy
  design item by forwarding it to
  `dsn~delegate-authorization-decisions-to-exasol~1`, or keep it and tag the
  same shared execution boundary after verifying it cannot elevate or replace
  the authenticated account.
* `dsn~keep-secret-rotation-and-revocation-outside-the-collection~1` — add an
  explicit task-scoped credential lifecycle statement to the shared connection
  helper, ensure every connection is closed at task completion, and tag that
  helper. Retain the existing operator guidance as the `uman` evidence.
* `dsn~keep-the-trust-boundary-at-the-authenticated-account-and-operator-environment~1`
  — implement the boundary as a shared runtime policy: accept only the
  operator-supplied connection account, make no account-selection or
  privilege-escalation decisions locally, and tag the common connection
  boundary.
* `dsn~make-privilege-changes-reviewable-through-planned-sql-and-exasol-audit-trails~1`
  — make user, role, and grant results return the sanitized statement plan and
  `changed` decision from one shared result builder. Add unit tests for the
  plan/result pair and an Exasol integration test that verifies the reported
  statements match the state transition; tag the builder and those tests.
* `dsn~rely-on-exasol-for-authoritative-audit-trails~1` — add a result/document
  contract that identifies the collection output as a redacted execution
  summary and directs operators to Exasol auditing as the authoritative record.
  Tag that contract rather than claiming that the collection provides an audit
  store.
* `dsn~require-explicit-compliance-review-for-security-relevant-integrations~1`
  — add a pull-request/release workflow gate requiring an explicit compliance
  decision when integration, release, or sensitive-data paths change. Tag the
  workflow step as `impl`.
* `dsn~review-dependency-changes-during-release-verification~1` — add a CI
  rule that detects changes to dependency metadata/lockfiles and requires a
  reviewed dependency-security checklist before release. Tag that release
  workflow gate as `impl`.
* `dsn~surface-exasol-authorization-rejections-without-local-privilege-logic~1`
  — preserve sanitized Exasol authorization errors in the shared error wrapper
  without retry or credential fallback. Add a unit test for an authorization
  denial and an integration test that runs a restricted account against an
  administrative operation; tag the wrapper and unit test.
* `dsn~treat-ci-redaction-and-publishing-credential-protection-as-release-gates~1`
  — make publishing depend on secrets scanning and required security checks,
  pass the Galaxy token only as a GitHub Actions secret, and keep checkout
  credentials disabled. Tag the publish workflow gate as `impl`.

## Task List

- [x] Create and checkout a new Git branch `feature/100-trace-requirements-and-security-mitigations`

### Requirements And Design

- [ ] Add `specs/security_requirements.feature` (or extend the existing
  feature layout) with readable Gherkin scenarios for implemented security
  behavior, each annotated with both `scenario_id` and `requirement_id`.
- [ ] Add scenarios only for requirements with a current implementation; list
  unimplemented mitigations in this changeset rather than assigning them a
  passing scenario.
- [ ] Stop and ask user for a review of the system requirements and security
  scenario mapping.
- [x] Update the security design only if the evidence review finds a semantic
  mismatch; preserve IDs where the documented behavior is accurate.
- [ ] Stop and ask user for a review of the design changes.

### Implementation

- [ ] Preserve the existing unfiltered `requirements:trace` invocation in
  `noxfile.py`; do not reintroduce `--wanted-artifact-types` filtering.
- [x] Add source-level OpenFastTrace coverage tags beside the smallest existing runtime
  functions/classes that implement each item in the “Already Implemented”
  inventory.
- [x] Add OpenFastTrace coverage tags to existing unit and integration tests only after
  confirming each assertion proves the tagged behavior.
- [x] Add the remaining evidence-based tags identified above for transient
  secret handling, single-attempt query execution, and the runtime dependency
  set; keep the process, audit, authorization-denial, and future-module items
  below untagged until their complete behavior is implemented and tested.
- [ ] Extend `test_acceptance_scenario_contract.py` and pytest marker
  registration to require and validate `requirement_id` together with
  `scenario_id`, including both directions of the scenario/test mapping.
- [ ] Implement the remaining items in the “Still Missing” inventory in
  separately reviewable slices, adding their test coverage and tags only in
  the slice that supplies the behavior.

### Verification

- [ ] Run the scenario/requirement contract test and its focused unit tests.
- [x] Run focused unit tests for connection security, redaction, identifier
  handling, planning, check mode, and changed reporting.
- [ ] Run the affected backend integration tests with `.env` loaded when it is
  present; use escalation if the local Exasol service is blocked by the
  sandbox.
- [ ] Run `poetry run nox -s requirements:trace` and resolve only genuine
  implementation/test gaps, leaving documented future or process work
  explicitly uncovered.
- [ ] Run `poetry run nox -s collection:sanity` and
  `poetry run nox -s collection:doc`.
- [x] Run SonarQube secrets scanning on changed specification, source, test,
  and workflow files.

## Version and Changelog Update

- [ ] Decide whether the implemented slices introduce user-visible behavior;
  update version and changelog only if they do.
