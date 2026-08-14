Feature: exasol-schema Ansible module runtime specification
  Manage Exasol database schemas directly through the exasol_schema Python
  runtime helpers.

  Background:
    Given an Exasol database is reachable at localhost

@id:scn~ansible-modules.exasol-schema-create-missing-schema~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Create a missing schema
    And the schema does not exist
    When the schema runtime runs with state present
    Then changed is true
    And schema equals the generated schema name
    And exists is true
    And executed_queries equals a single CREATE SCHEMA statement
    And the schema exists in EXA_SCHEMAS

@id:scn~ansible-modules.exasol-schema-leave-existing-schema-unchanged~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Leave an existing schema unchanged
    And the schema already exists
    When the schema runtime runs with state present
    Then changed is false
    And schema equals the generated schema name
    And exists is true
    And executed_queries equals []
    And the schema still exists in EXA_SCHEMAS

@id:scn~ansible-modules.exasol-schema-identifiers-follow-session-comparison~1
# Covers: req~exasol-schema-module~1
# Needs: dsn, itest
Scenario: Create a case-distinct schema in a case-sensitive session
    Given SQL_IDENTIFIER_COMPARISON is CASE SENSITIVE
    And exact-identifier schema "Sales+/=Schema" already exists
    When the schema runtime runs with name "sales+/=schema" and state present
    Then changed is true
    And executed_queries equals a single CREATE SCHEMA statement
    And both exact-identifier schemas exist in EXA_SCHEMAS

@id:scn~ansible-modules.exasol-schema-drop-existing-schema~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Drop an existing schema
    And the schema already exists
    When the schema runtime runs with state absent
    Then changed is true
    And schema equals the generated schema name
    And exists is false
    And executed_queries equals a single DROP SCHEMA statement
    And the schema no longer exists in EXA_SCHEMAS

@id:scn~ansible-modules.exasol-schema-check-mode-predicts-create-without-writing~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Check mode predicts create without writing
    And the schema does not exist
    When the schema runtime runs in check mode with state present
    Then changed is true
    And exists is true
    And executed_queries equals a single CREATE SCHEMA statement
    And the schema still does not exist in EXA_SCHEMAS

@id:scn~ansible-modules.exasol-schema-check-mode-predicts-no-action-when-schema-exists~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Check mode predicts no action when schema exists
    And the schema already exists
    When the schema runtime runs in check mode with state present
    Then changed is false
    And exists is true
    And executed_queries equals []
    And the schema still exists in EXA_SCHEMAS

@id:scn~ansible-modules.exasol-schema-check-mode-predicts-drop-without-writing~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Check mode predicts drop without writing
    And the schema already exists
    When the schema runtime runs in check mode with state absent and cascade
    Then changed is true
    And exists is false
    And executed_queries equals a single DROP SCHEMA CASCADE statement
    And the schema still exists in EXA_SCHEMAS

@id:scn~ansible-modules.exasol-schema-create-with-owner~1
# Covers: req~exasol-schema-module~1
# Needs: dsn, itest
Scenario: Create a schema with an owner
    And the schema does not exist
    And the requested owner exists
    When the schema runtime runs with state present and owner
    Then changed is true
    And executed_queries equals CREATE SCHEMA followed by ALTER SCHEMA CHANGE OWNER
    And EXA_SCHEMAS reports the requested owner

@id:scn~ansible-modules.exasol-schema-owner-does-not-exist~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Refuse to assign a non-existent owner
    And the schema does not exist
    And the requested owner does not exist
    When the schema runtime runs with state present and owner
    Then the operation fails with an error
    And the CREATE SCHEMA statement already committed before the failure
    And the schema exists but is not owned by the requested owner

@id:scn~ansible-modules.exasol-schema-change-owner~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Change the owner of an existing schema
    And the schema exists with a different owner
    And the requested owner exists
    When the schema runtime runs with state present and owner
    Then changed is true
    And executed_queries equals a single ALTER SCHEMA CHANGE OWNER statement
    And EXA_SCHEMAS reports the requested owner

