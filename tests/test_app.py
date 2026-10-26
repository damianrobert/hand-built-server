"""Run with: pytest

Tests marked `needs_db` require a real Postgres. Point TEST_DATABASE_URL at a
throwaway database that already has db/schema.sql applied, or they are skipped.
"""
import os

import pytest

from shortly import create_app, is_valid_url

TEST_DB = os.environ.get("TEST_DATABASE_URL")
needs_db = pytest.mark.skipif(not TEST_DB, reason="TEST_DATABASE_URL not set")


@pytest.mark.parametrize(
    "url,ok",
    [
        ("https://example.com", True),
        ("http://example.com/path?q=1", True),
        ("ftp://example.com", False),
        ("javascript:alert(1)", False),
        ("example.com", False),
        ("", False),
        ("https://" + "a" * 3000, False),
    ],
)
def test_is_valid_url(url, ok):
    assert is_valid_url(url) is ok


def test_healthz_reports_503_when_db_is_down():
    app = create_app({"DATABASE_URL": "postgresql://nobody@127.0.0.1:1/nope"})
    resp = app.test_client().get("/healthz")
    assert resp.status_code == 503
    assert resp.get_json()["database"] == "unreachable"


@pytest.fixture
def client():
    app = create_app({"DATABASE_URL": TEST_DB, "TESTING": True})
    return app.test_client()


@needs_db
def test_healthz_ok(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok", "database": "ok"}


@needs_db
def test_create_and_follow_link(client):
    resp = client.post("/", data={"url": "https://example.com/hello"})
    assert resp.status_code == 302

    page = client.get("/").get_data(as_text=True)
    assert "https://example.com/hello" in page

    from shortly import db
    with db.connection() as conn:
        code, clicks = conn.execute(
            "SELECT code, clicks FROM links WHERE target_url = %s ORDER BY id DESC LIMIT 1",
            ("https://example.com/hello",),
        ).fetchone()

    resp = client.get(f"/{code}")
    assert resp.status_code == 302
    assert resp.headers["Location"] == "https://example.com/hello"

    with db.connection() as conn:
        (new_clicks,) = conn.execute("SELECT clicks FROM links WHERE code = %s", (code,)).fetchone()
    assert new_clicks == clicks + 1


@needs_db
def test_unknown_code_is_404(client):
    assert client.get("/doesnotexist").status_code == 404


@needs_db
def test_invalid_url_is_rejected(client):
    resp = client.post("/", data={"url": "not a url"}, follow_redirects=True)
    assert "valid http" in resp.get_data(as_text=True)
