# Impacts External Interfaces / APIs

Yes.

The change extends the module interface exposed to playbooks and increases the set of Exasol operations invoked through `pyexasol`.

## Main Threats

### Unsafe Inputs Enable SQL Injection Or Statement Abuse
`thrt~unsafe-inputs-enable-sql-injection-or-statement-abuse~1`

Module inputs could be used to inject unsafe SQL or otherwise influence statement construction beyond the intended administrative action.

Status: draft

Needs: dsn

### Identifier Quoting Errors Target The Wrong Object
`thrt~identifier-quoting-errors-target-the-wrong-object~1`

Incorrect quoting, normalization, or escaping of identifiers could direct administrative SQL at the wrong Exasol object.

Status: draft

Needs: dsn

### Ambiguous Inputs Trigger Unintended SQL Effects
`thrt~ambiguous-inputs-trigger-unintended-sql-effects~1`

Unsafe or conflicting parameter combinations could cause unintended SQL operations or unclear runtime behavior.

Status: draft

Needs: dsn

### Upstream Errors Surface Sensitive Data
`thrt~upstream-errors-surface-sensitive-data~1`

Errors returned by drivers or Exasol could expose credentials, secrets, or confidential statement content when surfaced directly.

Status: draft

Needs: dsn

### Outbound Connections Accept Insecure Transport Or Trust
`thrt~outbound-connections-accept-insecure-transport-or-trust~1`

Connection setup could permit unencrypted transport or weakened certificate validation, enabling interception or impersonation.

Status: draft

Needs: dsn

## Required Controls

* keep module parameters explicit and validate mutually unsafe combinations
* construct SQL safely for identifiers, literals, and grant targets
* sanitize surfaced driver and database errors
* support only encrypted connections with explicit trust anchors
* treat `exasol_query` and `exasol_script` as trusted-operator interfaces, not sandboxes

## Mitigations

### Normalize And Validate Identifiers Before SQL Generation
`dsn~normalize-and-validate-identifiers-before-sql-generation~1`

Normalize and validate identifiers before generating SQL for user, role, grant, and other administrative targets.

Status: draft

Covers:
- `scn~repeated-runs-do-not-add-unrequested-authorization-changes~1`
- `thrt~unsafe-inputs-enable-sql-injection-or-statement-abuse~1`
- `thrt~identifier-quoting-errors-target-the-wrong-object~1`

Needs: impl, utest

### Centralize Connection Parameter Mapping And Secret Sanitization
`dsn~centralize-connection-parameter-mapping-and-secret-sanitization~1`

Centralize connection-parameter mapping and secret sanitization in shared runtime helpers.

Status: draft

Covers:
- `scn~password-not-exposed-in-failure-output~1`
- `scn~executed-queries-keep-object-names-but-redact-secrets~1`
- `thrt~upstream-errors-surface-sensitive-data~1`

Needs: impl, utest

### Encrypt Exasol Connections By Default
`dsn~encrypt-exasol-connections-by-default~2`

Open Exasol connections only over encrypted transport. Unencrypted connections
are not supported. Certificate validation remains enabled by default. When
operators disable CA validation, they must provide a certificate fingerprint so
the connection still uses an explicit trust anchor instead of downgrading to a
fully untrusted TLS session.

Status: draft

Covers:
- `scn~exasol-connections-use-encrypted-transport-by-default~2`
- `scn~fingerprint-pinning-keeps-trust-explicit~1`
- `scn~untrusted-tls-overrides-are-rejected~1`
- `thrt~outbound-connections-accept-insecure-transport-or-trust~1`

Needs: impl, utest

## Applicable Questions

* Is input validation performed?
* Is output data sanitized before use or display?
* Is communication with the third-party system encrypted using TLS?
