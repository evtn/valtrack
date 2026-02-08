# TabTrack - Time Series Data Collection API

A simple, dockerized time-series data collection service using FastAPI, InfluxDB, and PostgreSQL.

## Features

- **Push API**: Push (device, section, value) data points
- **Collect API**: Get latest values for all devices/sections
- **Scoped API Keys**: Create keys that can only push to specific device slugs
- **Master Key Management**: Create/list/revoke API keys using a master key
- **Server-Sent Events (SSE)**: Real-time subscriptions for updates
- **Persistent Storage**:
  - InfluxDB: Full time-series history
  - PostgreSQL: API key storage

## Quick Start

```bash
# Set the master key (required for API key management)
export MASTER_KEY=$(openssl rand -hex 32)

# Build and run
docker-compose up --build -d
```

## API Endpoints

### Push Data (requires scoped API key)

```bash
# Get an API key first (see below), then:
curl -X POST http://localhost:8000/push \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"device": "home", "section": "temperature", "value": 22.5}'
```

### Collect Data

```bash
curl http://localhost:8000/collect
```

Returns:
```json
{
  "home": {
    "temperature": {"updated_at": 1707123456, "value": 22.5},
    "humidity": {"updated_at": 1707123457, "value": 45.0}
  }
}
```

### API Key Management (requires master key)

#### Create API Key

```bash
curl -X POST http://localhost:8000/keys \
  -H "Authorization: Bearer $MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"device": "home", "key_id": "home-key-1"}'
```

Response:
```json
{
  "key_id": "home-key-1",
  "api_key": "abc123...",
  "device": "home"
}
```

#### List API Keys

```bash
curl http://localhost:8000/keys \
  -H "Authorization: Bearer $MASTER_KEY"
```

#### Revoke API Key

```bash
curl -X DELETE http://localhost:8000/keys/home-key-1 \
  -H "Authorization: Bearer $MASTER_KEY"
```

### SSE Endpoints

#### Subscribe to specific device:section (values only)

```bash
curl http://localhost:8000/sse/home/temperature
```

Events: `data: 22.5`

#### Subscribe to device (with section info)

```bash
curl http://localhost:8000/sse/home
```

Events: `data: temperature:22.5`

## Architecture

- **FastAPI**: Main application framework
- **InfluxDB**: Time-series database for all metric history
- **PostgreSQL**: Persistent storage for API keys
- **UV**: Fast Python package management and Docker builds

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MASTER_KEY` | Required. Master key for API key management | (required) |
| `INFLUXDB_URL` | InfluxDB connection URL | http://influxdb:8086 |
| `INFLUXDB_TOKEN` | InfluxDB authentication token | tabtrack-secret-token |
| `INFLUXDB_ORG` | InfluxDB organization | tabtrack |
| `INFLUXDB_BUCKET` | InfluxDB bucket for metrics | metrics |
| `DATABASE_URL` | PostgreSQL connection string | postgresql://postgres:postgres@postgres:5432/tabtrack |
