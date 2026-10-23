---
part: Runtime
status: shipped
updated: 2026-10-23
---

# Database credential out of the public compose file (2026-10-22)

**Review 2026-10-23: shipped, not verified.** On `main` and pushed: `37b0157` (DSN from `SMARTGARDEN_DATABASE_URL`), `d54a56c` (SQLAlchemy 2.0.51 pin), `4f552b2` (`validate_ssh_target`, tests in `backend/tests/test_camera_security.py`). This review did not check the NAS: which image runs there, and whether the SSH fix is deployed, are unconfirmed. Still open: the routes have no auth, and `smartgarden-dashboard:broken-37b0157` is still on the NAS.

## What happened
`docker-compose.yml` carried the full Postgres DSN for the `smartgarden` role (host 10.0.0.16:5433) as a literal since 2026-06-04 (`4a98f4b`). This repo is public, so the password was published. A liveness check on 2026-10-22 found it still accepted. The role is not a superuser; it can read and write only the `smartgarden` database (12 tables). It sees no `trading_bot` tables, but like every role it can create tables in `trading_bot_test` (PUBLIC default).

## Fix
- The compose file now reads `DATABASE_URL=${SMARTGARDEN_DATABASE_URL:?...}`. The value lives in the gitignored `deploy-kit/.env.deploy`, which `deploy-kit/lib.sh` stages as `.env` next to the compose file at deploy time. A deploy without it fails fast instead of starting with an empty or wrong DSN. (A plain `${DATABASE_URL}` would have picked up the shared trading DSN from `.env.deploy`.)
- The password is rotated with `ALTER ROLE smartgarden PASSWORD ...`, then the container is recreated (`docker compose up -d --force-recreate`; `docker restart` does not reload env). History is not rewritten: rotation is what makes the published value worthless.

## Resolved tickets
| Ticket | Root cause | Commit |
|---|---|---|
| Live DB password in public compose file | DSN written inline in `docker-compose.yml` | see `git log -- docker-compose.yml` (2026-10-22) |

## Follow-up: the redeploy crash-looped (SQLAlchemy 2.1)
The first image built after the rotation crash-looped with `ModuleNotFoundError: No module named 'psycopg'`. SQLAlchemy was not pinned, so the rebuild pulled 2.1.6, whose default driver for `postgresql://` is psycopg (v3); the image ships psycopg2. The earlier pin pass missed it because its tests ran on SQLite. The NAS was rolled back to the `:previous` image (SQLAlchemy 2.0.51) with the new credential, and `SQLAlchemy==2.0.51` is now pinned (verified: connects to the real database through psycopg2). The broken image is kept on the NAS as `smartgarden-dashboard:broken-37b0157`.

## Follow-up: SSH option injection in camera endpoints
`POST`/`PUT /api/camera/endpoints` stored `ssh_user`/`ssh_host` unvalidated and `camera_service.py` built `user@host` for `ssh`/`scp`, so `ssh_user='-oProxyCommand=...'` ran commands in the container (triggered by `POST /api/camera/endpoints/<id>/test`); `capture_command` ran any stored command on the Pi. Fixed: `validate_ssh_target` (strict user/host patterns, no leading `-`, port 1–65535) and a capture-command allowlist (`DEFAULT_CAPTURE_COMMANDS` plus `CAMERA_CAPTURE_COMMANDS`, `||`-separated) are enforced both in the API (400) and inside every function that shells out; every ssh/scp argv puts `--` before the destination. Tests: `backend/tests/test_camera_security.py`. The routes still have no auth (LAN-only service).
