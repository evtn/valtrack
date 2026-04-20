# Valtrack

Valtrack is a simple tracker for anything numeric.

Built on top of Postgres/TimescaleDB (bring your own instance or just use the one in compose file), Valtrack allows you to:

- Push any float into the database under a two-level key (device-section or item-field, whatever naming works for you)
- Collect devices/items, sections/fields or just everything at once, as a one-time GET request or as a stream via SSE
- Browse push history for any specific item
- Set up scoped API access, optionally restricting read/write/history/admin actions and/or specific device/sections

And with that you can mostly do anything you want.

## Quick Start (Docker Compose)

1. Copy contents of repo docker-compose.yml into any empty folder where you want to set up valtrack (e.g. valtrack):

```bash
wget https://raw.githubusercontent.com/evtn/valtrack/refs/heads/lord/docker-compose.yml
```

2. Create `.env` file with a random `MASTER_KEY`:

```bash
echo "MASTER_KEY=$(openssl rand -hex 32)" > .env
```

(optionally you can set up PORT environment variable to start API on non-default port, by default it's 17548)

3. Start the services:
   ```bash
   docker compose up -d
   ```

The API will be available at http://localhost:17548 (or the port specified in `.env`).

## Authentication

All endpoints require Bearer token authentication. Use your `MASTER_KEY` as the token for admin operations, or create scoped API keys for limited access.

```bash
# Using master key for admin operations
curl -H "Authorization: Bearer $MASTER_KEY" http://localhost:17548/admin/keys
```

## API Overview

Swagger page is available at http://localhost:17548/docs

### Push Data

Push a numeric value for a specific device and section:

```bash
curl -X POST http://localhost:17548/push \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"device": "sensor1", "section": "temperature", "value": 23.5}'
```

Use `forcepush: true` to store duplicate values (by default, identical consecutive values are skipped).

### Collect Data

Get the latest values for all devices:

```bash
curl -H "Authorization: Bearer $API_KEY" http://localhost:17548/items/
```

Get values for a specific device:

```bash
curl -H "Authorization: Bearer $API_KEY" http://localhost:17548/items/device/sensor1
```

Get values for a specific section across all devices:

```bash
curl -H "Authorization: Bearer $API_KEY" http://localhost:17548/items/section/temperature
```

### Get History

Browse historical values for a specific device/section:

```bash
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:17548/items/history?device=sensor1&section=temperature&limit=100&offset=0"
```

### Server-Sent Events (SSE)

Subscribe to real-time updates:

```bash
# Subscribe to all updates
curl -H "Authorization: Bearer $API_KEY" http://localhost:17548/sse

# Subscribe to specific device
curl -H "Authorization: Bearer $API_KEY" "http://localhost:17548/sse?device=sensor1"

# Subscribe to specific device and section
curl -H "Authorization: Bearer $API_KEY" "http://localhost:17548/sse?device=sensor1&section=temperature"
```

Use wildcards (`*`) for broader subscriptions. The SSE endpoint streams JSON events with `device`, `section`, `value`, `author`, and `updated_at` fields.

## API Key Management

### Create a New API Key (Admin only)

```bash
curl -X POST http://localhost:17548/admin/key \
  -H "Authorization: Bearer $MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "key_id": "my-sensor-key",
    "devices": ["sensor1", "sensor2"],
    "sections": ["temperature", "humidity"],
    "permissions": ["read", "write"]
  }'
```

Permissions can be: `read`, `write`, `history`, `admin`.
Use `["*"]` for devices or sections to allow access to all.

### List All API Keys (Admin only)

```bash
curl -H "Authorization: Bearer $MASTER_KEY" http://localhost:17548/admin/keys
```

### Get Current Key Info

```bash
curl -H "Authorization: Bearer $API_KEY" http://localhost:17548/keys/
```

### Revoke an API Key

Revoke your own key:

```bash
curl -X DELETE -H "Authorization: Bearer $API_KEY" http://localhost:17548/keys/
```

Revoke any key (Admin only):

```bash
curl -X DELETE "http://localhost:17548/admin/key?key_id=my-sensor-key" \
  -H "Authorization: Bearer $MASTER_KEY"
```

## Example Scripts

### Bash: Push CPU temperature

```bash
#!/bin/bash
API_KEY="your-api-key"
DEVICE="$(hostname)"
SECTION="cpu_temp"

while true; do
  TEMP=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null | awk '{print $1/1000}')
  if [ -n "$TEMP" ]; then
    curl -s -X POST http://localhost:17548/push \
      -H "Authorization: Bearer $API_KEY" \
      -H "Content-Type: application/json" \
      -d "{\"device\": \"$DEVICE\", \"section\": \"$SECTION\", \"value\": $TEMP}"
  fi
  sleep 60
done
```

### Python: Push and monitor

```python
import requests

API_KEY = "your-api-key"
BASE_URL = "http://localhost:17548"
headers = {"Authorization": f"Bearer {API_KEY}"}

# Push a value
requests.post(
    f"{BASE_URL}/push",
    headers=headers,
    json={"device": "server1", "section": "load", "value": 0.75}
)

# Get latest values
response = requests.get(f"{BASE_URL}/items/", headers=headers)
print(response.json())
```

## Data Model

Valtrack stores time-series data with the following structure:

- **device**: A grouping identifier (e.g., hostname, sensor ID, room name)
- **section**: A field identifier within the device (e.g., temperature, cpu_load, humidity)
- **value**: The numeric (float) value being tracked
- **timestamp**: When the value was recorded (UTC)
- **pushed_by**: The API key ID that pushed the value

## Development

The project uses:
- **FastAPI** for the web framework
- **SQLAlchemy** with async PostgreSQL support
- **TimescaleDB** for efficient time-series storage
- **uv** for dependency management

Run locally (requires Python 3.14+):

```bash
uv sync
uv run main.py --help
```
