# Security Considerations

This change expands the collection's database-administration surface. The main assets are Exasol credentials, authorization state, Ansible logs, and the integrity of automated schema, user, role, grant, and script execution workflows.

## Security Assessment

### Affects Authentication / Authorization

Yes.

The collection authenticates to Exasol with `login_*` parameters and performs authorization-sensitive operations through `exasol_user`, `exasol_role`, and `exasol_grants`.

Main threats:

* credential disclosure in task output or exceptions
* unintended privilege changes through incorrect idempotency or grant logic
* unintended privilege revocation or destructive drift during reconciliation
* use of over-privileged service accounts
* partial failures leaving authorization state inconsistent

Required controls:

* keep authentication failure handling secret-safe
* rely on Exasol authorization instead of local privilege bypass logic
* document the required least-privilege database permissions per module
* verify repeated runs do not add, revoke, or report privileges incorrectly
* make multi-step authorization changes fail predictably and visibly

Mitigations:

#### Sanitize Authentication and Authorization Failures
`dsn~sanitize-authentication-and-authorization-failures~1`

Reuse sanitized user-facing error handling for authentication and authorization failures.

Status: draft

Covers:
- `scn~operation-uses-authenticated-exasol-permissions~1`

Needs: impl, utest

#### Plan Authorization Lifecycle SQL From Metadata
`dsn~plan-authorization-lifecycle-sql-from-metadata~1`

Read the current Exasol state first, compare it with the requested user, role, or grant state, and generate only the SQL statements required to close that gap. This avoids blind create, alter, revoke, or drop operations and keeps repeated runs predictable.

Status: draft

Covers:
- `scn~repeated-runs-do-not-add-unrequested-authorization-changes~1`

Needs: impl, utest, itest

#### Delegate Authorization Decisions To Exasol
`dsn~delegate-authorization-decisions-to-exasol~1`

Keep authorization decisions delegated to Exasol instead of implementing local privilege logic.

Status: draft

Covers:
- `scn~operation-uses-authenticated-exasol-permissions~1`

Needs: impl

Applicable questions:

* How does the connector authenticate to the third-party system?
* Where are credentials stored?
* Can the connector operate with least-privilege permissions?
* How are privilege changes controlled and audited?

### Introduces or Modifies Sensitive Data Handling, Security-Relevant Processing, or Data Access Behavior

Yes.

The change processes passwords, usernames, role names, privileges, and possibly SQL scripts that may embed sensitive values.

Main threats:

* secrets leaking via logs, return values, tracebacks, or test failures
* SQL script content exposing confidential data in diagnostics
* unsafe handling of grant and user state leading to unauthorized access changes
* leakage through diffs, `changed` reporting, or debug output
* duplicate or replayed execution causing repeated destructive effects

Required controls:

* reuse shared secret-redaction helpers for parameters and exceptions
* avoid storing secrets locally in the collection
* keep module outputs minimal and free of raw credentials or script contents
* add tests for redaction and authorization-state correctness
* ensure replayed runs do not expose additional data or corrupt state

Mitigations:

#### Mark Secret-Bearing Parameters With `no_log=True`
`dsn~mark-secret-bearing-parameters-no-log~1`

Mark secret-bearing module parameters with `no_log=True`.

Status: draft

Covers:
- `scn~password-not-exposed-in-failure-output~1`

Needs: impl, utest

#### Redact Secrets From SQL And Surfaced Failures
`dsn~redact-secrets-from-sql-and-surfaced-failures~1`

Redact passwords and LDAP distinguished names from returned SQL and surfaced failures.

Status: draft

Covers:
- `scn~executed-queries-keep-object-names-but-redact-secrets~1`

Needs: impl, utest

#### Limit Results To Redacted Audit Fields
`dsn~limit-results-to-redacted-audit-fields~1`

Keep results limited to object identity, lifecycle state, and redacted statements.

Status: draft

Covers:
- `scn~executed-queries-keep-object-names-but-redact-secrets~1`

Needs: impl, utest

