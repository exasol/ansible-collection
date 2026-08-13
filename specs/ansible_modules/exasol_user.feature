Feature: exasol-user Ansible module runtime specification
  Manage Exasol database users directly through the exasol_user Python
  runtime helpers.

  Background:
    Given an Exasol database is reachable at localhost

Rule: Scenario behavior
@id:scn~ansible-modules.exasol-user-password-lifecycle-avoids-privileged-metadata~1
# Covers: req~exasol-user-module~1
# Needs: itest
Scenario: Password user lifecycle avoids privileged metadata
    Given the connected account can manage password-authenticated users
    And the connected account does not have SELECT ANY DICTIONARY
    When the user runtime creates, updates, or removes a password-authenticated user
    Then it checks existence through SYS.EXA_ALL_USERS
    And it does not query SYS.EXA_DBA_USERS

Rule: Scenario behavior
@id:scn~ansible-modules.exasol-user-ldap-metadata-lookup-is-privileged-and-separate~1
# Covers: req~exasol-user-module~1
# Needs: itest
Scenario: LDAP distinguished-name lookup is privileged and separate
    Given an existing LDAP user and an account with SELECT ANY DICTIONARY
    When the user runtime reconciles the requested LDAP distinguished name
    Then it checks existence through SYS.EXA_ALL_USERS
    And it reads DISTINGUISHED_NAME through SYS.EXA_DBA_USERS only for that comparison

Rule: Scenario behavior
@id:scn~ansible-modules.exasol-user-create-missing-user~1
# Covers: req~exasol-user-module~1
# Needs: itest
Scenario: Create a missing user
    And the user does not exist
    When the user runtime runs with state present and a password
    Then changed is true
    And user equals the generated user name
    And exists is true
    And executed_queries equals a CREATE USER statement and a GRANT CREATE SESSION statement
    And the user exists in EXA_ALL_USERS

Rule: Scenario behavior
@id:scn~ansible-modules.exasol-user-leave-existing-user-unchanged~1
# Covers: req~exasol-user-module~1
# Needs: dsn, itest
Scenario: Leave an existing user unchanged
    And the user already exists with a password
    When the user runtime runs again with the same password and update_password on_create
    Then changed is false
    And user equals the generated user name
    And exists is true
    And executed_queries equals []
    And the user still exists in EXA_ALL_USERS

Rule: Scenario behavior
@id:scn~ansible-modules.exasol-user-update-existing-user-password~1
# Covers: req~exasol-user-module~1
# Needs: dsn, itest
Scenario: Update an existing user's password
    And the user already exists with a password and a session grant
    When the user runtime runs with a rotated password and update_password always
    Then changed is true
    And user equals the generated user name
    And exists is true
    And executed_queries equals a single ALTER USER statement
    And the user can authenticate with the rotated password

Rule: Scenario behavior
@id:scn~ansible-modules.exasol-user-drop-existing-user~1
# Covers: req~exasol-user-module~1
# Needs: itest
Scenario: Drop an existing user
    And the user already exists with a password
    When the user runtime runs with state absent and cascade
    Then changed is true
    And user equals the generated user name
    And exists is false
    And executed_queries equals a single DROP USER CASCADE statement
    And the user no longer exists in EXA_ALL_USERS

Rule: Scenario behavior
@id:scn~ansible-modules.exasol-user-check-mode-predicts-create-without-writing~1
# Covers: req~exasol-user-module~1
# Needs: itest
Scenario: Check mode predicts create without writing
    And the user does not exist
    When the user runtime runs in check mode with state present and a password
    Then changed is true
    And exists is true
    And executed_queries equals a CREATE USER statement and a GRANT CREATE SESSION statement
    And the user still does not exist in EXA_ALL_USERS

Rule: Scenario behavior
@id:scn~ansible-modules.exasol-user-check-mode-predicts-no-change-when-user-exists~1
# Covers: req~exasol-user-module~1
# Needs: itest
Scenario: Check mode predicts no change when user exists
    And the user already exists with a password and a session grant
    When the user runtime runs in check mode with state present and no password update
    Then changed is false
    And exists is true
    And executed_queries equals []
    And the user can still authenticate with the old password

Rule: Scenario behavior
@id:scn~ansible-modules.exasol-user-check-mode-predicts-password-update-without-writing~1
# Covers: req~exasol-user-module~1
# Needs: itest
Scenario: Check mode predicts password update without writing
    And the user already exists with a password and a session grant
    When the user runtime runs in check mode with a rotated password and update_password always
    Then changed is true
    And exists is true
    And executed_queries equals a single ALTER USER statement
    And the user can still authenticate with the old password

Rule: Scenario behavior
@id:scn~ansible-modules.exasol-user-check-mode-predicts-drop-without-writing~1
# Covers: req~exasol-user-module~1
# Needs: itest
Scenario: Check mode predicts drop without writing
    And the user already exists with a password
    When the user runtime runs in check mode with state absent and cascade
    Then changed is true
    And exists is false
    And executed_queries equals a single DROP USER CASCADE statement
    And the user still exists in EXA_ALL_USERS
