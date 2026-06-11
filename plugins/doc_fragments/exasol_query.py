"""Documentation fragments for Exasol modules."""

from __future__ import annotations


class ModuleDocFragment:
    """Shared Exasol module documentation fragments."""

    DOCUMENTATION = r"""
options:
  login_host:
    description:
      - Host name or IP address of the Exasol database.
    type: str
    default: localhost
  login_port:
    description:
      - Port of the Exasol database.
    type: int
    default: 8563
  login_user:
    description:
      - User name used to authenticate with Exasol.
    type: str
    required: true
  login_password:
    description:
      - Password used to authenticate with Exasol.
    type: str
  login_db:
    description:
      - Schema to open after connecting to Exasol.
      - This value is mapped to the pyexasol C(schema) connection argument.
      - This collection keeps the familiar Ansible database-module option name
        even though Exasol has schemas rather than per-connection databases.
    type: str
    default: ''
    aliases:
      - login_schema
  autocommit:
    description:
      - Whether pyexasol should enable autocommit for the connection.
    type: bool
    default: true
  fetch_size:
    description:
      - Maximum pyexasol fetch message size in bytes.
      - This value is mapped to the pyexasol C(fetch_size_bytes) argument.
    type: int
    default: 5000
  compression:
    description:
      - Whether pyexasol should use zlib compression for WebSocket and HTTP
        transport.
    type: bool
    default: false
  encryption:
    description:
      - Whether pyexasol should use TLS for the Exasol connection.
    type: bool
    default: true
  validate_certs:
    description:
      - Whether pyexasol should validate the TLS certificate presented by Exasol.
      - Public CA certificates and system-wide trust stores are used by default.
      - Set O(ca_cert) when the Exasol certificate is signed by a private CA.
      - When O(certificate_fingerprint) is set, this option controls whether CA
        validation also runs before fingerprint validation.
    type: bool
    default: true
  ca_cert:
    description:
      - Path to a CA certificate or certificate bundle used to validate the TLS
        certificate presented by Exasol.
      - This value is mapped to the websocket-client C(ca_certs) SSL option.
      - This option is only used when O(validate_certs) is V(true).
    type: path
  certificate_fingerprint:
    description:
      - Expected SHA-256 fingerprint of the TLS certificate presented by Exasol.
      - This value is appended to the pyexasol DSN and validated by pyexasol.
      - Set O(validate_certs) to V(false) to use the fingerprint as the trust
        anchor for self-signed certificates.
      - Use a hexadecimal fingerprint without separators.
    type: str
  client_kwargs:
    description:
      - Additional keyword arguments passed to C(pyexasol.connect).
      - This option is treated as sensitive by the shared module argument spec.
    type: dict
    default: {}
requirements:
  - exasol-ansible-modules
"""