@id:scn~ansible-modules.exasol-schema-owner-idempotent~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Leave an identical schema owner unchanged
    And the schema exists with the requested owner
    When the schema runtime runs with state present and owner
    Then changed is false
    And executed_queries equals []
    And EXA_SCHEMAS still reports the requested owner

@id:scn~ansible-modules.exasol-schema-owner-check-mode~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Check mode predicts an owner change without writing
    And the schema exists with a different owner
    And the requested owner exists
    When the schema runtime runs in check mode with state present and owner
    Then changed is true
    And executed_queries equals a single ALTER SCHEMA CHANGE OWNER statement
    And EXA_SCHEMAS still reports the original owner

@id:scn~ansible-modules.exasol-schema-owner-check-mode-idempotent~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Check mode predicts no owner change when already matching
    And the schema exists with the requested owner
    When the schema runtime runs in check mode with state present and owner
    Then changed is false
    And executed_queries equals []
    And EXA_SCHEMAS still reports the requested owner

@id:scn~ansible-modules.exasol-schema-set-comment~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Set a schema comment
    And the schema exists without a comment
    When the schema runtime runs with state present and comment
    Then changed is true
    And executed_queries equals a single COMMENT ON SCHEMA statement
    And EXA_SCHEMAS reports the requested comment

@id:scn~ansible-modules.exasol-schema-clear-comment~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Clear a schema comment
    And the schema exists with a comment
    When the schema runtime runs with state present and an empty comment
    Then changed is true
    And executed_queries equals COMMENT ON SCHEMA IS NULL
    And EXA_SCHEMAS reports no comment

@id:scn~ansible-modules.exasol-schema-comment-idempotent~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Leave an identical schema comment unchanged
    And the schema exists with the requested comment
    When the schema runtime runs with state present and comment
    Then changed is false
    And executed_queries equals []
    And EXA_SCHEMAS still reports the requested comment

@id:scn~ansible-modules.exasol-schema-comment-check-mode~1
# Covers: req~exasol-schema-module~1
# Needs: dsn, itest
Scenario: Check mode predicts a comment change without writing
    And the schema exists with a different comment
    When the schema runtime runs in check mode with state present and comment
    Then changed is true
    And executed_queries equals a single COMMENT ON SCHEMA statement
    And EXA_SCHEMAS still reports the original comment

@id:scn~ansible-modules.exasol-schema-comment-check-mode-idempotent~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Check mode predicts no comment change when already matching
    And the schema exists with the requested comment
    When the schema runtime runs in check mode with state present and comment
    Then changed is false
    And executed_queries equals []
    And EXA_SCHEMAS still reports the requested comment

@id:scn~ansible-modules.exasol-schema-rename~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Rename an existing schema
    And the source schema exists
    And the target schema does not exist
    When the schema runtime runs with state present and new_name
    Then changed is true
    And executed_queries equals a single RENAME SCHEMA statement
    And only the target schema exists in EXA_SCHEMAS

@id:scn~ansible-modules.exasol-schema-rename-idempotent~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Leave an already renamed schema unchanged
    And the source schema does not exist
    And the target schema exists
    When the schema runtime runs with state present and new_name
    Then changed is false
    And executed_queries equals []
    And only the target schema exists in EXA_SCHEMAS

@id:scn~ansible-modules.exasol-schema-rename-check-mode~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Check mode predicts a rename without writing
    And the source schema exists
    And the target schema does not exist
    When the schema runtime runs in check mode with state present and new_name
    Then changed is true
    And executed_queries equals a single RENAME SCHEMA statement
    And only the source schema exists in EXA_SCHEMAS

@id:scn~ansible-modules.exasol-schema-rename-check-mode-idempotent~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Check mode predicts no rename when already renamed
    And the source schema does not exist
    And the target schema exists
    When the schema runtime runs in check mode with state present and new_name
    Then changed is false
    And executed_queries equals []
    And only the target schema exists in EXA_SCHEMAS

