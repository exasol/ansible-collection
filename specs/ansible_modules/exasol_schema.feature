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

  @exasol-schema-create-with-owner
  Scenario: Create a schema with an owner
    Given an Exasol database is reachable at localhost
    And the schema does not exist
    And the requested owner exists
    When the schema runtime runs with state present and owner
    Then changed is true
    And executed_queries equals CREATE SCHEMA followed by ALTER SCHEMA CHANGE OWNER
    And EXA_SCHEMAS reports the requested owner

  @exasol-schema-change-owner
  Scenario: Change the owner of an existing schema
    Given an Exasol database is reachable at localhost
    And the schema exists with a different owner
    And the requested owner exists
    When the schema runtime runs with state present and owner
    Then changed is true
    And executed_queries equals a single ALTER SCHEMA CHANGE OWNER statement
    And EXA_SCHEMAS reports the requested owner

  @exasol-schema-owner-idempotent
  Scenario: Leave an identical schema owner unchanged
    Given an Exasol database is reachable at localhost
    And the schema exists with the requested owner
    When the schema runtime runs with state present and owner
    Then changed is false
    And executed_queries equals []
    And EXA_SCHEMAS still reports the requested owner

  @exasol-schema-owner-check-mode
  Scenario: Check mode predicts an owner change without writing
    Given an Exasol database is reachable at localhost
    And the schema exists with a different owner
    And the requested owner exists
    When the schema runtime runs in check mode with state present and owner
    Then changed is true
    And executed_queries equals a single ALTER SCHEMA CHANGE OWNER statement
    And EXA_SCHEMAS still reports the original owner

  @exasol-schema-set-comment
  Scenario: Set a schema comment
    Given an Exasol database is reachable at localhost
    And the schema exists without a comment
    When the schema runtime runs with state present and comment
    Then changed is true
    And executed_queries equals a single COMMENT ON SCHEMA statement
    And EXA_SCHEMAS reports the requested comment

  @exasol-schema-clear-comment
  Scenario: Clear a schema comment
    Given an Exasol database is reachable at localhost
    And the schema exists with a comment
    When the schema runtime runs with state present and an empty comment
    Then changed is true
    And executed_queries equals COMMENT ON SCHEMA IS NULL
    And EXA_SCHEMAS reports no comment

  @exasol-schema-comment-idempotent
  Scenario: Leave an identical schema comment unchanged
    Given an Exasol database is reachable at localhost
    And the schema exists with the requested comment
    When the schema runtime runs with state present and comment
    Then changed is false
    And executed_queries equals []
    And EXA_SCHEMAS still reports the requested comment

  @exasol-schema-comment-check-mode
  Scenario: Check mode predicts a comment change without writing
    Given an Exasol database is reachable at localhost
    And the schema exists with a different comment
    When the schema runtime runs in check mode with state present and comment
    Then changed is true
    And executed_queries equals a single COMMENT ON SCHEMA statement
    And EXA_SCHEMAS still reports the original comment

  @exasol-schema-rename
  Scenario: Rename an existing schema
    Given an Exasol database is reachable at localhost
    And the source schema exists
    And the target schema does not exist
    When the schema runtime runs with state present and new_name
    Then changed is true
    And executed_queries equals a single RENAME SCHEMA statement
    And only the target schema exists in EXA_SCHEMAS

  @exasol-schema-rename-idempotent
  Scenario: Leave an already renamed schema unchanged
    Given an Exasol database is reachable at localhost
    And the source schema does not exist
    And the target schema exists
    When the schema runtime runs with state present and new_name
    Then changed is false
    And executed_queries equals []
    And only the target schema exists in EXA_SCHEMAS

  @exasol-schema-rename-check-mode
  Scenario: Check mode predicts a rename without writing
    Given an Exasol database is reachable at localhost
    And the source schema exists
    And the target schema does not exist
    When the schema runtime runs in check mode with state present and new_name
    Then changed is true
    And executed_queries equals a single RENAME SCHEMA statement
    And only the source schema exists in EXA_SCHEMAS

  @exasol-schema-set-raw-size-limit
  Scenario: Set a schema raw size limit
    Given an Exasol database is reachable at localhost
    And the schema exists without a raw size limit
    When the schema runtime runs with state present and raw_size_limit
    Then changed is true
    And executed_queries equals a single ALTER SCHEMA SET RAW_SIZE_LIMIT statement
    And EXA_ALL_OBJECT_SIZES reports the requested raw size limit

  @exasol-schema-change-raw-size-limit
  Scenario: Change a schema raw size limit
    Given an Exasol database is reachable at localhost
    And the schema exists with a different raw size limit
    When the schema runtime runs with state present and raw_size_limit
    Then changed is true
    And executed_queries equals a single ALTER SCHEMA SET RAW_SIZE_LIMIT statement
    And EXA_ALL_OBJECT_SIZES reports the requested raw size limit

  @exasol-schema-raw-size-limit-idempotent
  Scenario: Leave an identical schema raw size limit unchanged
    Given an Exasol database is reachable at localhost
    And the schema exists with the requested raw size limit
    When the schema runtime runs with state present and raw_size_limit
    Then changed is false
    And executed_queries equals []
    And EXA_ALL_OBJECT_SIZES still reports the requested raw size limit

  @exasol-schema-raw-size-limit-check-mode
  Scenario: Check mode predicts a raw size limit change without writing
    Given an Exasol database is reachable at localhost
    And the schema exists with a different raw size limit
    When the schema runtime runs in check mode with state present and raw_size_limit
    Then changed is true
    And executed_queries equals a single ALTER SCHEMA SET RAW_SIZE_LIMIT statement
    And EXA_ALL_OBJECT_SIZES still reports the original raw size limit

  @exasol-schema-drop-non-empty-without-cascade
  Scenario: Refuse to drop a non-empty schema without cascade
    Given an Exasol database is reachable at localhost
    And the schema contains a table
    When the schema runtime runs with state absent without cascade
    Then the operation fails with an error mentioning CASCADE
    And the schema and table still exist
