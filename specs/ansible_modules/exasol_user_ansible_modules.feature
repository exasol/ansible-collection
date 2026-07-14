Feature: exasol-user Ansible module runtime specification
  Manage Exasol database users directly through the exasol_user Python
  runtime helpers.

  @exasol-user-create-missing-user
  Scenario: Create a missing user
    Given an Exasol database is reachable at localhost
    And the user does not exist
    When the user runtime runs with state present and a password
    Then changed is true
    And user equals the generated user name
    And exists is true
    And executed_queries equals a CREATE USER statement and a GRANT CREATE SESSION statement
    And the user exists in EXA_ALL_USERS

  @exasol-user-leave-existing-user-unchanged
  Scenario: Leave an existing user unchanged
    Given an Exasol database is reachable at localhost
    And the user already exists with a password
    When the user runtime runs again with the same password and update_password on_create
    Then changed is false
    And user equals the generated user name
    And exists is true
    And executed_queries equals []
    And the user still exists in EXA_ALL_USERS

  @exasol-user-update-existing-user-password
  Scenario: Update an existing user's password
    Given an Exasol database is reachable at localhost
    And the user already exists with a password and a session grant
    When the user runtime runs with a rotated password and update_password always
    Then changed is true
    And user equals the generated user name
    And exists is true
    And executed_queries equals a single ALTER USER statement
    And the user can authenticate with the rotated password

  @exasol-user-drop-existing-user
  Scenario: Drop an existing user
    Given an Exasol database is reachable at localhost
    And the user already exists with a password
    When the user runtime runs with state absent and cascade
    Then changed is true
    And user equals the generated user name
    And exists is false
    And executed_queries equals a single DROP USER CASCADE statement
    And the user no longer exists in EXA_ALL_USERS

  @exasol-user-check-mode-predicts-create-without-writing
  Scenario: Check mode predicts create without writing
    Given an Exasol database is reachable at localhost
    And the user does not exist
    When the user runtime runs in check mode with state present and a password
    Then changed is true
    And exists is true
    And executed_queries equals a CREATE USER statement and a GRANT CREATE SESSION statement
    And the user still does not exist in EXA_ALL_USERS

  @exasol-user-check-mode-predicts-drop-without-writing
  Scenario: Check mode predicts drop without writing
    Given an Exasol database is reachable at localhost
    And the user already exists with a password
    When the user runtime runs in check mode with state absent and cascade
    Then changed is true
    And exists is false
    And executed_queries equals a single DROP USER CASCADE statement
    And the user still exists in EXA_ALL_USERS
