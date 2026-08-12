Feature: exasol-schema specification
  Manage Exasol database schemas from Ansible playbooks.

  Background:
    Given an Exasol database is reachable at localhost

  @exasol-schema-create-missing-schema
  Scenario: Create missing schema
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
    And schema "SALES" already exists in EXA_SCHEMAS
    When exasol_schema runs again with:
      | name  | state   |
      | SALES | present |
    Then changed is false
    And exists is true
    And executed_queries equals []
    And schema "SALES" exists in EXA_SCHEMAS

  @exasol-schema-creates-case-distinct-schema-by-default
  Scenario: Applying a case-distinct schema creates it by default
    Given SQL_IDENTIFIER_COMPARISON is CASE SENSITIVE
    And exact-identifier schema "Sales+/=Schema" already exists in EXA_SCHEMAS
    When exasol_schema runs with:
      | name             | state   |
      | "sales+/=schema" | present |
    Then changed is true
    And schema equals "\"sales+/=schema\""
    And exists is true
    And executed_queries equals:
      | sql                            |
      | CREATE SCHEMA "sales+/=schema" |
    And EXA_SCHEMAS contains one row where SCHEMA_NAME equals "Sales+/=Schema"
    And EXA_SCHEMAS contains one row where SCHEMA_NAME equals "sales+/=schema"

  @exasol-schema-check-mode-create
  Scenario: Check mode predicts create
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

  @exasol-schema-drop-non-empty-without-cascade
  Scenario: Refuse to drop a non-empty schema without cascade
    And schema "SALES" exists in EXA_SCHEMAS
    And schema "SALES" contains table "SALES_TAB"
    And exasol_schema does not check whether the schema contains objects before issuing the drop
    When exasol_schema runs with:
      | name  | state  |
      | SALES | absent |
    Then the module fails with an error mentioning CASCADE
    And schema "SALES" still exists in EXA_SCHEMAS

  @exasol-schema-drop-missing-schema
  Scenario: Drop missing schema
    And schema "SALES" does not exist in EXA_SCHEMAS
    When exasol_schema runs with:
      | name  | state  |
      | SALES | absent |
    Then changed is false
    And exists is false
    And executed_queries equals []

  @exasol-schema-create-with-owner
  Scenario: Create a schema and assign its owner
    And the schema does not exist
    And the requested owner exists
    When a playbook runs exasol_schema with state present and owner
    Then changed is true
    And CREATE SCHEMA is followed by ALTER SCHEMA CHANGE OWNER
    And EXA_SCHEMAS reports the requested owner

  @exasol-schema-change-owner
  Scenario: Change the owner of an existing schema through a playbook
    And the schema exists with a different owner
    And the requested owner exists
    When a playbook runs exasol_schema with state present and owner
    Then changed is true
    And executed_queries equals a single ALTER SCHEMA CHANGE OWNER statement
    And EXA_SCHEMAS reports the requested owner

  @exasol-schema-owner-idempotent
  Scenario: Keep an identical schema owner unchanged
    And the schema exists with the requested owner
    When a playbook runs exasol_schema with state present and owner
    Then changed is false
    And executed_queries equals []
    And EXA_SCHEMAS still reports the requested owner

  @exasol-schema-set-comment
  Scenario: Set a schema comment through a playbook
    And the schema exists without a comment
    When a playbook runs exasol_schema with a comment
    Then changed is true
    And executed_queries contains a COMMENT ON SCHEMA statement
    And EXA_SCHEMAS reports the requested comment

  @exasol-schema-rename
  Scenario: Rename a schema through a playbook
    And the source schema exists
    And the target schema does not exist
    When a playbook runs exasol_schema with new_name
    Then changed is true
    And executed_queries contains a RENAME SCHEMA statement
    And only the target schema exists

  @exasol-schema-rename-idempotent
  Scenario: Leave an already renamed schema unchanged through a playbook
    And the source schema does not exist
    And the target schema already exists
    When a playbook runs exasol_schema with new_name again
    Then changed is false
    And executed_queries equals []
    And only the target schema exists

  @exasol-schema-raw-size-limit-check-mode
  Scenario: Predict a raw size limit change through a playbook
    And the schema exists with a raw size limit
    When a playbook runs exasol_schema in check mode with a different raw_size_limit
    Then changed is true
    And executed_queries contains an ALTER SCHEMA SET RAW_SIZE_LIMIT statement
    And EXA_ALL_OBJECT_SIZES still reports the original limit

  @exasol-schema-clear-raw-size-limit-playbook
  Scenario: Clear a raw size limit through a playbook
    And the schema exists with a raw size limit
    When a playbook runs exasol_schema with raw_size_limit -1
    Then changed is true
    And executed_queries contains an ALTER SCHEMA SET RAW_SIZE_LIMIT NULL statement
    And EXA_ALL_OBJECT_SIZES reports no limit
