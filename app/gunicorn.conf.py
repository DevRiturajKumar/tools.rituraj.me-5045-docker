import os

bind = "0.0.0.0:5045"
workers = int(os.environ.get("GUNICORN_WORKERS", "4"))
worker_class = "sync"
timeout = 120
keepalive = 5

accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")

limit_request_line = 4096
limit_request_fields = 100
