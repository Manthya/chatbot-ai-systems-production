# Phase 4.0: Monitoring & Observability

This phase integrates Prometheus and Grafana for system-wide monitoring, latency tracking, and cache hit/miss observability.

## 🎯 Objectives
- Track LLM latency and token usage.
- Monitor Redis cache hit/miss rates.
- Visualize system health and resource usage (CPU/Memory).
- Set up alerting for service failures.

## 🏗️ Architecture
- **Backend Instrumentation**: FastAPI app exposes metrics at `/metrics`.
- **Prometheus**: Time-series database. Scrapes metrics from backend (`backend:8000`) and Redis Exporter (`redis-exporter:9121`).
- **Grafana**: Dashboarding and visualization.
- **Redis Exporter**: Exports Redis metrics.

## 🚀 Accessing Dashboards

### Prometheus
- **URL**: [http://localhost:9090](http://localhost:9090)
- **Use for**: Debugging raw metrics, checking target health (`Status > Targets`).
- **Key Metrics**:
    - `http_requests_total`: Total request count.
    - `http_request_duration_seconds_bucket`: Latency distribution.
    - `process_cpu_seconds_total`: CPU usage.

### Grafana
- **URL**: [http://localhost:3000](http://localhost:3000)
- **Credentials**: `admin` / `admin` (default)
- **Data Source**: Prometheus is pre-configured.
- **Dashboards**: You can import standard dashboards for:
    - **FastAPI**: ID `16135` (FastAPI Observability)
    - **Redis**: ID `763` (Redis Dashboard for Prometheus Redis Exporter)

## 🛠️ Verification
To verify the stack is running:
1. Check containers: `docker compose ps`
2. Check metrics endpoint: `curl http://localhost:8000/metrics`
3. Check Prometheus targets: `http://localhost:9090/targets`

## ⚙️ Configuration
- **Prometheus**: `docker/prometheus/prometheus.yml`
- **Grafana Datasources**: `docker/grafana/provisioning/datasources/datasource.yml`

## 📋 Completed Tasks
- [x] Add Prometheus & Grafana to `docker-compose.yml`.
- [x] Implement custom metrics in `src/chatbot_ai_system/server/main.py`.
- [x] Create a Grafana dashboard for chat performance.
- [x] Track Redis hit/miss rates in caching layers.
