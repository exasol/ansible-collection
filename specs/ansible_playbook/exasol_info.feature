Feature: exasol-info specification
  Gather Exasol server information from Ansible playbooks.

  Background:
    Given an Exasol cluster reachable at login_host

    @exasol-info-return-cluster-info
    Scenario: Returns version and cluster info
      When exasol_info runs with valid credentials
      Then result MUST contain key "version"
      And result.version MUST match a semver-like pattern (e.g. "8.x.y")
      And result MUST contain key "database_name"
      And result MUST contain key "cluster_size"
      And result.cluster_size MUST be at least 1
      And changed MUST always be false

    @exasol-info-check-mode
    Scenario: Supports check mode
      When exasol_info runs in check mode with valid credentials
      Then result MUST contain key "version"
      And result MUST contain key "database_name"
      And result MUST contain key "cluster_size"
      And changed MUST always be false
