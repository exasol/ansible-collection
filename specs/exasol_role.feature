Feature: exasol-role specification
  Manage Exasol database roles from Ansible playbooks.

  @exasol-role-create-missing-role
  Scenario: Create missing role
    Given an Exasol database is reachable at localhost
    And role "READER" does not exist in EXA_ALL_ROLES
    When exasol_role runs with:
      | name   | state   |
      | READER | present |
    Then changed is true
    And role equals "READER"
    And exists is true
    And executed_queries equals:
      | sql                  |
      | CREATE ROLE "READER" |
    And EXA_ALL_ROLES contains one row where ROLE_NAME equals "READER"

  @exasol-role-preserves-exact-identifier
  Scenario: Create role with exact identifier semantics
    Given an Exasol database is reachable at localhost
    And exact-identifier role "Reader+/=Role" does not exist in EXA_ALL_ROLES
    When exasol_role runs with:
      | name          | state   |
      | "Reader+/=Role" | present |
    Then changed is true
    And role equals "\"Reader+/=Role\""
    And exists is true
    And executed_queries equals:
      | sql                           |
      | CREATE ROLE "Reader+/=Role"   |
    And EXA_ALL_ROLES contains one row where ROLE_NAME equals "Reader+/=Role"

  @exasol-role-present-idempotent
  Scenario: Present role is idempotent
    Given an Exasol database is reachable at localhost
    And role "READER" already exists in EXA_ALL_ROLES
    When exasol_role runs with:
      | name   | state   |
      | READER | present |
    Then changed is false
    And exists is true
    And executed_queries equals []

  @exasol-role-present-idempotent-with-different-case-spelling
  Scenario: Present role stays idempotent across case-only spelling changes
    Given an Exasol database is reachable at localhost
    And exact-identifier role "Reader+/=Role" already exists in EXA_ALL_ROLES
    When exasol_role runs with:
      | name              | state   |
      | "reader+/=role"   | present |
    Then changed is false
    And role equals "\"reader+/=role\""
    And exists is true
    And executed_queries equals []
    And EXA_ALL_ROLES contains one row where ROLE_NAME equals "Reader+/=Role"

  @exasol-role-check-mode-create
  Scenario: Check mode predicts create
    Given an Exasol database is reachable at localhost
    And role "CHECK_READER" does not exist in EXA_ALL_ROLES
    When exasol_role runs in check mode with:
      | name         | state   |
      | CHECK_READER | present |
    Then changed is true
    And exists is true
    And executed_queries equals:
      | sql                         |
      | CREATE ROLE "CHECK_READER" |
    And role "CHECK_READER" still does not exist in EXA_ALL_ROLES

  @exasol-role-check-mode-drop
  Scenario: Check mode predicts drop
    Given an Exasol database is reachable at localhost
    And role "READER" exists in EXA_ALL_ROLES
    When exasol_role runs in check mode with:
      | name   | state  | cascade |
      | READER | absent | true    |
    Then changed is true
    And exists is false
    And executed_queries equals:
      | sql                        |
      | DROP ROLE "READER" CASCADE |
    And role "READER" still exists in EXA_ALL_ROLES

  @exasol-role-drop-existing-role
  Scenario: Drop existing role
    Given an Exasol database is reachable at localhost
    And role "READER" exists in EXA_ALL_ROLES
    When exasol_role runs with:
      | name   | state  | cascade |
      | READER | absent | true    |
    Then changed is true
    And exists is false
    And executed_queries equals:
      | sql                        |
      | DROP ROLE "READER" CASCADE |
    And role "READER" no longer exists in EXA_ALL_ROLES

  @exasol-role-drop-missing-role
  Scenario: Drop missing role
    Given an Exasol database is reachable at localhost
    And role "READER" does not exist in EXA_ALL_ROLES
    When exasol_role runs with:
      | name   | state  |
      | READER | absent |
    Then changed is false
    And exists is false
    And executed_queries equals []
