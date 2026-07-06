# Security Considerations

This change expands the collection's database-administration surface. The main assets are Exasol credentials, authorization state, Ansible logs, and the integrity of automated schema, user, role, grant, and script execution workflows.

## Affects Authentication / Authorization

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

Applicable questions:

* How does the connector authenticate to the third-party system?
* Where are credentials stored?
* Can the connector operate with least-privilege permissions?
* How are privilege changes controlled and audited?

## Introduces or Modifies Sensitive Data Handling, Security-Relevant Processing, or Data Access Behavior

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

Applicable questions:

* Are secrets ever exposed in logs, monitoring systems, or configuration files?
* Is PII exposure in logs, monitoring, or error messages prevented?
* Is only the minimum required data shared or displayed?

## Impacts External Interfaces / APIs

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
* continue using TLS-capable connection handling with correct certificate validation
* treat `exasol_script` as a trusted-operator interface, not a sandbox

Applicable questions:

* Are API endpoints authenticated and authorized?
* Is input validation performed?
* Is output data sanitized before use or display?
* Is communication with the third-party system encrypted using TLS?

## Involves New Dependencies or Services

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

Applicable questions:

* Does the integration affect compliance scope?
* What permissions are required by the connector in the third-party system?

## Affects Infrastructure or Configuration

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

Applicable questions:

* In which network zone will the connector run?
* Does the connector require direct access to sensitive systems or databases?
* Are firewall rules restricted to only necessary endpoints and ports?
* How are secrets rotated and revoked?

## Residual Risk

`exasol_script` intentionally enables arbitrary SQL execution for trusted operators. The security boundary is therefore operator authorization, secret-safe handling, and transport protection, not restriction of SQL semantics inside the module.

Trusted operators can still intentionally or accidentally execute destructive SQL. This risk is accepted as part of the module's purpose and must be managed operationally through least privilege, review of playbooks, and controlled execution environments.
