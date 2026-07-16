Feature: exasol-schema Ansible module runtime specification
  Manage Exasol database schemas directly through the exasol_schema Python
  runtime helpers.

  @exasol-schema-create-missing-schema
  Scenario: Create a missing schema
    Given an Exasol database is reachable at localhost
    And the schema does not exist
    When the schema runtime runs with state present
    Then changed is true
    And schema equals the generated schema name
    And exists is true
    And executed_queries equals a single CREATE SCHEMA statement
    And the schema exists in EXA_SCHEMAS

  @exasol-schema-leave-existing-schema-unchanged
  Scenario: Leave an existing schema unchanged
    Given an Exasol database is reachable at localhost
    And the schema already exists
    When the schema runtime runs with state present
    Then changed is false
    And schema equals the generated schema name
    And exists is true
    And executed_queries equals []
    And the schema still exists in EXA_SCHEMAS

  @exasol-schema-drop-existing-schema
  Scenario: Drop an existing schema
    Given an Exasol database is reachable at localhost
    And the schema already exists
    When the schema runtime runs with state absent
    Then changed is true
    And schema equals the generated schema name
    And exists is false
    And executed_queries equals a single DROP SCHEMA statement
    And the schema no longer exists in EXA_SCHEMAS

  @exasol-schema-check-mode-predicts-create-without-writing
  Scenario: Check mode predicts create without writing
    Given an Exasol database is reachable at localhost
    And the schema does not exist
    When the schema runtime runs in check mode with state present
    Then changed is true
    And exists is true
    And executed_queries equals a single CREATE SCHEMA statement
    And the schema still does not exist in EXA_SCHEMAS

  @exasol-schema-check-mode-predicts-no-action-when-schema-exists
  Scenario: Check mode predicts no action when schema exists
    Given an Exasol database is reachable at localhost
    And the schema already exists
    When the schema runtime runs in check mode with state present
    Then changed is false
    And exists is true
    And executed_queries equals []
    And the schema still exists in EXA_SCHEMAS

  @exasol-schema-check-mode-predicts-drop-without-writing
  Scenario: Check mode predicts drop without writing
    Given an Exasol database is reachable at localhost
    And the schema already exists
    When the schema runtime runs in check mode with state absent and cascade
    Then changed is true
    And exists is false
    And executed_queries equals a single DROP SCHEMA CASCADE statement
    And the schema still exists in EXA_SCHEMAS
