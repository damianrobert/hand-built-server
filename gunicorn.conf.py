# Loaded automatically when gunicorn starts in this directory.
import os

# Localhost only: Nginx is the only public entry point.
bind = os.environ.get("BIND", "127.0.0.1:8000")
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
timeout = 30

# Log to stdout/stderr so systemd's journal captures it (journald rotates it for you).
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info").lower()
