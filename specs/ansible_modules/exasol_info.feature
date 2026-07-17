Feature: exasol-info Ansible module runtime specification
  Gather Exasol server information directly through the exasol_info Python
  runtime helpers.

  @exasol-info-returns-version-and-cluster-size
  Scenario: Return basic server metadata
    Given an Exasol database is reachable at localhost
    When the info runtime runs with valid login parameters
    Then changed is false
    And version exists and is non-empty
    And database_name exists and is non-empty
    And cluster_size exists and is at least 1
