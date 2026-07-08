# Security Considerations

This change expands the collection's database-administration surface. The main assets are Exasol credentials, authorization state, Ansible logs, and the integrity of automated schema, user, role, grant, and script execution workflows.

## Security Assessment

### Affects Authentication / Authorization

Yes.

The collection authenticates to Exasol with `login_*` parameters and performs authorization-sensitive operations through `exasol_user`, `exasol_role`, `exasol_query`, planned grant-management and schema-management workflows, and future trusted-operator modules such as `exasol_grants`, `exasol_schema`, and `exasol_script`.

#### Main Threats

##### Incorrect Idempotency Or Grant Logic Changes Privileges
`thrt~incorrect-idempotency-or-grant-logic-changes-privileges~1`

Incorrect planning or grant logic could add privileges or mutate authorization state that the operator did not request.

Status: draft

Needs: dsn

##### Reconciliation Drift Revokes Or Changes Authorization Unexpectedly
`thrt~reconciliation-drift-revokes-or-changes-authorization-unexpectedly~1`

Blind reconciliation or incomplete metadata checks could revoke privileges or otherwise drift authorization state away from the requested target.

Status: draft

Needs: dsn

##### Over-Privileged Service Accounts Expand Blast Radius
`thrt~over-privileged-service-accounts-expand-blast-radius~1`

Automation accounts with more Exasol privileges than necessary could turn routine playbook execution into broader security-impacting changes.

Status: draft

Needs: dsn

##### Partial Authorization Failures Leave Inconsistent State
`thrt~partial-authorization-failures-leave-inconsistent-state~1`

Multi-step authorization changes that fail midway could leave user, role, or grant state inconsistent with the requested outcome.

Status: draft

Needs: dsn

#### Required Controls

* keep authentication failure handling secret-safe
* rely on Exasol authorization instead of local privilege bypass logic
* document the required least-privilege database permissions per module
* verify repeated runs do not add, revoke, or report privileges incorrectly
* make multi-step authorization changes fail predictably and visibly

#### Mitigations

##### Surface Exasol Authorization Rejections Without Local Privilege Logic
`dsn~surface-exasol-authorization-rejections-without-local-privilege-logic~1`

When Exasol rejects an operation because the authenticated account lacks the required privilege, surface that rejection in sanitized form and stop. The collection must not retry with alternate credentials, emulate privilege checks locally, or add fallback behavior that could bypass or reinterpret Exasol authorization decisions.

Status: draft

Covers:
- `scn~operation-uses-authenticated-exasol-permissions~1`
- `thrt~upstream-errors-surface-sensitive-data~1`

Needs: impl, utest

##### Plan Authorization Lifecycle SQL From Metadata
`dsn~plan-authorization-lifecycle-sql-from-metadata~1`

Read the current Exasol state first, compare it with the requested user, role, or grant state, and generate only the SQL statements required to close that gap. This avoids blind create, alter, revoke, or drop operations and keeps repeated runs predictable across grant-management flows as well as user and role lifecycle changes.

Status: draft

Covers:
- `scn~repeated-runs-do-not-add-unrequested-authorization-changes~1`
- `thrt~incorrect-idempotency-or-grant-logic-changes-privileges~1`
- `thrt~reconciliation-drift-revokes-or-changes-authorization-unexpectedly~1`
- `thrt~partial-authorization-failures-leave-inconsistent-state~1`

Needs: impl, utest, itest

##### Delegate Authorization Decisions To Exasol
`dsn~delegate-authorization-decisions-to-exasol~1`

Keep authorization decisions delegated to Exasol instead of implementing local privilege logic.

Status: draft

Covers:
- `scn~operation-uses-authenticated-exasol-permissions~1`
- `thrt~over-privileged-service-accounts-expand-blast-radius~1`

Needs: impl

#### Applicable Questions

* How does the connector authenticate to the third-party system?
* Where are credentials stored?
* Can the connector operate with least-privilege permissions?
* How are privilege changes controlled and audited?

### Introduces or Modifies Sensitive Data Handling, Security-Relevant Processing, or Data Access Behavior

Yes.

The change processes passwords, usernames, role names, privileges, and possibly SQL scripts that may embed sensitive values.

#### Main Threats

