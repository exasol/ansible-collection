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

  @exasol-schema-create-with-owner
  Scenario: Create a schema and assign its owner
    Given an Exasol database is reachable at localhost
    And the schema does not exist
    And the requested owner exists
    When a playbook runs exasol_schema with state present and owner
    Then changed is true
    And CREATE SCHEMA is followed by ALTER SCHEMA CHANGE OWNER
    And EXA_SCHEMAS reports the requested owner

  @exasol-schema-change-owner
  Scenario: Change the owner of an existing schema through a playbook
    Given an Exasol database is reachable at localhost
    And the schema exists with a different owner
    And the requested owner exists
    When a playbook runs exasol_schema with state present and owner
    Then changed is true
    And executed_queries equals a single ALTER SCHEMA CHANGE OWNER statement
    And EXA_SCHEMAS reports the requested owner

  @exasol-schema-owner-idempotent
  Scenario: Keep an identical schema owner unchanged
    Given an Exasol database is reachable at localhost
    And the schema exists with the requested owner
    When a playbook runs exasol_schema with state present and owner
    Then changed is false
    And executed_queries equals []
    And EXA_SCHEMAS still reports the requested owner

  @exasol-schema-set-comment
  Scenario: Set a schema comment through a playbook
    Given an Exasol database is reachable at localhost
    And the schema exists without a comment
    When a playbook runs exasol_schema with a comment
    Then changed is true
    And executed_queries contains a COMMENT ON SCHEMA statement
    And EXA_SCHEMAS reports the requested comment

  @exasol-schema-rename
  Scenario: Rename a schema through a playbook
    Given an Exasol database is reachable at localhost
    And the source schema exists
    And the target schema does not exist
    When a playbook runs exasol_schema with new_name
    Then changed is true
    And executed_queries contains a RENAME SCHEMA statement
    And only the target schema exists

  @exasol-schema-raw-size-limit-check-mode
  Scenario: Predict a raw size limit change through a playbook
    Given an Exasol database is reachable at localhost
    And the schema exists with a raw size limit
    When a playbook runs exasol_schema in check mode with a different raw_size_limit
    Then changed is true
    And executed_queries contains an ALTER SCHEMA SET RAW_SIZE_LIMIT statement
    And EXA_ALL_OBJECT_SIZES still reports the original limit
