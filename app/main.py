#!/usr/bin/env python3
"""
SRE Cloud Observability Service
Demonstrates production SRE patterns:
- Liveness (/health) and Readiness (/ready) probes for Kubernetes / Cloud Run
- Native Prometheus /metrics exposition (Golden Signals: Traffic, Errors, Latency, Saturation)
- Chaos Engineering endpoints (/simulate/error, /simulate/slow) to validate Alerting & Error Budgets
"""
import json
import os
import time
import threading
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

START_TIME = time.time()
LOCK = threading.Lock()

METRICS = {
    "requests_total": {},  # (method, path, status) -> count
    "errors_total": 0,
    "latency_sum": 0.0,
    "latency_count": 0,
    "ready": True,
}

SLO_TARGET = 0.999  # 99.9% availability SLO


def record_metric(method: str, path: str, status: int, duration_s: float) -> None:
    with LOCK:
        key = (method, path, str(status))
        METRICS["requests_total"][key] = METRICS["requests_total"].get(key, 0) + 1
        if status >= 500:
            METRICS["errors_total"] += 1
        METRICS["latency_sum"] += duration_s
        METRICS["latency_count"] += 1


def render_prometheus_metrics() -> str:
    uptime = time.time() - START_TIME
    with LOCK:
        total_reqs = sum(METRICS["requests_total"].values())
        errors = METRICS["errors_total"]
        lat_sum = METRICS["latency_sum"]
        lat_cnt = METRICS["latency_count"]
        ready_val = 1 if METRICS["ready"] else 0
        req_items = list(METRICS["requests_total"].items())

    # Calculate current availability SLI & Error Budget remaining
    sli = 1.0 if total_reqs == 0 else max(0.0, (total_reqs - errors) / total_reqs)
    allowed_error_rate = 1.0 - SLO_TARGET
    actual_error_rate = 0.0 if total_reqs == 0 else errors / total_reqs
    budget_remaining = max(0.0, 1.0 - (actual_error_rate / allowed_error_rate)) if allowed_error_rate > 0 else 1.0

    lines = [
        "# HELP app_uptime_seconds Total uptime of the SRE service in seconds.",
        "# TYPE app_uptime_seconds gauge",
        f"app_uptime_seconds {uptime:.2f}",
        "# HELP app_ready_status Readiness probe state (1=ready, 0=draining).",
        "# TYPE app_ready_status gauge",
        f"app_ready_status {ready_val}",
        "# HELP app_sli_availability_ratio Current availability SLI ratio (0..1).",
        "# TYPE app_sli_availability_ratio gauge",
        f"app_sli_availability_ratio {sli:.6f}",
        "# HELP app_error_budget_remaining_ratio Remaining SLO error budget ratio (0..1).",
        "# TYPE app_error_budget_remaining_ratio gauge",
        f"app_error_budget_remaining_ratio {budget_remaining:.6f}",
        "# HELP http_request_errors_total Total number of HTTP 5xx errors.",
        "# TYPE http_request_errors_total counter",
        f"http_request_errors_total {errors}",
        "# HELP http_request_duration_seconds_sum Total HTTP request duration in seconds.",
        "# TYPE http_request_duration_seconds_sum counter",
        f"http_request_duration_seconds_sum {lat_sum:.6f}",
        "# HELP http_request_duration_seconds_count Total number of timed HTTP requests.",
        "# TYPE http_request_duration_seconds_count counter",
        f"http_request_duration_seconds_count {lat_cnt}",
        "# HELP http_requests_total Total HTTP requests by method, path, and status.",
        "# TYPE http_requests_total counter",
    ]
    for (method, path, status), count in sorted(req_items):
        lines.append(
            f'http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
        )
    return "\n".join(lines) + "\n"


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>sre-cloud-observability-platform</title>
<style>
  :root {
    --bg: #fafafa;
    --surface: #ffffff;
    --border: #e4e4e7;
    --text: #18181b;
    --muted: #71717a;
    --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", sans-serif;
    font-size: 13px;
    line-height: 1.5;
    padding: 36px 24px;
  }
  .wrap { max-width: 940px; margin: 0 auto; }
  header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    border-bottom: 1px solid var(--border);
    padding-bottom: 14px;
    margin-bottom: 24px;
  }
  h1 { font-size: 16px; font-weight: 600; font-family: var(--mono); letter-spacing: -0.02em; color: var(--text); }
  .meta { color: var(--muted); font-family: var(--mono); font-size: 12px; }
  .metrics-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
    background: var(--surface);
    margin-bottom: 20px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
  }
  .metric {
    padding: 16px 18px;
    border-right: 1px solid var(--border);
  }
  .metric:last-child { border-right: none; }
  .metric-label { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; font-weight: 500; }
  .metric-val { font-family: var(--mono); font-size: 20px; font-weight: 600; margin-top: 4px; color: var(--text); }
  .toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 22px;
  }
  button, a.cmd {
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 6px 12px;
    font-family: var(--mono);
    font-size: 12px;
    cursor: pointer;
    text-decoration: none;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
    transition: border-color 0.12s, background 0.12s;
  }
  button:hover, a.cmd:hover { border-color: #a1a1aa; background: #f4f4f5; }
  .section-title {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
    margin-bottom: 8px;
    font-family: var(--mono);
  }
  pre {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px 18px;
    overflow-x: auto;
    font-family: var(--mono);
    font-size: 12px;
    line-height: 1.65;
    color: #27272a;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
  }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>sre-cloud-observability-platform</h1>
    <div class="meta">SLO 99.9% &middot; Prometheus /metrics &middot; europe-west1</div>
  </header>

  <div class="metrics-row">
    <div class="metric"><div class="metric-label">Status</div><div class="metric-val" id="healthVal">--</div></div>
    <div class="metric"><div class="metric-label">Availability SLI</div><div class="metric-val" id="sliVal">--</div></div>
    <div class="metric"><div class="metric-label">5xx Errors</div><div class="metric-val" id="errVal">0</div></div>
    <div class="metric"><div class="metric-label">Uptime</div><div class="metric-val" id="upVal">0s</div></div>
  </div>

  <div class="toolbar">
    <button onclick="hit('/api/orders')">GET /api/orders</button>
    <button onclick="hit('/simulate/slow')">GET /simulate/slow</button>
    <button onclick="hit('/simulate/error')">GET /simulate/error</button>
    <a class="cmd" href="/metrics" target="_blank">/metrics</a>
    <a class="cmd" href="/health" target="_blank">/health</a>
    <a class="cmd" href="/ready" target="_blank">/ready</a>
  </div>

  <div class="section-title">Prometheus Exposition (/metrics)</div>
  <pre id="metricsBox">loading...</pre>
</div>
<script>
async function refresh() {
  const h = await fetch('/health').then(r => r.json());
  document.getElementById('healthVal').textContent = h.status;
  document.getElementById('upVal').textContent = Math.floor(h.uptime_seconds) + 's';
  const m = await fetch('/metrics').then(r => r.text());
  document.getElementById('metricsBox').textContent = m;
  const sli = m.match(/app_sli_availability_ratio ([0-9.]+)/);
  if (sli) document.getElementById('sliVal').textContent = (parseFloat(sli[1]) * 100).toFixed(2) + '%';
  const err = m.match(/http_request_errors_total ([0-9]+)/);
  if (err) document.getElementById('errVal').textContent = err[1];
}
async function hit(path) { await fetch(path); refresh(); }
refresh();
setInterval(refresh, 3000);
</script>
</body>
</html>
"""


class SREHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Structured JSON access logging (SRE best practice for Loki / Cloud Logging)
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "level": "INFO",
            "client_ip": self.client_address[0],
            "request": self.requestline,
            "message": fmt % args,
        }
        print(json.dumps(log_entry), flush=True)

    def _send(self, status: int, content_type: str, body: bytes, path_label: str, start_t: float):
        duration = time.time() - start_t
        record_metric(self.command, path_label, status, duration)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        start_t = time.time()
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/":
            self._send(200, "text/html; charset=utf-8", DASHBOARD_HTML.encode("utf-8"), "/", start_t)
            return

        if path == "/health":
            payload = {
                "status": "healthy",
                "service": "sre-cloud-observability-platform",
                "uptime_seconds": round(time.time() - START_TIME, 2),
                "pid": os.getpid(),
            }
            self._send(200, "application/json", json.dumps(payload).encode("utf-8"), "/health", start_t)
            return

        if path == "/ready":
            if METRICS["ready"]:
                self._send(200, "application/json", b'{"ready":true}', "/ready", start_t)
            else:
                self._send(503, "application/json", b'{"ready":false}', "/ready", start_t)
            return

        if path == "/metrics":
            body = render_prometheus_metrics().encode("utf-8")
            self._send(200, "text/plain; version=0.0.4; charset=utf-8", body, "/metrics", start_t)
            return

        if path == "/api/orders":
            payload = {"status": "ok", "orders_processed": 42, "region": os.getenv("CLOUD_REGION", "europe-west1")}
            self._send(200, "application/json", json.dumps(payload).encode("utf-8"), "/api/orders", start_t)
            return

        if path == "/simulate/slow":
            time.sleep(1.2)
            payload = {"status": "slow_response", "injected_latency_seconds": 1.2}
            self._send(200, "application/json", json.dumps(payload).encode("utf-8"), "/simulate/slow", start_t)
            return

        if path == "/simulate/error":
            payload = {"status": "error", "detail": "Simulated 500 internal failure for SRE alerting test"}
            self._send(500, "application/json", json.dumps(payload).encode("utf-8"), "/simulate/error", start_t)
            return

        self._send(404, "application/json", b'{"error":"not_found"}', "/404", start_t)


def run_server(host: str = "0.0.0.0", port: int = None):
    port = port or int(os.getenv("PORT", "8080"))
    server = ThreadingHTTPServer((host, port), SREHandler)
    print(json.dumps({"level": "INFO", "event": "startup", "host": host, "port": port}), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    run_server()