##### Secrets Leak Through Logs, Results, Or Tracebacks
`thrt~secrets-leak-through-logs-results-or-tracebacks~1`

Secret values could be exposed through task output, returned fields, exception traces, or test diagnostics.

Status: draft

Needs: dsn

##### SQL Diagnostics Expose Confidential Script Content
`thrt~sql-diagnostics-expose-confidential-script-content~1`

Returned SQL or surfaced diagnostics could reveal confidential values embedded in administrative statements or operator-supplied scripts.

Status: draft

Needs: dsn

##### Unsafe Authorization-State Handling Changes Access
`thrt~unsafe-authorization-state-handling-changes-access~1`

Incorrect handling of user, role, or grant state could create unauthorized access changes or fail to preserve the intended security posture.

Status: draft

Needs: dsn

##### Diffs Or Status Reporting Leak Sensitive Details
`thrt~diffs-or-status-reporting-leak-sensitive-details~1`

Task diffs, `changed` reporting, or debug output could reveal sensitive information or mislead operators about security-relevant actions.

Status: draft

Needs: dsn

##### Replayed Execution Repeats Destructive Effects
`thrt~replayed-execution-repeats-destructive-effects~1`

Repeated or replayed execution could reapply destructive or privilege-changing actions beyond the operator's intent.

Status: draft

Needs: dsn

#### Required Controls

* reuse shared secret-redaction helpers for parameters and exceptions
* avoid storing secrets locally in the collection
* keep module outputs minimal and free of raw credentials or script contents
* add tests for redaction and authorization-state correctness
* ensure replayed runs do not expose additional data or corrupt state

#### Mitigations

##### Mark Secret-Bearing Parameters With `no_log=True`
`dsn~mark-secret-bearing-parameters-no-log~1`

Mark secret-bearing module parameters with `no_log=True`.

Status: draft

Covers:
- `scn~password-not-exposed-in-failure-output~1`
- `thrt~secrets-leak-through-logs-results-or-tracebacks~1`

Needs: impl, utest

##### Redact Secrets From SQL And Surfaced Failures
`dsn~redact-secrets-from-sql-and-surfaced-failures~1`

Redact passwords and LDAP distinguished names from returned SQL and surfaced failures.

Status: draft

Covers:
- `scn~executed-queries-keep-object-names-but-redact-secrets~1`
- `thrt~secrets-leak-through-logs-results-or-tracebacks~1`
- `thrt~sql-diagnostics-expose-confidential-script-content~1`

Needs: impl, utest

#### Applicable Questions

* Are secrets ever exposed in logs, monitoring systems, or configuration files?
* Is PII exposure in logs, monitoring, or error messages prevented?
* Is only the minimum required data shared or displayed?

### Impacts External Interfaces / APIs

Yes.

The change extends the module interface exposed to playbooks and increases the set of Exasol operations invoked through `pyexasol`.

#### Main Threats

##### Unsafe Inputs Enable SQL Injection Or Statement Abuse
`thrt~unsafe-inputs-enable-sql-injection-or-statement-abuse~1`

Module inputs could be used to inject unsafe SQL or otherwise influence statement construction beyond the intended administrative action.

Status: draft

Needs: dsn

##### Identifier Quoting Errors Target The Wrong Object
`thrt~identifier-quoting-errors-target-the-wrong-object~1`

Incorrect quoting, normalization, or escaping of identifiers could direct administrative SQL at the wrong Exasol object.

Status: draft

Needs: dsn

##### Ambiguous Inputs Trigger Unintended SQL Effects
`thrt~ambiguous-inputs-trigger-unintended-sql-effects~1`

Unsafe or conflicting parameter combinations could cause unintended SQL operations or unclear runtime behavior.

Status: draft

Needs: dsn

##### Upstream Errors Surface Sensitive Data
`thrt~upstream-errors-surface-sensitive-data~1`

Errors returned by drivers or Exasol could expose credentials, secrets, or confidential statement content when surfaced directly.

Status: draft

Needs: dsn

##### Outbound Connections Accept Insecure Transport Or Trust
`thrt~outbound-connections-accept-insecure-transport-or-trust~1`

Connection setup could permit unencrypted transport or weakened certificate validation, enabling interception or impersonation.

