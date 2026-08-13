Feature: exasol-query specification
  Execute Exasol SQL statements from Ansible playbooks.

  Background:
    Given an Exasol database is reachable at localhost

@id:scn~ansible-playbook.exasol-query-read-metadata-version~1
# Covers: req~exasol-query-module~1
# Needs: itest
Scenario: Read database version metadata
    When exasol_query runs a read-only EXA_METADATA query
    Then changed is false
    And one result row contains a non-empty database version
    And execution_time_ms contains one entry

@id:scn~ansible-playbook.exasol-query-single-select~1
# Covers: req~exasol-query-module~1
# Needs: itest
Scenario: Execute single SELECT
    When exasol_query runs "SELECT 11 AS A"
    Then changed is false
    And query_result contains value "11"
    And query_all_results contains one result set
    And executed_queries equals:
      | sql            |
      | SELECT 11 AS A |

@id:scn~ansible-playbook.exasol-query-login-schema-canonical~1
# Covers: req~exasol-query-module~1
# Needs: itest
Scenario: Select a connection schema with login_schema
    Given a schema exists for the connection
    When exasol_query runs with login_schema set to that schema and login_db unset
    Then the query runs with that schema selected

@id:scn~ansible-playbook.exasol-query-login-db-deprecated-alias~1
# Covers: req~exasol-query-module~1
# Needs: itest
Scenario: Select a connection schema with deprecated login_db
    Given a schema exists for the connection
    When exasol_query runs with login_schema unset and login_db set to that schema
    Then the query runs with that schema selected

@id:scn~ansible-playbook.exasol-query-login-schema-legacy-precedence~1
# Covers: req~exasol-query-module~1
# Needs: itest
Scenario: Prefer login_db when both schema parameters are supplied
    Given two schemas exist for the connection
    When exasol_query runs with login_schema and login_db set to different schemas
    Then the query runs with the login_db schema selected
    And Ansible warns that both the option and its alias are set

@id:scn~ansible-playbook.exasol-query-login-schema-same-value-warning~1
# Covers: req~exasol-query-module~1
# Needs: itest
Scenario: Warn when both schema parameters have the same value
    Given a schema exists for the connection
    When exasol_query runs with login_schema and login_db set to that same schema
    Then the query runs with that schema selected
    And Ansible warns that both the option and its alias are set

@id:scn~ansible-playbook.exasol-query-batch-statements~1
# Covers: req~exasol-query-module~1
# Needs: itest
Scenario: Execute statement batch on one connection
    And a schema does not exist
    When exasol_query runs a batch creating a schema, table, rows, and summary query
    Then changed is true
    And executed_queries preserves the supplied order
    And query_result contains row count "2"
    And query_result contains note "backend"

@id:scn~ansible-playbook.exasol-query-positional-args~1
# Covers: req~exasol-query-module~1
# Needs: itest
Scenario: Bind positional arguments
    When exasol_query runs "SELECT ? AS A" with positional argument "42"
    Then changed is false
    And query_result contains value "42"

@id:scn~ansible-playbook.exasol-query-named-args~1
# Covers: req~exasol-query-module~1
# Needs: itest
Scenario: Bind named arguments
    When exasol_query runs "SELECT :n AS A" with named argument "n=7"
    Then changed is false
    And query_result contains value "7"

@id:scn~ansible-playbook.exasol-query-check-mode-select~1
# Covers: req~exasol-query-module~1
# Needs: itest
Scenario: Execute read-only query in check mode
    When exasol_query runs "SELECT 13 AS A" in check mode
    Then changed is false
    And query_result contains value "13"

@id:scn~ansible-playbook.exasol-query-check-mode-write~1
# Covers: req~exasol-query-module~1
# Needs: itest
Scenario: Predict write in check mode without execution
    And a check-mode schema does not exist
    When exasol_query runs CREATE SCHEMA in check mode
    Then changed is true
    And no query is executed
    And the check-mode schema still does not exist

@id:scn~ansible-playbook.exasol-query-sanitize-bad-credentials~1
# Covers: req~exasol-query-module~1
# Needs: itest
Scenario: Sanitize bad credential errors
    When exasol_query runs with an invalid login password
    Then the module fails with an authentication error
    And the invalid password is not exposed

@id:scn~ansible-playbook.exasol-query-reject-batch-args~1
# Covers: req~exasol-query-module~1
# Needs: itest
Scenario: Reject bound arguments for statement batch
    When exasol_query runs a statement batch with bound arguments
    Then the module fails with a validation error
    And the error explains that bound arguments require a single statement

@id:scn~ansible-playbook.exasol-query-check-mode-mixed-batch~1
# Covers: req~exasol-query-module~1
# Needs: itest
Scenario: Skip mixed read-write batch in check mode
    And a check-mode schema does not exist
    When exasol_query runs a batch containing SELECT and CREATE SCHEMA in check mode
    Then changed is true
    And no statement in the batch is executed
    And the check-mode schema still does not exist
