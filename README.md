# shortly

A tiny URL shortener: paste a long URL, get a short link and a click counter.
Flask + PostgreSQL, served by gunicorn on `127.0.0.1:8000` behind Nginx.

> This README covers **the app only**. The server runbook (Nginx, TLS, firewall,
> systemd, backups, monitoring, Break It notes) belongs in its own section/file.

## Endpoints

| Method | Path       | What it does                                              |
|--------|------------|-----------------------------------------------------------|
| GET    | `/`        | Form + 20 most recent links                               |
| POST   | `/`        | Create a short link (`url` form field, http/https only)   |
| GET    | `/<code>`  | 302 redirect to the target, increments `clicks`           |
| GET    | `/healthz` | `200 {"status":"ok"}` if app + DB are fine, else `503`    |

Point your external uptime monitor at `https://yourdomain/healthz`. It fails
when the database is down too, not only when the app is.

## Configuration (environment variables)

| Variable          | Default                                        | Notes                         |
|-------------------|------------------------------------------------|-------------------------------|
| `DATABASE_URL`    | `postgresql://shortly_app@localhost/shortly`   | libpq connection string       |
| `SECRET_KEY`      | `dev-only-change-me`                           | **Set in production**         |
| `BIND`            | `127.0.0.1:8000`                               | Keep it on localhost          |
| `WEB_CONCURRENCY` | `2`                                            | gunicorn worker count         |
| `LOG_LEVEL`       | `INFO`                                         |                               |

See `.env.example`. Logs go to stdout/stderr, so under systemd they land in
`journalctl -u shortly`.

## Database setup (least privilege)

```bash
sudo -u postgres createdb shortly
sudo -u postgres psql -c "CREATE ROLE shortly_app LOGIN PASSWORD 'strong-password';"
sudo -u postgres psql -d shortly -f db/schema.sql   # tables, owned by postgres
sudo -u postgres psql -d shortly -f db/grants.sql   # SELECT/INSERT/UPDATE only
```

The app role can't delete rows, alter the schema or create tables. Check it:

```bash
psql "postgresql://shortly_app:...@127.0.0.1/shortly" -c "DROP TABLE links;"   # -> permission denied
```

Backups: `pg_dump -Fc shortly > shortly-$(date +%F).dump` (run as `postgres`).
Restore into a fresh DB: `createdb shortly_restore && pg_restore -d shortly_restore file.dump`.

## Install & run

```bash
sudo apt install python3-venv python3-pip      # Ubuntu/Debian
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export DATABASE_URL=postgresql://shortly_app:strong-password@127.0.0.1/shortly
.venv/bin/gunicorn wsgi:app                    # reads gunicorn.conf.py
curl -s localhost:8000/healthz
```

Example systemd `ExecStart` (with `WorkingDirectory=` set to the checkout):
`/opt/shortly/.venv/bin/gunicorn wsgi:app`

## Tests

```bash
.venv/bin/pip install pytest
.venv/bin/pytest                                # DB tests skipped
TEST_DATABASE_URL=postgresql://...@127.0.0.1/shortly_test .venv/bin/pytest
```

## Handy for Break It drills

- Kill it: `sudo systemctl kill -s KILL shortly`. systemd should restart it.
- Stop Postgres: `/healthz` returns 503 and your uptime check should alert.
- Wrong password in the env file: app starts, `/healthz` 503, auth error in the journal.
- Stop the app: Nginx returns 502 Bad Gateway.