Status: draft

Needs: dsn

#### Required Controls

* keep module parameters explicit and validate mutually unsafe combinations
* construct SQL safely for identifiers, literals, and grant targets
* sanitize surfaced driver and database errors
* support only encrypted connections with correct certificate validation
* treat `exasol_query` and any future `exasol_script` surface as trusted-operator interfaces, not sandboxes

#### Mitigations

##### Normalize And Validate Identifiers Before SQL Generation
`dsn~normalize-and-validate-identifiers-before-sql-generation~1`

Normalize and validate identifiers before generating SQL for user, role, grant, and other administrative targets.

Status: draft

Covers:
- `scn~repeated-runs-do-not-add-unrequested-authorization-changes~1`
- `thrt~unsafe-inputs-enable-sql-injection-or-statement-abuse~1`
- `thrt~identifier-quoting-errors-target-the-wrong-object~1`

Needs: impl, utest

##### Centralize Connection Parameter Mapping And Secret Sanitization
`dsn~centralize-connection-parameter-mapping-and-secret-sanitization~1`

Centralize connection-parameter mapping and secret sanitization in shared runtime helpers.

Status: draft

Covers:
- `scn~password-not-exposed-in-failure-output~1`
- `scn~executed-queries-keep-object-names-but-redact-secrets~1`
- `thrt~upstream-errors-surface-sensitive-data~1`

Needs: impl, utest

##### Encrypt Exasol Connections By Default
`dsn~encrypt-exasol-connections-by-default~1`

Open Exasol connections only over encrypted transport. Unencrypted connections are not supported. Certificate validation is mandatory on every supported connection path, so operators must provide trust material that keeps the connection encrypted and authenticated instead of downgrading transport security.

Status: draft

Covers:
- `scn~exasol-connections-use-encrypted-transport-by-default~1`
- `thrt~outbound-connections-accept-insecure-transport-or-trust~1`

Needs: impl, utest

#### Applicable Questions

* Are API endpoints authenticated and authorized?
* Is input validation performed?
* Is output data sanitized before use or display?
* Is communication with the third-party system encrypted using TLS?

### Involves New Dependencies or Services

Yes.

The scope depends on `pyexasol` for SQL script execution support and on Ansible Galaxy packaging for a usable release artifact.

#### Main Threats

##### Dependency Changes Expand Supply-Chain Risk
`thrt~dependency-changes-expand-supply-chain-risk~1`

New or changed dependencies could introduce vulnerable or higher-risk code paths into authentication, transport, or SQL handling.

Status: draft

Needs: dsn

##### Compromised Packages Enter The Install Path
`thrt~compromised-packages-enter-the-install-path~1`

Substituted, malicious, or otherwise compromised packages could enter the installation path and undermine collection security.

Status: draft

Needs: dsn

##### Runtime Package Version Drift Breaks Security Expectations
`thrt~runtime-package-version-drift-breaks-security-expectations~1`

Version drift between the collection and its required runtime packages could silently change security-relevant behavior.

Status: draft

Needs: dsn

##### Release Artifacts Misinstall Runtime Dependencies
`thrt~release-artifacts-misinstall-runtime-dependencies~1`

Release artifacts could install successfully while omitting or mismatching runtime dependencies needed for secure behavior.

Status: draft

Needs: dsn

#### Required Controls

* keep dependencies minimal and versioned consistently
* validate that collection installation pulls the required Python package automatically
* review upstream `pyexasol` changes that affect authentication, transport, or script execution behavior
* verify release artifacts resolve dependencies from the intended source only

#### Mitigations

##### Limit The Runtime Dependency Set
`dsn~limit-the-runtime-dependency-set~1`

Keep the runtime dependency set limited to `pyexasol` and `sqlglot`.

Status: draft

Covers:
- `thrt~dependency-changes-expand-supply-chain-risk~1`

Needs: impl

##### Verify Packaging Installs Runtime Dependencies
`dsn~verify-packaging-installs-runtime-dependencies~1`

Verify packaging and installation through collection build and documentation checks.

Status: draft

Covers:
- `thrt~runtime-package-version-drift-breaks-security-expectations~1`
- `thrt~release-artifacts-misinstall-runtime-dependencies~1`

Needs: impl

