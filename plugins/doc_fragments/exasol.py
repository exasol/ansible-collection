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
    required: true
  login_db:
    description:
      - Schema to open after connecting to Exasol.
      - This value is mapped to the pyexasol C(schema) connection argument.
    type: str
    default: ''
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
  compression:
    description:
      - Whether pyexasol should use zlib compression for WebSocket and HTTP
        transport.
    type: bool
    default: false
  encryption:
    description:
      - Whether pyexasol should use TLS for WebSocket and HTTP transport.
      - TLS is enabled by default. Set this option to V(false) only when the
        target Exasol deployment explicitly requires an unencrypted connection.
    type: bool
    default: true
  client_kwargs:
    description:
      - Additional keyword arguments passed to C(pyexasol.connect).
      - This option is treated as sensitive by the shared module argument spec.
    type: dict
    default: {}
requirements:
  - pyexasol
"""
