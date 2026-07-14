Feature: exasol-role Ansible module runtime specification
  Manage Exasol database roles directly through the exasol_role Python
  runtime helpers.

  @exasol-role-create-missing-role
  Scenario: Create a missing role
    Given an Exasol database is reachable at localhost
    And the role does not exist
    When the role runtime runs with state present
    Then changed is true
    And role equals the generated role name
    And exists is true
    And executed_queries equals a single CREATE ROLE statement
    And the role exists in EXA_ALL_ROLES

  @exasol-role-leave-existing-role-unchanged
  Scenario: Leave an existing role unchanged
    Given an Exasol database is reachable at localhost
    And the role already exists
    When the role runtime runs with state present
    Then changed is false
    And role equals the generated role name
    And exists is true
    And executed_queries equals []
    And the role still exists in EXA_ALL_ROLES

  @exasol-role-drop-existing-role
  Scenario: Drop an existing role
    Given an Exasol database is reachable at localhost
    And the role already exists
    When the role runtime runs with state absent and cascade
    Then changed is true
    And role equals the generated role name
    And exists is false
    And executed_queries equals a single DROP ROLE CASCADE statement
    And the role no longer exists in EXA_ALL_ROLES

  @exasol-role-check-mode-predicts-create-without-writing
  Scenario: Check mode predicts create without writing
    Given an Exasol database is reachable at localhost
    And the role does not exist
    When the role runtime runs in check mode with state present
    Then changed is true
    And exists is true
    And executed_queries equals a single CREATE ROLE statement
    And the role still does not exist in EXA_ALL_ROLES

  @exasol-role-check-mode-predicts-drop-without-writing
  Scenario: Check mode predicts drop without writing
    Given an Exasol database is reachable at localhost
    And the role already exists
    When the role runtime runs in check mode with state absent and cascade
    Then changed is true
    And exists is false
    And executed_queries equals a single DROP ROLE CASCADE statement
    And the role still exists in EXA_ALL_ROLES
