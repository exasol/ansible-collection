Feature: Security requirements
  Verify security properties shared by the Exasol Ansible modules.

@id:scn~operation-uses-authenticated-exasol-permissions~1
# Covers: req~respect-exasol-authorization~1
# Needs: dsn
Scenario: Operations use authenticated Exasol permissions
    Given an authenticated account lacks an administrative privilege
    When an operator runs an administration task
    Then Exasol rejects the operation without local privilege elevation

@id:scn~password-not-exposed-in-failure-output~1
# Covers: req~protect-secret-values~1
# Needs: dsn
Scenario: Passwords are not exposed in failure output
    Given a login password contains a secret value
    When authentication fails
    Then the failure output redacts the secret value

@id:scn~metadata-access-matches-requested-lifecycle-operation~1
# Covers: req~minimize-exasol-metadata-privileges~1
# Needs: dsn
Scenario: Lifecycle metadata uses least-privileged catalog views
    Given a lifecycle operation requires existence metadata
    When user or role management evaluates the current state
    Then it uses only the least-privileged applicable catalog view

@id:scn~repeated-runs-do-not-add-unrequested-authorization-changes~1
# Covers: req~keep-authorization-changes-predictable~1
# Needs: dsn
Scenario: Repeated authorization runs are unchanged
    Given the authorization state already matches the request
    When the operator repeats the administration task
    Then no additional authorization-changing SQL is emitted

@id:scn~role-membership-grants-are-reconciled~1
# Covers: req~keep-authorization-changes-predictable~1
# Needs: dsn
Scenario: Role memberships are reconciled
    Given an operator requests a role membership state
    When exasol_grants evaluates the existing membership
    Then it plans only the required grant or revoke statements

@id:scn~exact-principal-identifiers-are-preserved~1
# Covers: req~preserve-exact-exasol-principal-identifiers~1
# Needs: dsn
Scenario: Exact principal identifiers are preserved
    Given a user or role name uses a delimited Exasol identifier
    When the collection validates it and generates SQL
    Then the SQL targets that exact identifier

@id:scn~exasol-connections-use-encrypted-transport-by-default~2
# Covers: req~protect-exasol-transport~2
# Needs: dsn
Scenario: Connections use encrypted transport by default
    Given an operator uses shared connection options
    When the collection opens a connection
    Then encryption and certificate validation are enabled

@id:scn~fingerprint-pinning-keeps-trust-explicit~1
# Covers: req~protect-exasol-transport~2
# Needs: dsn
Scenario: Fingerprint pinning is explicit trust
    Given CA validation is disabled with a certificate fingerprint
    When the collection opens a connection
    Then it uses the fingerprint as the trust anchor

@id:scn~untrusted-tls-overrides-are-rejected~1
# Covers: req~protect-exasol-transport~2
# Needs: dsn
Scenario: Untrusted TLS overrides are rejected
    Given CA validation is disabled without a fingerprint
    When the collection validates the connection options
    Then it rejects the configuration before connecting

@id:scn~executed-queries-keep-object-names-but-redact-secrets~1
# Covers: req~keep-audit-output-secret-safe~1
# Needs: dsn
Scenario: Audit output preserves names but redacts secrets
    Given a task has secret-bearing parameters
    When the module reports planned SQL or an error
    Then object names remain visible and secrets are redacted
