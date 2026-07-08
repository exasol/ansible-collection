# Security Considerations

This change expands the collection's database-administration surface. The main assets are Exasol credentials, authorization state, Ansible logs, and the integrity of automated schema, user, role, grant, and script execution workflows.

```{toctree}
:maxdepth: 1
:hidden:

security/affects_authentication_authorization
security/introduces_or_modifies_sensitive_data_handling_security_relevant_processing_or_data_access_behavior
security/impacts_external_interfaces_apis
security/involves_new_dependencies_or_services
security/affects_infrastructure_or_configuration
security/data_at_rest_pii_and_local_persistence
security/accountability_compliance_and_auditability
security/availability_and_failure_handling
security/tier_segregation_and_trusted_operator_boundary
```

## Security Assessment

* [Affects Authentication / Authorization](security/affects_authentication_authorization.md).
* [Introduces or Modifies Sensitive Data Handling, Security-Relevant Processing, or Data Access Behavior](security/introduces_or_modifies_sensitive_data_handling_security_relevant_processing_or_data_access_behavior.md).
* [Impacts External Interfaces / APIs](security/impacts_external_interfaces_apis.md).
* [Involves New Dependencies or Services](security/involves_new_dependencies_or_services.md).
* [Affects Infrastructure or Configuration](security/affects_infrastructure_or_configuration.md).

## Other Security Considerations

* [Data At Rest, PII, and Local Persistence](security/data_at_rest_pii_and_local_persistence.md).
* [Accountability, Compliance, and Auditability](security/accountability_compliance_and_auditability.md).
* [Availability and Failure Handling](security/availability_and_failure_handling.md).
* [Tier Segregation and Trusted-Operator Boundary](security/tier_segregation_and_trusted_operator_boundary.md).

## Residual Risk

`exasol_query` intentionally enables operator-supplied SQL execution today, and any future `exasol_script` module would do the same for a broader trusted-operator surface. The security boundary is therefore operator authorization, secret-safe handling, and transport protection, not restriction of SQL semantics inside the module.

Trusted operators can still intentionally or accidentally execute destructive SQL. This risk is accepted as part of the module's purpose and must be managed operationally through least privilege, review of playbooks, and controlled execution environments.
