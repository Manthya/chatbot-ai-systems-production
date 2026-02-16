# Phase 4.1: Observability Hardening & Validation

This phase builds upon the foundation of Phase 4.0 by resolving critical integration issues, adding system-level monitoring, and implementing robust alerting.

## 🎯 Objectives
- Resolve port conflicts between Frontend and Grafana.
- Implement missing system-level metrics (CPU, Memory).
- Enable and verify Prometheus alerting rules.
- Fix WebSocket connectivity for accurate frontend observability.
- Automate traffic generation for validation.

## 🔗 Key Differences from Phase 4.0

| Feature | Phase 4.0 (Planned) | Phase 4.1 (Implemented) | Reason |
|---------|---------------------|------------------------|--------|
| **Grafana Port** | `3000` | `3001` | Conflict with Next.js Frontend (default `3000`). |
| **System Metrics** | Basic process metrics | **Full Node Exporter** | Process metrics were insufficient for host-level monitoring. |
| **Alerting** | Planned | **Implemented** | Added `rules.yml` with High Error & Latency alerts. |
| **Frontend WS** | Port `8001` | Port `8000` | Frontend was pointing to wrong backend port for WebSockets. |
| **Database** | `localhost` | `postgres` service | Fixed `ConnectionRefusedError` in Docker network. |

## 🏗️ Architecture Updates

### 1. Expanded Service Stack
Added `node-exporter` to `docker-compose.yml` to scrape kernel-level metrics.

```yaml
  node-exporter:
    image: prom/node-exporter:latest
    ports:
      - "9100:9100"
```

### 2. Alerting Configuration
Implemented `docker/prometheus/rules.yml` with the following active rules:
- **HighErrorRate**: Triggers > 5% failure rate (5xx codes) over 5m.
- **HighLatency**: Triggers if P99 latency > 1s over 5m.

### 3. Grafana Dashboard Enhancements
The "Chatbot Observability" dashboard (`chatbot_overview.json`) now includes a **System Resources** row:
- **CPU Usage**: `rate(node_cpu_seconds_total{mode!="idle"}[1m])`
- **Memory Usage**: `(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100`

## 🛠️ Verification & Usage

### Traffic Generation
A new script `scripts/generate_traffic.py` allows identifying metrics flow:

```bash
# Run generic traffic
python scripts/generate_traffic.py --count 50 --delay 0.5

# Simulate errors for alerting
python scripts/generate_traffic.py --error-rate 0.2
```

### Access Points
- **Grafana**: [http://localhost:3001](http://localhost:3001) (Updated from 3000)
- **Prometheus**: [http://localhost:9090](http://localhost:9090)
- **Visual Evidence**: See `walkthrough.md` for verified dashboards.

## 📋 Completed Tasks
- [x] Moved Grafana to port `3001`.
- [x] Integrated `node-exporter` and configured Prometheus scraping.
- [x] Defined and loaded Prometheus Alerting rules.
- [x] Fixed Frontend WebSocket connection (`ws://localhost:8000`).
- [x] Verified full stack observability (Frontend -> Backend -> Prometheus -> Grafana).