##### Review Dependency Changes During Release Verification
`dsn~review-dependency-changes-during-release-verification~1`

Review dependency changes as part of release verification for security-sensitive paths.

Status: draft

Covers:
- `thrt~dependency-changes-expand-supply-chain-risk~1`
- `thrt~compromised-packages-enter-the-install-path~1`

Needs: impl

#### Applicable Questions

* Does the integration affect compliance scope?
* What permissions are required by the connector in the third-party system?

### Affects Infrastructure or Configuration

Yes.

The change affects connection configuration, secret provisioning, CI or release automation, and the operational guidance for running the modules.

#### Main Threats

##### Plaintext Credentials Leak Through Inventory Or CI
`thrt~plaintext-credentials-leak-through-inventory-or-ci~1`

Operators or automation could place credentials in plaintext inventory, CI configuration, or other unsafe inputs that later leak through logs or artifact metadata.

Status: draft

Needs: dsn

##### Overly Broad Network Reach Exposes Exasol Endpoints
`thrt~overly-broad-network-reach-exposes-exasol-endpoints~1`

Automation environments with unnecessary network reach could expose Exasol administration endpoints to more systems or operators than intended.

Status: draft

Needs: dsn

##### Missing Guidance Weakens TLS Or Secret Handling
`thrt~missing-guidance-weakens-tls-or-secret-handling~1`

Insecure defaults or incomplete operator guidance could normalize unsafe TLS trust configuration or weak secret-handling practices.

Status: draft

Needs: dsn

##### Compromised Publishing Paths Ship Untrusted Artifacts
`thrt~compromised-publishing-paths-ship-untrusted-artifacts~1`

Misconfigured or compromised Galaxy publishing paths could release untrusted artifacts or disclose publishing credentials.

Status: draft

Needs: dsn

#### Required Controls

* keep Vault-based or equivalent secret management as the documented baseline
* document required network reachability and approved endpoints only
* avoid introducing new persistent secret stores, background services, or cluster-control paths
* verify release and test automation do not print secrets
* protect namespace ownership and release-publishing credentials

#### Mitigations

##### Document Vault-Backed Secret Handling
`dsn~document-vault-backed-secret-handling~1`

Document Vault-backed secret handling as the normal operator workflow.

Status: draft

Covers:
- `thrt~plaintext-credentials-leak-through-inventory-or-ci~1`
- `thrt~missing-guidance-weakens-tls-or-secret-handling~1`

Needs: uman

##### Avoid Extra Control-Plane Services
`dsn~avoid-extra-control-plane-services~1`

Keep the collection as a direct client of Exasol. Do not add brokers, agents, background reconcilers, or long-lived helper services that cache credentials, queue privileged actions, or create another place where authorization and secret handling can drift from the database.

Status: draft

Covers:
- `thrt~overly-broad-network-reach-exposes-exasol-endpoints~1`

Needs: impl

##### Treat CI Redaction And Publishing-Credential Protection As Release Gates
`dsn~treat-ci-redaction-and-publishing-credential-protection-as-release-gates~1`

Do not ship a release if CI logs can expose secrets or if Galaxy publishing credentials are not adequately protected. Secret-safe logs and protected release credentials are mandatory conditions for publishing, not best-effort hygiene.

Status: draft

Covers:
- `thrt~plaintext-credentials-leak-through-inventory-or-ci~1`
- `thrt~compromised-publishing-paths-ship-untrusted-artifacts~1`

Needs: impl

#### Applicable Questions

* In which network zone will the connector run?
* Does the connector require direct access to sensitive systems or databases?
* Are firewall rules restricted to only necessary endpoints and ports?
* How are secrets rotated and revoked?

## Other Security Considerations

### Data At Rest, PII, and Local Persistence

The collection is not intended to become a secret store. Passwords, LDAP distinguished names, and connection credentials enter through Ansible variables and are forwarded to Exasol or `pyexasol` only for the lifetime of a task.

#### Main Threats

##### Persisted Credentials Or SQL Leak Secrets At Rest
`thrt~persisted-credentials-or-sql-leak-secrets-at-rest~1`

Locally persisted credentials, secret-bearing SQL, or cached identity data could expose secrets outside the task lifetime through files, caches, or artifacts.

