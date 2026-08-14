Feature: exasol-role specification
  Manage Exasol database roles from Ansible playbooks.

  Background:
    Given an Exasol database is reachable at localhost

@id:scn~ansible-playbook.exasol-role-create-missing-role~1
# Covers: req~exasol-role-module~1
# Needs: itest
Scenario: Create missing role
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

@id:scn~ansible-playbook.exasol-role-preserves-exact-identifier~1
# Covers: req~exasol-role-module~1
# Needs: itest
Scenario: Create role with exact identifier semantics
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

@id:scn~ansible-playbook.exasol-role-present-idempotent~1
# Covers: req~exasol-role-module~1
# Needs: itest
Scenario: Present role is idempotent
    And role "READER" already exists in EXA_ALL_ROLES
    When exasol_role runs with:
      | name   | state   |
      | READER | present |
    Then changed is false
    And exists is true
    And executed_queries equals []

@id:scn~ansible-playbook.exasol-role-present-idempotent-with-different-case-spelling~1
# Covers: req~exasol-role-module~1
# Needs: itest
Scenario: Present role stays idempotent across case-only spelling changes
    And exact-identifier role "Reader+/=Role" already exists in EXA_ALL_ROLES
    When exasol_role runs with:
      | name              | state   |
      | "reader+/=role"   | present |
    Then changed is false
    And role equals "\"reader+/=role\""
    And exists is true
    And executed_queries equals []
    And EXA_ALL_ROLES contains one row where ROLE_NAME equals "Reader+/=Role"

@id:scn~ansible-playbook.exasol-role-check-mode-create~1
# Covers: req~exasol-role-module~1
# Needs: itest
Scenario: Check mode predicts create
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

@id:scn~ansible-playbook.exasol-role-check-mode-drop~1
# Covers: req~exasol-role-module~1
# Needs: itest
Scenario: Check mode predicts drop
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

@id:scn~ansible-playbook.exasol-role-drop-existing-role~1
# Covers: req~exasol-role-module~1
# Needs: itest
Scenario: Drop existing role
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

@id:scn~ansible-playbook.exasol-role-drop-missing-role~1
# Covers: req~exasol-role-module~1
# Needs: itest
Scenario: Drop missing role
    And role "READER" does not exist in EXA_ALL_ROLES
    When exasol_role runs with:
      | name   | state  |
      | READER | absent |
    Then changed is false
    And exists is false
    And executed_queries equals []
