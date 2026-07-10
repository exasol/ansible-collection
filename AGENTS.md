# AGENTS.md

## Spec-Driven Development

- For issue-driven planning and implementation, use the OpenFastTrace spec-driven development skill:
  https://github.com/itsallcode/openfasttrace/raw/refs/heads/main/.agents/skills/openfasttrace-spec-driven-development/SKILL.md
- Treat `doc/system_requirements.md`, `doc/design_index.md`, referenced `doc/design/` chapters, and `doc/changesets/` as the source of truth for changes that affect requirements, design, behavior, tests, or verification.
- Before substantial implementation for a new issue, create or update the matching changeset in `doc/changesets/` and derive its tasks from the requirements, design, and quality requirements.
- Keep OpenFastTrace IDs stable unless semantics change, and keep traceability clean between requirements, scenarios, threats, design items, implementation, and tests.
- Run requirement tracing with `poetry run nox -s requirements:trace`.

## Running Tests

- Check for a local `.env` file before running integration or acceptance tests.
- If `.env` exists, load it for test commands with `set -a; source .env; set +a; ...` so `PYTEST_ADDOPTS` and Exasol connection flags are applied.
- For `test/integration/acceptance/*`, a plain `poetry run pytest ...` can be misleading:
  it may start a managed ITDE database or use default connection options because the local connection options were not loaded.
- In this repository, the local `.env` currently sets `--itde-db-version=external` and Exasol connection arguments for acceptance tests.
- If acceptance tests need to connect to a local database or other service, sandboxed execution may fail with socket errors such as `PermissionError: [Errno 1] Operation not permitted`.
- When that happens, rerun the same test command with escalation so the process can reach local services outside the sandbox.
- Distinguish environment failures from code failures:
  unexpected managed-database startup usually means missing local configuration, while connection errors during setup usually mean sandbox/network restrictions.