Status: draft

Needs: dsn

##### Sensitive Identifiers Leak Directory Or Personal Data
`thrt~sensitive-identifiers-leak-directory-or-personal-data~1`

LDAP distinguished names or similar identifiers could reveal directory structure, personal data, or sensitive organizational details if exposed unnecessarily.

Status: draft

Needs: dsn

#### Required Controls

* keep secret values in Vault or equivalent external secret management
* do not persist credentials, raw SQL containing secrets, or cached identity data in collection-owned files
* keep returned data limited to object identifiers and redacted statements
* treat LDAP distinguished names as sensitive because they can expose directory structure and personal identifiers

#### Mitigations

##### Redact Sensitive Identifiers Unless Auditability Requires Them
`dsn~redact-sensitive-identifiers-unless-auditability-requires-them~1`

Redact sensitive identifiers from outputs where they are not needed for auditability.

Status: draft

Covers:
- `scn~executed-queries-keep-object-names-but-redact-secrets~1`
- `thrt~sql-diagnostics-expose-confidential-script-content~1`
- `thrt~sensitive-identifiers-leak-directory-or-personal-data~1`

Needs: impl, utest

##### Keep Secret Handling Transient Within Task Execution
`dsn~keep-secret-handling-transient-within-task-execution~1`

Keep secret handling transient within the task lifecycle, without local credential caches or collection-owned secret stores.

Status: draft

Covers:
- `thrt~secrets-leak-through-logs-results-or-tracebacks~1`
- `thrt~persisted-credentials-or-sql-leak-secrets-at-rest~1`

Needs: impl

### Accountability, Compliance, and Auditability

The collection should make security-relevant actions reviewable without disclosing secrets.

#### Main Threats

##### Audit Output Exposes Secrets Or Sensitive Details
`thrt~audit-output-exposes-secrets-or-sensitive-details~1`

Security-relevant output intended for auditability could reveal secrets or other sensitive details in logs, CI records, or operator-visible results.

Status: draft

Needs: dsn

##### Misleading Changed Reporting Obscures Security Impact
`thrt~misleading-changed-reporting-obscures-security-impact~1`

`changed` reporting that does not match emitted SQL could mislead operators about whether security-relevant state actually changed.

Status: draft

Needs: dsn

##### Local Reporting Competes With Authoritative Database Audit Trails
`thrt~local-reporting-competes-with-authoritative-database-audit-trails~1`

Collection-side reporting could be mistaken for the source of truth and weaken reliance on Exasol's authoritative audit trail for database actions.

Status: draft

Needs: dsn

#### Required Controls

* keep `executed_queries` redacted but object-specific
* keep `changed` reporting aligned with emitted SQL so repeated runs are explainable
* preserve Exasol as the system of record for authentication, authorization, and server-side auditing
* treat secret leakage in task output, CI logs, or release logs as a release blocker

#### Mitigations

##### Expose Normalized Object Names Without Secret Values
`dsn~expose-normalized-object-names-without-secret-values~1`

Expose normalized object names while hiding secret values.

Status: draft

Covers:
- `scn~executed-queries-keep-object-names-but-redact-secrets~1`
- `thrt~sql-diagnostics-expose-confidential-script-content~1`
- `thrt~diffs-or-status-reporting-leak-sensitive-details~1`
- `thrt~audit-output-exposes-secrets-or-sensitive-details~1`

Needs: impl, utest

##### Derive `changed` From Planned SQL
`dsn~derive-changed-from-planned-sql~1`

Set `changed=true` only when the planner has determined that the collection must emit state-changing SQL. If the requested state already matches Exasol metadata and no SQL should run, report `changed=false` so operators can trust repeated-run behavior and audit output.

Status: draft

Covers:
- `scn~repeated-runs-do-not-add-unrequested-authorization-changes~1`
- `thrt~unsafe-authorization-state-handling-changes-access~1`
- `thrt~diffs-or-status-reporting-leak-sensitive-details~1`
- `thrt~replayed-execution-repeats-destructive-effects~1`
- `thrt~misleading-changed-reporting-obscures-security-impact~1`

Needs: impl, utest, itest

##### Rely On Exasol For Authoritative Audit Trails
`dsn~rely-on-exasol-for-authoritative-audit-trails~1`

