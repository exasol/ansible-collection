# Security Considerations

This change expands the collection's database-administration surface. The main assets are Exasol credentials, authorization state, Ansible logs, and the integrity of automated schema, user, role, grant, and script execution workflows.

## Security Assessment

### Affects Authentication / Authorization

See [Affects Authentication / Authorization](security_considerations/affects_authentication_authorization.md).

### Introduces or Modifies Sensitive Data Handling, Security-Relevant Processing, or Data Access Behavior

See [Introduces or Modifies Sensitive Data Handling, Security-Relevant Processing, or Data Access Behavior](security_considerations/introduces_or_modifies_sensitive_data_handling_security_relevant_processing_or_data_access_behavior.md).

### Impacts External Interfaces / APIs

See [Impacts External Interfaces / APIs](security_considerations/impacts_external_interfaces_apis.md).

### Involves New Dependencies or Services

See [Involves New Dependencies or Services](security_considerations/involves_new_dependencies_or_services.md).

### Affects Infrastructure or Configuration

See [Affects Infrastructure or Configuration](security_considerations/affects_infrastructure_or_configuration.md).

## Other Security Considerations

### Data At Rest, PII, and Local Persistence

See [Data At Rest, PII, and Local Persistence](security_considerations/data_at_rest_pii_and_local_persistence.md).

### Accountability, Compliance, and Auditability

See [Accountability, Compliance, and Auditability](security_considerations/accountability_compliance_and_auditability.md).

### Availability and Failure Handling

See [Availability and Failure Handling](security_considerations/availability_and_failure_handling.md).

### Tier Segregation and Trusted-Operator Boundary

See [Tier Segregation and Trusted-Operator Boundary](security_considerations/tier_segregation_and_trusted_operator_boundary.md).

## Residual Risk

`exasol_query` intentionally enables operator-supplied SQL execution today, and any future `exasol_script` module would do the same for a broader trusted-operator surface. The security boundary is therefore operator authorization, secret-safe handling, and transport protection, not restriction of SQL semantics inside the module.

Trusted operators can still intentionally or accidentally execute destructive SQL. This risk is accepted as part of the module's purpose and must be managed operationally through least privilege, review of playbooks, and controlled execution environments.
