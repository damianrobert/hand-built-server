"""shortly - a tiny URL shortener backed by PostgreSQL."""
import logging
import os
import secrets
import string
from urllib.parse import urlparse

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, url_for
from psycopg import errors
from werkzeug.middleware.proxy_fix import ProxyFix

from . import db

CODE_ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 6
MAX_URL_LENGTH = 2048


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        DATABASE_URL=os.environ.get("DATABASE_URL", "postgresql://shortly_app@localhost/shortly"),
    )
    if config:
        app.config.update(config)

    # Nginx sits in front of us: trust one hop of X-Forwarded-For / -Proto / -Host
    # so generated short links use https://yourdomain instead of http://127.0.0.1.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    db.init_app(app)

    @app.get("/")
    def index():
        with db.connection() as conn:
            links = conn.execute(
                "SELECT code, target_url, clicks, created_at FROM links"
                " ORDER BY created_at DESC LIMIT 20"
            ).fetchall()
        return render_template("index.html", links=links)

    @app.post("/")
    def create_link():
        target = request.form.get("url", "").strip()
        if not is_valid_url(target):
            flash("Please enter a valid http:// or https:// URL.", "error")
            return redirect(url_for("index"))

        code = insert_link(target)
        app.logger.info("created link %s -> %s", code, target)
        flash(url_for("follow", code=code, _external=True), "created")
        return redirect(url_for("index"))

    @app.get("/<code>")
    def follow(code):
        with db.connection() as conn:
            row = conn.execute(
                "UPDATE links SET clicks = clicks + 1 WHERE code = %s RETURNING target_url",
                (code,),
            ).fetchone()
        if row is None:
            abort(404)
        return redirect(row[0], code=302)

    @app.get("/healthz")
    def healthz():
        """Used by the uptime monitor: 200 only if the app *and* the database are fine."""
        try:
            with db.connection() as conn:
                conn.execute("SELECT 1 FROM links LIMIT 1")
        except Exception:
            app.logger.exception("health check failed")
            return jsonify(status="error", database="unreachable"), 503
        return jsonify(status="ok", database="ok")

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("404.html"), 404

    return app


def is_valid_url(value):
    if not value or len(value) > MAX_URL_LENGTH:
        return False
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def insert_link(target, attempts=5):
    for _ in range(attempts):
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        try:
            with db.connection() as conn:
                conn.execute(
                    "INSERT INTO links (code, target_url) VALUES (%s, %s)", (code, target)
                )
            return code
        except errors.UniqueViolation:
            continue
    raise RuntimeError("could not generate a unique short code")