Rely on Exasol for authoritative audit trails of database-side actions.

Status: draft

Covers:
- `thrt~unsafe-authorization-state-handling-changes-access~1`
- `thrt~local-reporting-competes-with-authoritative-database-audit-trails~1`

Needs: impl

### Availability and Failure Handling

The administration surface is operational tooling, not a high-availability control plane. Availability therefore depends on Exasol reachability, valid credentials, and predictable failure behavior.

#### Main Threats

##### Invalid Inputs Or SQL Paths Cause Unsafe Failures
`thrt~invalid-inputs-or-sql-paths-cause-unsafe-failures~1`

Authentication, validation, or SQL-construction failures could trigger unsafe execution paths or make operational failures harder to recover from.

Status: draft

Needs: dsn

##### Partial Failures Leave State Unsafe For Repeated Runs
`thrt~partial-failures-leave-state-unsafe-for-repeated-runs~1`

Operational failures during multi-step changes could leave state in a condition that makes subsequent runs unsafe or misleading.

Status: draft

Needs: dsn

##### Autonomous Retries Repeat Privileged Actions
`thrt~autonomous-retries-repeat-privileged-actions~1`

Background retries or local retry loops could reissue privileged SQL and amplify unintended changes.

Status: draft

Needs: dsn

##### Check Mode Diverges From Real Execution
`thrt~check-mode-diverges-from-real-execution~1`

Check mode that does not follow the same planning logic as normal execution could mislead operators about pending security-relevant effects.

Status: draft

Needs: dsn

#### Required Controls

* fail fast on authentication, validation, and SQL-construction errors
* keep repeated runs safe after partial operational failures
* avoid background retries or local reconciliation loops that could amplify privilege changes
* keep check mode and idempotent planning available so operators can assess impact before applying changes

#### Mitigations

##### Validate Inputs Before Risky SQL Paths
`dsn~validate-inputs-before-risky-sql-paths~1`

Reject invalid or conflicting module inputs before building or executing administrative SQL. This includes malformed identifiers, unsupported option combinations, and inputs that would make the target operation ambiguous or unsafe.

Status: draft

Covers:
- `thrt~unsafe-inputs-enable-sql-injection-or-statement-abuse~1`
- `thrt~ambiguous-inputs-trigger-unintended-sql-effects~1`
- `thrt~invalid-inputs-or-sql-paths-cause-unsafe-failures~1`

Needs: impl, utest

##### Keep Check-Mode Planning Deterministic And Side-Effect Free
`dsn~keep-check-mode-planning-deterministic-and-side-effect-free~1`

Make check mode run the same planning logic as normal execution, but stop before any state-changing SQL is sent. Given the same requested state and database metadata, check mode should produce the same decision and reporting without creating side effects.

Status: draft

Covers:
- `scn~repeated-runs-do-not-add-unrequested-authorization-changes~1`
- `thrt~partial-authorization-failures-leave-inconsistent-state~1`
- `thrt~replayed-execution-repeats-destructive-effects~1`
- `thrt~partial-failures-leave-state-unsafe-for-repeated-runs~1`
- `thrt~check-mode-diverges-from-real-execution~1`

Needs: impl, utest

##### Avoid Autonomous Retry Of Privileged Actions
`dsn~avoid-autonomous-retry-of-privileged-actions~1`

Avoid autonomous retry behavior that could repeat privileged actions.

Status: draft

Covers:
- `thrt~replayed-execution-repeats-destructive-effects~1`
- `thrt~autonomous-retries-repeat-privileged-actions~1`

Needs: impl

### Tier Segregation and Trusted-Operator Boundary

These modules are designed for trusted operators running in controlled automation environments. In particular, `exasol_query` already executes operator-supplied SQL directly against Exasol, and any future `exasol_script` surface would extend the same trust model. The collection does not sandbox SQL semantics or downgrade the authority of the authenticated Exasol account.

#### Main Threats

##### Untrusted Tiers Reach Administrative Interfaces
`thrt~untrusted-tiers-reach-administrative-interfaces~1`

Running the collection from uncontrolled or overly broad automation tiers could expose Exasol administrative interfaces to untrusted environments.

Status: draft

Needs: dsn