Applicable questions:

* Are secrets ever exposed in logs, monitoring systems, or configuration files?
* Is PII exposure in logs, monitoring, or error messages prevented?
* Is only the minimum required data shared or displayed?

### Impacts External Interfaces / APIs

Yes.

The change extends the module interface exposed to playbooks and increases the set of Exasol operations invoked through `pyexasol`.

Main threats:

* SQL injection or unsafe statement construction from module inputs
* identifier quoting or escaping bugs targeting the wrong object
* unsafe or ambiguous module inputs causing unintended SQL effects
* upstream error messages surfacing sensitive data
* insecure transport or certificate validation on outbound database connections

Required controls:

* keep module parameters explicit and validate mutually unsafe combinations
* construct SQL safely for identifiers, literals, and grant targets
* sanitize surfaced driver and database errors
* support only encrypted connections with correct certificate validation
* treat `exasol_script` as a trusted-operator interface, not a sandbox

Mitigations:

#### Normalize And Validate Identifiers Before SQL Generation
`dsn~normalize-and-validate-identifiers-before-sql-generation~1`

Normalize and validate identifiers before generating SQL.

Status: draft

Covers:
- `scn~repeated-runs-do-not-add-unrequested-authorization-changes~1`

Needs: impl, utest

#### Centralize Connection Parameter Mapping And Secret Sanitization
`dsn~centralize-connection-parameter-mapping-and-secret-sanitization~1`

Centralize connection-parameter mapping and secret sanitization in shared runtime helpers.

Status: draft

Covers:
- `scn~password-not-exposed-in-failure-output~1`
- `scn~executed-queries-keep-object-names-but-redact-secrets~1`

Needs: impl, utest

#### Encrypt Exasol Connections By Default
`dsn~encrypt-exasol-connections-by-default~1`

Open Exasol connections only over encrypted transport. Unencrypted connections are not supported. Certificate validation remains part of the supported connection path, so operators must provide trust material that keeps the connection encrypted and authenticated instead of downgrading transport security.

Status: draft

Covers:
- `scn~exasol-connections-use-encrypted-transport-by-default~1`

Needs: impl, utest

Applicable questions:

* Are API endpoints authenticated and authorized?
* Is input validation performed?
* Is output data sanitized before use or display?
* Is communication with the third-party system encrypted using TLS?

### Involves New Dependencies or Services

Yes.

The scope depends on `pyexasol` for SQL script execution support and on Ansible Galaxy packaging for a usable release artifact.

Main threats:

* supply-chain risk from new or changed package dependencies
* malicious, substituted, or compromised packages in the install path
* version drift between collection and required Python package
* release artifacts that install successfully but fail securely or insecurely at runtime

Required controls:

* keep dependencies minimal and versioned consistently
* validate that collection installation pulls the required Python package automatically
* review upstream `pyexasol` changes that affect authentication, transport, or script execution behavior
* verify release artifacts resolve dependencies from the intended source only

Mitigations:

#### Limit The Runtime Dependency Set
`dsn~limit-the-runtime-dependency-set~1`

Keep the runtime dependency set limited to `pyexasol` and `sqlglot`.

Status: draft

Needs: impl

#### Verify Packaging Installs Runtime Dependencies
`dsn~verify-packaging-installs-runtime-dependencies~1`

Verify packaging and installation through collection build and documentation checks.

Status: draft

Needs: impl

#### Review Dependency Changes During Release Verification
`dsn~review-dependency-changes-during-release-verification~1`

Review dependency changes as part of release verification for security-sensitive paths.

Status: draft

Needs: impl

Applicable questions:

* Does the integration affect compliance scope?
* What permissions are required by the connector in the third-party system?

### Affects Infrastructure or Configuration

Yes.

The change affects connection configuration, secret provisioning, CI or release automation, and the operational guidance for running the modules.

Main threats:

* credentials placed in plaintext inventory or CI configuration
* overly broad network reach from automation environments to Exasol
* insecure defaults or missing documentation for TLS and secret handling
* publication to the wrong or compromised Galaxy namespace

