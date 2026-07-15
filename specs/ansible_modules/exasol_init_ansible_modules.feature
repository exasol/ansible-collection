Feature: exasol-init Ansible module runtime specification
  Initialize an Exasol environment directly through the exasol_init Python
  runtime helpers, in the dependency order discovered in
  specs/diagrams/exasol_init_process_diagram.md and
  specs/glossary/exasol_init_glossary.md.

  @exasol-init-create-full-environment
  Scenario: Create a full environment from empty state
    Given an Exasol database is reachable at localhost
    And no requested role, user, or schema exists
    When the init runtime runs with roles, users, role_grants, schemas, grants, and scripts
    Then changed is true
    And executed_queries orders roles before users before role_grants before schemas before grants before scripts
    And every requested role, user, and schema exists in its Exasol catalog view
    And the requested role grant exists in EXA_DBA_ROLE_GRANTS
    And the requested schema privilege grant exists in EXA_DBA_OBJ_PRIVS

  @exasol-init-leave-existing-environment-unchanged
  Scenario: Leave an already-initialized environment unchanged
    Given an Exasol database is reachable at localhost
    And the requested role, user, role grant, schema, and schema grant already exist
    When the init runtime runs again with the same roles, users, role_grants, schemas, and grants
    Then changed is false
    And executed_queries equals []

  @exasol-init-check-mode-predicts-plan-without-writing
  Scenario: Check mode predicts the full plan without writing
    Given an Exasol database is reachable at localhost
    And no requested role, user, or schema exists
    When the init runtime runs in check mode with roles, users, role_grants, schemas, grants, and scripts
    Then changed is true
    And executed_queries contains one statement per requested command
    And no requested role, user, or schema exists afterward

  @exasol-init-drop-environment-with-cascade
  Scenario: Drop an existing environment in reverse dependency order
    Given an Exasol database is reachable at localhost
    And the requested role, user, role grant, schema, and schema grant already exist
    When the init runtime runs with state absent and cascade for the role, user, and schema
    Then changed is true
    And executed_queries orders the schema grant revoke before the role grant revoke before the schema drop before the user drop before the role drop
    And none of the requested role, user, or schema exist afterward

  @exasol-init-execute-scripts-after-grants
  Scenario: Execute init scripts only after grants are applied
    Given an Exasol database is reachable at localhost
    And the requested role and schema do not exist
    When the init runtime runs with a role, a schema, a schema grant, and one init script
    Then changed is true
    And the script statement is the last entry in executed_queries
    And the schema exists before the script statement runs
