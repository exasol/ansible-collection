Feature: exasol-script specification
  Execute multi-statement Exasol SQL scripts from Ansible playbooks.

  @exasol-script-execute-simple-multi-statement-script
  Scenario: Execute a simple multi-statement script
    Given an Exasol database is reachable at localhost
    When exasol_script runs a script creating a schema, a table, and a row
    Then changed is true
    And executed_queries preserves the supplied statement order
    And query_result contains the inserted row's id

  @exasol-script-execute-script-body-with-slash-terminator
  Scenario: Execute a script body terminated by a standalone slash line
    Given an Exasol database is reachable at localhost
    When exasol_script runs a CREATE SCRIPT body with embedded semicolons terminated by a standalone "/" line
    Then changed is true
    And executed_queries contains a single CREATE SCRIPT statement
    And the script exists in EXA_ALL_SCRIPTS

  @exasol-script-read-only-script-reports-unchanged
  Scenario: Read-only script reports unchanged
    Given an Exasol database is reachable at localhost
    When exasol_script runs a script containing only SELECT statements
    Then changed is false
    And query_result contains the last statement's selected value

  @exasol-script-failing-statement-blocks-later-statements
  Scenario: Failing statement blocks later statements
    Given an Exasol database is reachable at localhost
    When exasol_script runs a script whose second statement fails
    Then the module fails with an error mentioning the failing statement
    And the schema from the first statement exists in EXA_ALL_SCHEMAS
    And the table from the third statement does not exist in EXA_ALL_TABLES

  @exasol-script-check-mode-read-only-script
  Scenario: Check mode keeps a read-only script on the execution path
    Given an Exasol database is reachable at localhost
    When exasol_script runs a read-only script in check mode
    Then changed is false
    And query_result is not empty

  @exasol-script-check-mode-write-script
  Scenario: Check mode predicts a write script without executing it
    Given an Exasol database is reachable at localhost
    When exasol_script runs a script creating a schema in check mode
    Then changed is true
    And executed_queries equals the whole script as one entry
    And the schema does not exist in EXA_ALL_SCHEMAS

  @exasol-script-sanitize-bad-credentials
  Scenario: Sanitize bad credential errors
    Given an Exasol database is reachable at localhost
    When exasol_script runs with an invalid login password
    Then the module fails with an authentication error
    And the invalid password is not exposed

  @exasol-script-reject-unsupported-bound-arguments
  Scenario: Reject unsupported bound arguments
    Given an Exasol database is reachable at localhost
    When exasol_script runs with a positional_args argument
    Then the module fails with an unsupported parameters error

  @exasol-script-reports-per-statement-results-and-rowcount
  Scenario: Report one result list and rowcount entry per statement
    Given an Exasol database is reachable at localhost
    When exasol_script runs a script creating a table, inserting a row, and selecting from it
    Then query_all_results contains one entry per statement
    And the entry for the SELECT statement contains the selected row
    And rowcount contains one entry per statement

  @exasol-script-reports-execution-time-per-statement
  Scenario: Report execution time per statement
    Given an Exasol database is reachable at localhost
    When exasol_script runs a script containing two statements
    Then execution_time_ms contains one entry per statement

  @exasol-script-statement-failure-does-not-expose-password
  Scenario: Statement failure error does not expose the connection password
    Given an Exasol database is reachable at localhost
    When exasol_script runs a script whose second statement fails
    Then the module fails with an error mentioning the failing statement
    And the login password is not exposed

  @exasol-script-reject-named-args
  Scenario: Reject named arguments
    Given an Exasol database is reachable at localhost
    When exasol_script runs with a named_args argument
    Then the module fails with an unsupported parameters error