##### Shared Or Over-Privileged Accounts Cross Role Boundaries
`thrt~shared-or-over-privileged-accounts-cross-role-boundaries~1`

Using shared or overly privileged service accounts across automation roles could blur security boundaries and expand the impact of mistakes or misuse.

Status: draft

Needs: dsn

##### Direct SQL Surfaces Are Mistaken For Sandboxed Interfaces
`thrt~direct-sql-surfaces-are-mistaken-for-sandboxed-interfaces~1`

Operators could incorrectly assume that direct SQL interfaces such as `exasol_query` or future script modules constrain SQL semantics or reduce account authority.

Status: draft

Needs: dsn

##### Declarative Modules Drift From The Trusted-Operator Security Model
`thrt~declarative-modules-drift-from-the-trusted-operator-security-model~1`

Future administrative modules could diverge from the established least-privilege, redaction, transport, and repeatable-planning model.

Status: draft

Needs: dsn

#### Required Controls

* run the collection only from tiers that are allowed to reach Exasol administration endpoints
* use separate low-privilege connection accounts for distinct automation roles where possible
* treat `exasol_query` and any future `exasol_grants`, `exasol_schema`, or `exasol_script` surface as subject to the same least-privilege, redaction, and transport-protection rules
* require repeatable state-reconciliation planning only for modules that reconcile declarative authorization or schema state from observed metadata

#### Mitigations

##### Keep The Trust Boundary At The Authenticated Account And Operator Environment
`dsn~keep-the-trust-boundary-at-the-authenticated-account-and-operator-environment~1`

Treat the authenticated Exasol account and the automation environment running the playbook as the security boundary. The collection must not try to dilute, extend, or reinterpret that authority with its own privilege model.

Status: draft

Covers:
- `scn~operation-uses-authenticated-exasol-permissions~1`
- `thrt~over-privileged-service-accounts-expand-blast-radius~1`
- `thrt~untrusted-tiers-reach-administrative-interfaces~1`

Needs: impl

##### Require Least-Privilege Service Accounts For Automation Tiers
`dsn~require-least-privilege-service-accounts-for-automation-tiers~1`

Use separate service accounts for separate automation roles and grant each account only the Exasol privileges required for its job. A playbook that manages users should not automatically inherit the rights needed for broader scripting or schema administration if it does not need them.

Comment:

In practice, this is enforced mainly through documentation, operational guidance, and account provisioning outside the collection: the collection can describe the expected privilege boundaries, but it cannot reliably downgrade or constrain an already over-privileged Exasol account supplied by the operator.

Status: draft

Covers:
- `thrt~over-privileged-service-accounts-expand-blast-radius~1`
- `thrt~overly-broad-network-reach-exposes-exasol-endpoints~1`
- `thrt~shared-or-over-privileged-accounts-cross-role-boundaries~1`

Needs: uman

##### Apply The Security Model To Future Administrative Modules
`dsn~apply-the-security-model-to-future-administrative-modules~1`

Current `exasol_query` and any future administrative module such as `exasol_grants`, `exasol_schema`, or `exasol_script` must follow the same rules established here where they apply: no local privilege bypass, encrypted transport only, secret-safe output, and least-privilege operation. Modules that reconcile declarative authorization or schema state from observed metadata, such as `exasol_grants` or `exasol_schema`, must also use repeatable planning based on observed database state. Direct SQL surfaces such as `exasol_query` remain trusted-operator interfaces and are explicitly exempt from that state-reconciliation rule.

Status: draft

Covers:
- `thrt~missing-guidance-weakens-tls-or-secret-handling~1`
- `thrt~direct-sql-surfaces-are-mistaken-for-sandboxed-interfaces~1`
- `thrt~declarative-modules-drift-from-the-trusted-operator-security-model~1`

Needs: impl

## Residual Risk

`exasol_query` intentionally enables operator-supplied SQL execution today, and any future `exasol_script` module would do the same for a broader trusted-operator surface. The security boundary is therefore operator authorization, secret-safe handling, and transport protection, not restriction of SQL semantics inside the module.

Trusted operators can still intentionally or accidentally execute destructive SQL. This risk is accepted as part of the module's purpose and must be managed operationally through least privilege, review of playbooks, and controlled execution environments.
