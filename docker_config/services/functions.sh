#!/bin/bash -e

start_tcp_receiver() {
  echo "[*] Starting gevent flag receiver"
  cd services/tcp_receiver
  python3 server.py
}

start_web() {
  echo "[*] Starting web service $1"
  cd "services/$1"
  gunicorn "app:app" \
    --bind "0.0.0.0:${PORT:-5000}" \
    --log-level INFO \
    --worker-class eventlet \
    --worker-connections 1024
}

start_api() {
  start_web api
}

start_admin() {
  start_web admin
}

start_events() {
  start_web events
}

start_monitoring() {
  start_web monitoring
}

start_http_receiver() {
  start_web http_receiver
}
