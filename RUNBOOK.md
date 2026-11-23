# Incident Response Runbook — SRE Cloud Observability Platform

## Service Level Objectives (SLOs)
| SLI | Target SLO | 30-Day Error Budget |
|---|---|---|
| Availability (`non-5xx / total`) | **99.9%** | 43.2 minutes / month |
| Latency (`p95 < 300ms`) | **99.0%** | 1% slow requests |

---

## Playbook 1: `ServiceDown` (Critical)
**Trigger:** `up{job="sre-app"} == 0` for > 30s.

### Immediate Triage Steps
1. Verify container / pod state:
   ```bash
   docker ps -a | grep sre-app
   docker logs --tail=100 sre-app
   ```
2. Check host saturation (CPU, Memory, Disk):
   ```bash
   top -bn1 | head -n 15
   free -h && df -h
   ```
3. Restart or rollback to previous healthy image tag if crash persists.

---

## Playbook 2: `HighErrorRate` (Critical)
**Trigger:** `rate(http_request_errors_total[5m]) > 0.05` for > 1m.

### Immediate Triage Steps
1. Inspect structured JSON logs for `500` responses:
   ```bash
   docker logs sre-app | grep '"500"' | tail -n 30
   ```
2. Check `/metrics` (`app_error_budget_remaining_ratio`) to assess SLO burn rate.
3. If caused by a recent release, execute immediate rollback via CI/CD or Terraform revision traffic split.

---

## Post-Mortem Policy (Blameless)
Every Sev-1 / Sev-2 incident requires a blameless post-mortem within 48 hours documenting:
- Root Cause & Timeline
- Detection Gap (MTTD) & Recovery Time (MTTR)
- Concrete action items to prevent recurrence.
