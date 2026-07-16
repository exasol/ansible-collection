Feature: exasol-schema specification
  Manage Exasol database schemas from Ansible playbooks.

  @exasol-schema-create-missing-schema
  Scenario: Create missing schema
    Given an Exasol database is reachable at localhost
    And schema "SALES" does not exist in EXA_SCHEMAS
    When exasol_schema runs with:
      | name  | state   |
      | SALES | present |
    Then changed is true
    And schema equals "SALES"
    And exists is true
    And executed_queries equals:
      | sql                   |
      | CREATE SCHEMA "SALES" |
    And schema "SALES" exists in EXA_SCHEMAS

  @exasol-schema-preserves-exact-identifier
  Scenario: Create schema with exact identifier semantics
    Given an Exasol database is reachable at localhost
    And exact-identifier schema "Sales+/=Schema" does not exist in EXA_SCHEMAS
    When exasol_schema runs with:
      | name             | state   |
      | "Sales+/=Schema" | present |
    Then changed is true
    And schema equals "\"Sales+/=Schema\""
    And exists is true
    And executed_queries equals:
      | sql                                  |
      | CREATE SCHEMA "Sales+/=Schema"       |
    And schema "Sales+/=Schema" exists in EXA_SCHEMAS

  @exasol-schema-apply-unchanged
  Scenario: Applying identical schema state results in no changes
    Given an Exasol database is reachable at localhost
    And schema "SALES" already exists in EXA_SCHEMAS
    When exasol_schema runs again with:
      | name  | state   |
      | SALES | present |
    Then changed is false
    And exists is true
    And executed_queries equals []
    And schema "SALES" exists in EXA_SCHEMAS

  @exasol-schema-apply-unchanged-with-different-case-spelling
  Scenario: Applying same schema with different case spelling stays idempotent
    Given an Exasol database is reachable at localhost
    And exact-identifier schema "Sales+/=Schema" already exists in EXA_SCHEMAS
    When exasol_schema runs again with:
      | name             | state   |
      | "sales+/=schema" | present |
    Then changed is false
    And schema equals "\"sales+/=schema\""
    And exists is true
    And executed_queries equals []
    And EXA_SCHEMAS contains one row where SCHEMA_NAME equals "Sales+/=Schema"

  @exasol-schema-check-mode-create
  Scenario: Check mode predicts create
    Given an Exasol database is reachable at localhost
    And schema "SALES" does not exist in EXA_SCHEMAS
    When exasol_schema runs in check mode with:
      | name  | state   |
      | SALES | present |
    Then changed is true
    And exists is true
    And executed_queries equals:
      | sql                   |
      | CREATE SCHEMA "SALES" |
    And schema "SALES" does not exist in EXA_SCHEMAS

  @exasol-schema-check-mode-drop
  Scenario: Check mode predicts drop
    Given an Exasol database is reachable at localhost
    And schema "SALES" exists in EXA_SCHEMAS
    When exasol_schema runs in check mode with:
      | name  | state  |
      | SALES | absent |
    Then changed is true
    And exists is false
    And executed_queries equals:
      | sql                 |
      | DROP SCHEMA "SALES" |
    And schema "SALES" still exists in EXA_SCHEMAS

  @exasol-schema-check-mode-drop-cascade
  Scenario: Check mode predicts cascade drop
    Given an Exasol database is reachable at localhost
    And schema "SALES" exists in EXA_SCHEMAS
    And schema "SALES" contains database objects
    When exasol_schema runs in check mode with:
      | name  | state  | cascade |
      | SALES | absent | true    |
    Then changed is true
    And exists is false
    And executed_queries equals:
      | sql                         |
      | DROP SCHEMA "SALES" CASCADE |
    And schema "SALES" still exists in EXA_SCHEMAS

  @exasol-schema-drop-existing-schema
  Scenario: Drop existing empty schema
    Given an Exasol database is reachable at localhost
    And schema "SALES" exists in EXA_SCHEMAS
    And schema "SALES" is empty
    When exasol_schema runs with:
      | name  | state  |
      | SALES | absent |
    Then changed is true
    And exists is false
    And executed_queries equals:
      | sql                 |
      | DROP SCHEMA "SALES" |
    And schema "SALES" no longer exists in EXA_SCHEMAS

  @exasol-schema-drop-existing-schema-cascade
  Scenario: Drop existing non-empty schema using cascade
    Given an Exasol database is reachable at localhost
    And schema "SALES" exists in EXA_SCHEMAS
    And schema "SALES" contains table "SALES_TAB"
    When exasol_schema runs with:
      | name  | state  | cascade |
      | SALES | absent | true    |
    Then changed is true
    And exists is false
    And executed_queries equals:
      | sql                         |
      | DROP SCHEMA "SALES" CASCADE |
    And schema "SALES" no longer exists in EXA_SCHEMAS

  @exasol-schema-drop-missing-schema
  Scenario: Drop missing schema
    Given an Exasol database is reachable at localhost
    And schema "SALES" does not exist in EXA_SCHEMAS
    When exasol_schema runs with:
      | name  | state  |
      | SALES | absent |
    Then changed is false
    And exists is false
    And executed_queries equals []
