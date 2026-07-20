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
  review (`dsn~limit-the-runtime-dependency-set~1`,
  `dsn~verify-packaging-installs-runtime-dependencies~1`,
  `dsn~review-dependency-changes-during-release-verification~1`,
  `dsn~treat-ci-redaction-and-publishing-credential-protection-as-release-gates~1`,
  `dsn~require-explicit-compliance-review-for-security-relevant-integrations~1`).
  Some are release-process controls and must be implemented in CI/release
  workflow or documentation, not falsely represented by Python runtime tags.
* Future-module policy (`dsn~apply-the-security-model-to-future-administrative-modules~1`):
  trace only the current `exasol_query`, `exasol_grants`, and `exasol_schema`
  behavior that exists. Keep any `exasol_script` or other future-module claims
  uncovered until those modules exist.

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
- [ ] Update the security design only if the evidence review finds a semantic
  mismatch; preserve IDs where the documented behavior is accurate.
- [ ] Stop and ask user for a review of the design changes.

### Implementation

- [ ] Preserve the existing unfiltered `requirements:trace` invocation in
  `noxfile.py`; do not reintroduce `--wanted-artifact-types` filtering.
- [ ] Add source-level `Covers:` tags beside the smallest existing runtime
  functions/classes that implement each item in the “Already Implemented”
  inventory.
- [ ] Add `Covers:` tags to existing unit and integration tests only after
  confirming each assertion proves the tagged behavior.
- [ ] Extend `test_acceptance_scenario_contract.py` and pytest marker
  registration to require and validate `requirement_id` together with
  `scenario_id`, including both directions of the scenario/test mapping.
- [ ] Implement the remaining items in the “Still Missing” inventory in
  separately reviewable slices, adding their test coverage and tags only in
  the slice that supplies the behavior.

### Verification

- [ ] Run the scenario/requirement contract test and its focused unit tests.
- [ ] Run focused unit tests for connection security, redaction, identifier
  handling, planning, check mode, and changed reporting.
- [ ] Run the affected backend integration tests with `.env` loaded when it is
  present; use escalation if the local Exasol service is blocked by the
  sandbox.
- [ ] Run `poetry run nox -s requirements:trace` and resolve only genuine
  implementation/test gaps, leaving documented future or process work
  explicitly uncovered.
- [ ] Run `poetry run nox -s collection:sanity` and
  `poetry run nox -s collection:doc`.
- [ ] Run SonarQube secrets scanning on changed specification, source, test,
  and workflow files.

## Version and Changelog Update

- [ ] Decide whether the implemented slices introduce user-visible behavior;
  update version and changelog only if they do.
