# SRE Cloud Observability & DevOps Platform

Production-grade **Site Reliability Engineering (SRE) & DevOps** reference architecture built by **Sohaib Ghaberit**.

Demonstrates end-to-end reliability engineering practices:
- **Four Golden Signals & Observability:** Native Prometheus `/metrics` exposition tracking Traffic, Errors, Latency, Availability SLI, and real-time Error Budget remaining.
- **Liveness & Readiness Probes:** `/health` and `/ready` endpoints designed for Kubernetes / Google Cloud Run zero-downtime deployments.
- **Chaos Engineering Endpoints:** `/simulate/error` (500 injection) and `/simulate/slow` (latency injection) to validate alerting rules.
- **Hardened Containerization:** Non-root multi-stage `Dockerfile` with built-in `HEALTHCHECK` + full `docker-compose.yml` stack (`App + Prometheus + Grafana`).
- **CI/CD Automation:** GitHub Actions pipeline running automated `unittest` checks, Docker image build + live container smoke test, and `terraform validate`.
- **Infrastructure as Code (IaC):** Terraform configuration (`terraform/main.tf`) provisioning Google Cloud Run with auto-scaling, health probes, and Cloud Monitoring Uptime Checks.
- **Incident Response:** Production `RUNBOOK.md` with SLO/SLI definitions and triage playbooks.

## Architecture

```
                 +-----------------------------+
                 |   GitHub Actions CI/CD      |
                 | Tests -> Docker -> Terraform|
                 +--------------+--------------+
                                |
                                v
+-----------+    /health    +---+--------------------+    /metrics    +------------+    Dashboards    +---------+
|  Clients  +-------------->+  SRE Python Service    +<---------------+ Prometheus +------------------>+ Grafana |
+-----------+  /api/orders  | (Non-root Docker/Cloud)|   Alert Rules  +------------+                   +---------+
                            +------------------------+
```

## Quick Start

### Run Locally (Python)
```bash
python3 -m unittest discover -s tests -v
python3 -m app.main
# Open http://localhost:8080
```

### Run Full SRE Stack (Docker + Prometheus + Grafana)
```bash
docker compose up --build
# App Dashboard: http://localhost:8080
# Prometheus:    http://localhost:9090
# Grafana:       http://localhost:3000 (admin / admin)
```

---
**Author:** Sohaib Ghaberit — Full-Stack, Data/IA & DevOps/SRE Engineer  
GitHub: https://github.com/ghaberitsohaib
