# setup_exasol

Installs and configures the prerequisites needed to operate Exasol with this
collection.

## Requirements

- Target hosts must support the tasks implemented by this role.

## Role Variables

This role currently has no documented variables beyond its defaults.

## Example Playbook

```yaml
- hosts: exasol_hosts
  roles:
    - role: exasol.exasol.setup_exasol
```

## License

MIT License.
