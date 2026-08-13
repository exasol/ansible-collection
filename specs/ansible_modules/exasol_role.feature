Feature: exasol-role Ansible module runtime specification
  Manage Exasol database roles directly through the exasol_role Python
  runtime helpers.

  Background:
    Given an Exasol database is reachable at localhost

@id:scn~ansible-modules.exasol-role-lifecycle-avoids-privileged-metadata~1
# Covers: req~exasol-role-module~1
# Needs: itest
Scenario: Role lifecycle avoids privileged metadata
    Given the connected account can manage roles
    And the connected account does not have SELECT ANY DICTIONARY
    When the role runtime creates or removes a role
    Then it checks existence through SYS.EXA_ALL_ROLES
    And it does not query a privileged dictionary view

@id:scn~ansible-modules.exasol-role-create-missing-role~1
# Covers: req~exasol-role-module~1
# Needs: itest
Scenario: Create a missing role
    And the role does not exist
    When the role runtime runs with state present
    Then changed is true
    And role equals the generated role name
    And exists is true
    And executed_queries equals a single CREATE ROLE statement
    And the role exists in EXA_ALL_ROLES

@id:scn~ansible-modules.exasol-role-leave-existing-role-unchanged~1
# Covers: req~exasol-role-module~1
# Needs: itest
Scenario: Leave an existing role unchanged
    And the role already exists
    When the role runtime runs with state present
    Then changed is false
    And role equals the generated role name
    And exists is true
    And executed_queries equals []
    And the role still exists in EXA_ALL_ROLES

@id:scn~ansible-modules.exasol-role-drop-existing-role~1
# Covers: req~exasol-role-module~1
# Needs: itest
Scenario: Drop an existing role
    And the role already exists
    When the role runtime runs with state absent and cascade
    Then changed is true
    And role equals the generated role name
    And exists is false
    And executed_queries equals a single DROP ROLE CASCADE statement
    And the role no longer exists in EXA_ALL_ROLES

@id:scn~ansible-modules.exasol-role-check-mode-predicts-create-without-writing~1
# Covers: req~exasol-role-module~1
# Needs: itest
Scenario: Check mode predicts create without writing
    And the role does not exist
    When the role runtime runs in check mode with state present
    Then changed is true
    And exists is true
    And executed_queries equals a single CREATE ROLE statement
    And the role still does not exist in EXA_ALL_ROLES

@id:scn~ansible-modules.exasol-role-check-mode-predicts-no-action-when-role-exists~1
# Covers: req~exasol-role-module~1
# Needs: itest
Scenario: Check mode predicts no action when role exists
    And the role already exists
    When the role runtime runs in check mode with state present
    Then changed is false
    And exists is true
    And executed_queries equals []
    And the role still exists in EXA_ALL_ROLES

@id:scn~ansible-modules.exasol-role-check-mode-predicts-drop-without-writing~1
# Covers: req~exasol-role-module~1
# Needs: itest
Scenario: Check mode predicts drop without writing
    And the role already exists
    When the role runtime runs in check mode with state absent and cascade
    Then changed is true
    And exists is false
    And executed_queries equals a single DROP ROLE CASCADE statement
    And the role still exists in EXA_ALL_ROLES
