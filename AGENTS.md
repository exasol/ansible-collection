# AGENTS.md

## Running Tests

- Check for a local `.env` file before running integration or acceptance tests.
- If `.env` exists, load it for test commands with `set -a; source .env; set +a; ...` so `PYTEST_ADDOPTS` and backend flags are applied.
- For `test/integration/acceptance/*`, a plain `poetry run pytest ...` can be misleading:
  it may skip tests because the backend selection and connection options were not loaded.
- In this repository, the local `.env` currently sets `--backend=onprem` and Exasol connection arguments for acceptance tests.
- If acceptance tests need to connect to a local database or other service, sandboxed execution may fail with socket errors such as `PermissionError: [Errno 1] Operation not permitted`.
- When that happens, rerun the same test command with escalation so the process can reach local services outside the sandbox.
- Distinguish environment failures from code failures:
  skipped tests usually mean missing backend configuration, while connection errors during setup usually mean sandbox/network restrictions.
