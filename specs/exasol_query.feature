Feature: exasol-query specification
  Execute Exasol SQL statements from Ansible playbooks.

  @exasol-query-read-metadata-version
  Scenario: Read database version metadata
    Given an Exasol database is reachable at localhost
    When exasol_query runs a read-only EXA_METADATA query
    Then changed is false
    And one result row contains a non-empty database version
    And execution_time_ms contains one entry

  @exasol-query-single-select
  Scenario: Execute single SELECT
    Given an Exasol database is reachable at localhost
    When exasol_query runs "SELECT 11 AS A"
    Then changed is false
    And query_result contains value "11"
    And query_all_results contains one result set
    And executed_queries equals:
      | sql            |
      | SELECT 11 AS A |

  @exasol-query-batch-statements
  Scenario: Execute statement batch on one connection
    Given an Exasol database is reachable at localhost
    And a disposable schema does not exist
    When exasol_query runs a batch creating a schema, table, rows, and summary query
    Then changed is true
    And executed_queries preserves the supplied order
    And query_result contains row count "2"
    And query_result contains note "backend"

  @exasol-query-positional-args
  Scenario: Bind positional arguments
    Given an Exasol database is reachable at localhost
    When exasol_query runs "SELECT ? AS A" with positional argument "42"
    Then changed is false
    And query_result contains value "42"

  @exasol-query-named-args
  Scenario: Bind named arguments
    Given an Exasol database is reachable at localhost
    When exasol_query runs "SELECT :n AS A" with named argument "n=7"
    Then changed is false
    And query_result contains value "7"

  @exasol-query-check-mode-select
  Scenario: Execute read-only query in check mode
    Given an Exasol database is reachable at localhost
    When exasol_query runs "SELECT 13 AS A" in check mode
    Then changed is false
    And query_result contains value "13"

  @exasol-query-check-mode-write
  Scenario: Predict write in check mode without execution
    Given an Exasol database is reachable at localhost
    And a disposable check-mode schema does not exist
    When exasol_query runs CREATE SCHEMA in check mode
    Then changed is true
    And no query is executed
    And the check-mode schema still does not exist

  @exasol-query-sanitize-bad-credentials
  Scenario: Sanitize bad credential errors
    Given an Exasol database is reachable at localhost
    When exasol_query runs with an invalid login password
    Then the module fails with an authentication error
    And the invalid password is not exposed