Required controls:

* keep Vault-based or equivalent secret management as the documented baseline
* document required network reachability and approved endpoints only
* avoid introducing new persistent secret stores, background services, or cluster-control paths
* verify release and test automation do not print secrets
* protect namespace ownership and release-publishing credentials

Mitigations:

#### Document Vault-Backed Secret Handling
`dsn~document-vault-backed-secret-handling~1`

Document Vault-backed secret handling as the normal operator workflow.

Status: draft

Needs: uman

#### Avoid Extra Control-Plane Services
`dsn~avoid-extra-control-plane-services~1`

Keep the collection as a direct client of Exasol. Do not add brokers, agents, background reconcilers, or long-lived helper services that cache credentials, queue privileged actions, or create another place where authorization and secret handling can drift from the database.

Status: draft

Needs: impl

#### Treat CI Redaction And Publishing-Credential Protection As Release Gates
`dsn~treat-ci-redaction-and-publishing-credential-protection-as-release-gates~1`

Do not ship a release if CI logs can expose secrets or if Galaxy publishing credentials are not adequately protected. Secret-safe logs and protected release credentials are mandatory conditions for publishing, not best-effort hygiene.

Status: draft

Needs: impl

Applicable questions:

* In which network zone will the connector run?
* Does the connector require direct access to sensitive systems or databases?
* Are firewall rules restricted to only necessary endpoints and ports?
* How are secrets rotated and revoked?

## Other Security Considerations

### Data At Rest, PII, and Local Persistence

The collection is not intended to become a secret store. Passwords, LDAP distinguished names, and connection credentials enter through Ansible variables and are forwarded to Exasol or `pyexasol` only for the lifetime of a task.

Required controls:

* keep secret values in Vault or equivalent external secret management
* do not persist credentials, raw SQL containing secrets, or cached identity data in collection-owned files
* keep returned data limited to object identifiers and redacted statements
* treat LDAP distinguished names as sensitive because they can expose directory structure and personal identifiers

Mitigations:

#### Avoid Local Secret Persistence
`dsn~avoid-local-secret-persistence~1`

Avoid local credential caches or collection-owned secret stores.

Status: draft

Needs: impl

#### Redact Sensitive Identifiers Unless Auditability Requires Them
`dsn~redact-sensitive-identifiers-unless-auditability-requires-them~1`

Redact sensitive identifiers from outputs where they are not needed for auditability.

Status: draft

Covers:
- `scn~executed-queries-keep-object-names-but-redact-secrets~1`

Needs: impl, utest

#### Keep Secret Handling Transient Within Task Execution
`dsn~keep-secret-handling-transient-within-task-execution~1`

Keep secret handling transient within the task lifecycle.

Status: draft

Needs: impl

### Accountability, Compliance, and Auditability

The collection should make security-relevant actions reviewable without disclosing secrets.

Required controls:

* keep `executed_queries` redacted but object-specific
* keep `changed` reporting aligned with emitted SQL so repeated runs are explainable
* preserve Exasol as the system of record for authentication, authorization, and server-side auditing
* treat secret leakage in task output, CI logs, or release logs as a release blocker

Mitigations:

#### Expose Normalized Object Names Without Secret Values
`dsn~expose-normalized-object-names-without-secret-values~1`

Expose normalized object names while hiding secret values.

Status: draft

Covers:
- `scn~executed-queries-keep-object-names-but-redact-secrets~1`

Needs: impl, utest

#### Derive `changed` From Planned SQL
`dsn~derive-changed-from-planned-sql~1`

Set `changed=true` only when the planner has determined that the collection must emit state-changing SQL. If the requested state already matches Exasol metadata and no SQL should run, report `changed=false` so operators can trust repeated-run behavior and audit output.

Status: draft

Covers:
- `scn~repeated-runs-do-not-add-unrequested-authorization-changes~1`

Needs: impl, utest, itest