@id:scn~ansible-modules.exasol-schema-set-raw-size-limit~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Set a schema raw size limit
    And the schema exists without a raw size limit
    When the schema runtime runs with state present and raw_size_limit
    Then changed is true
    And executed_queries equals a single ALTER SCHEMA SET RAW_SIZE_LIMIT statement
    And EXA_ALL_OBJECT_SIZES reports the requested raw size limit

@id:scn~ansible-modules.exasol-schema-change-raw-size-limit~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Change a schema raw size limit
    And the schema exists with a different raw size limit
    When the schema runtime runs with state present and raw_size_limit
    Then changed is true
    And executed_queries equals a single ALTER SCHEMA SET RAW_SIZE_LIMIT statement
    And EXA_ALL_OBJECT_SIZES reports the requested raw size limit

@id:scn~ansible-modules.exasol-schema-raw-size-limit-idempotent~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Leave an identical schema raw size limit unchanged
    And the schema exists with the requested raw size limit
    When the schema runtime runs with state present and raw_size_limit
    Then changed is false
    And executed_queries equals []
    And EXA_ALL_OBJECT_SIZES still reports the requested raw size limit

@id:scn~ansible-modules.exasol-schema-clear-raw-size-limit~1
# Covers: req~exasol-schema-module~1
# Needs: dsn, itest
Scenario: Clear a schema raw size limit
    And the schema exists with a raw size limit
    When the schema runtime runs with state present and raw_size_limit -1
    Then changed is true
    And executed_queries equals a single ALTER SCHEMA SET RAW_SIZE_LIMIT NULL statement
    And EXA_ALL_OBJECT_SIZES reports no raw size limit

@id:scn~ansible-modules.exasol-schema-clear-raw-size-limit-idempotent~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Leave an already cleared schema raw size limit unchanged
    And the schema exists without a raw size limit
    When the schema runtime runs with state present and raw_size_limit -1
    Then changed is false
    And executed_queries equals []

@id:scn~ansible-modules.exasol-schema-clear-raw-size-limit-check-mode~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Check mode predicts clearing a raw size limit without writing
    And the schema exists with a raw size limit
    When the schema runtime runs in check mode with state present and raw_size_limit -1
    Then changed is true
    And executed_queries equals a single ALTER SCHEMA SET RAW_SIZE_LIMIT NULL statement
    And EXA_ALL_OBJECT_SIZES still reports the original raw size limit

@id:scn~ansible-modules.exasol-schema-raw-size-limit-check-mode~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Check mode predicts a raw size limit change without writing
    And the schema exists with a different raw size limit
    When the schema runtime runs in check mode with state present and raw_size_limit
    Then changed is true
    And executed_queries equals a single ALTER SCHEMA SET RAW_SIZE_LIMIT statement
    And EXA_ALL_OBJECT_SIZES still reports the original raw size limit

@id:scn~ansible-modules.exasol-schema-raw-size-limit-check-mode-idempotent~1
# Covers: req~exasol-schema-module~1
# Needs: itest
Scenario: Check mode predicts no raw size limit change when already matching
    And the schema exists with the requested raw size limit
    When the schema runtime runs in check mode with state present and raw_size_limit
    Then changed is false
    And executed_queries equals []
    And EXA_ALL_OBJECT_SIZES still reports the requested raw size limit

@id:scn~ansible-modules.exasol-schema-drop-non-empty-without-cascade~1
# Covers: req~exasol-schema-module~1
# Needs: dsn, itest
Scenario: Refuse to drop a non-empty schema without cascade
    And the schema contains a table
    And the runtime does not check whether the schema contains objects before issuing the drop
    When the schema runtime runs with state absent without cascade
    Then the operation fails with an error mentioning CASCADE
    And the schema and table still exist
