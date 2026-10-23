# Database credential out of the public compose file (2026-10-22)

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