#### Rely On Exasol For Authoritative Audit Trails
`dsn~rely-on-exasol-for-authoritative-audit-trails~1`

Rely on Exasol for authoritative audit trails of database-side actions.

Status: draft

Needs: impl

### Availability and Failure Handling

The administration surface is operational tooling, not a high-availability control plane. Availability therefore depends on Exasol reachability, valid credentials, and predictable failure behavior.

Required controls:

* fail fast on authentication, validation, and SQL-construction errors
* keep repeated runs safe after partial operational failures
* avoid background retries or local reconciliation loops that could amplify privilege changes
* keep check mode and idempotent planning available so operators can assess impact before applying changes

Mitigations:

#### Validate Inputs Before Risky SQL Paths
`dsn~validate-inputs-before-risky-sql-paths~1`

Reject invalid or conflicting module inputs before building or executing administrative SQL. This includes malformed identifiers, unsupported option combinations, and inputs that would make the target operation ambiguous or unsafe.

Status: draft

Needs: impl, utest

#### Keep Check-Mode Planning Deterministic And Side-Effect Free
`dsn~keep-check-mode-planning-deterministic-and-side-effect-free~1`

Make check mode run the same planning logic as normal execution, but stop before any state-changing SQL is sent. Given the same requested state and database metadata, check mode should produce the same decision and reporting without creating side effects.

Status: draft

Covers:
- `scn~repeated-runs-do-not-add-unrequested-authorization-changes~1`

Needs: impl, utest

#### Avoid Autonomous Retry Of Privileged Actions
`dsn~avoid-autonomous-retry-of-privileged-actions~1`

Avoid autonomous retry behavior that could repeat privileged actions.

Status: draft

Needs: impl

### Tier Segregation and Trusted-Operator Boundary

These modules are designed for trusted operators running in controlled automation environments. The collection does not sandbox SQL semantics or downgrade the authority of the authenticated Exasol account.

Required controls:

* run the collection only from tiers that are allowed to reach Exasol administration endpoints
* use separate low-privilege connection accounts for distinct automation roles where possible
* treat any future `exasol_grants`, `exasol_schema`, or `exasol_script` surface as subject to the same least-privilege, redaction, and repeated-run-safety rules

Mitigations:

#### Keep The Trust Boundary At The Authenticated Account And Operator Environment
`dsn~keep-the-trust-boundary-at-the-authenticated-account-and-operator-environment~1`

Treat the authenticated Exasol account and the automation environment running the playbook as the security boundary. The collection must not try to dilute, extend, or reinterpret that authority with its own privilege model.

Status: draft

Covers:
- `scn~operation-uses-authenticated-exasol-permissions~1`

Needs: impl

#### Require Least-Privilege Service Accounts For Automation Tiers
`dsn~require-least-privilege-service-accounts-for-automation-tiers~1`

Use separate service accounts for separate automation roles and grant each account only the Exasol privileges required for its job. A playbook that manages users should not automatically inherit the rights needed for broader scripting or schema administration if it does not need them.

Comment:

In practice, this is enforced mainly through documentation, operational guidance, and account provisioning outside the collection: the collection can describe the expected privilege boundaries, but it cannot reliably downgrade or constrain an already over-privileged Exasol account supplied by the operator.

Status: draft

Needs: uman

#### Apply The Security Model To Future Administrative Modules
`dsn~apply-the-security-model-to-future-administrative-modules~1`

Any future administrative module such as `exasol_grants`, `exasol_schema`, or `exasol_script` must follow the same rules established here: no local privilege bypass, encrypted transport only, secret-safe output, least-privilege operation, and repeatable planning based on observed database state.

Status: draft

Needs: impl

## Residual Risk

`exasol_script` intentionally enables arbitrary SQL execution for trusted operators. The security boundary is therefore operator authorization, secret-safe handling, and transport protection, not restriction of SQL semantics inside the module.

Trusted operators can still intentionally or accidentally execute destructive SQL. This risk is accepted as part of the module's purpose and must be managed operationally through least privilege, review of playbooks, and controlled execution environments.
