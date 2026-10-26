"""Connection pool shared by all requests in a worker process."""
from contextlib import contextmanager

from psycopg_pool import ConnectionPool

_pool = None


def init_app(app):
    global _pool
    # open=False + lazy open: the app still starts (and /healthz can report 503)
    # when Postgres is down, instead of crashing at boot.
    _pool = ConnectionPool(
        app.config["DATABASE_URL"],
        min_size=1,
        max_size=5,
        open=False,
        timeout=5,
        kwargs={"connect_timeout": 3},
    )


@contextmanager
def connection():
    if _pool.closed:
        _pool.open(wait=False)
    # Commits on success, rolls back on exception, returns the connection to the pool.
    with _pool.connection() as conn:
        yield conn
