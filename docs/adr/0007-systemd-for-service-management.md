# ADR-007: Systemd for Service Management

## Status
Accepted

## Context
We need to run multiple background services on the VPS:
- **AIS Collector** - Real-time WebSocket data collection (runs continuously)
- **Atlantic Tracker** - Polled API scans (runs every 6 hours)
- **Web Tracker** - Flask web server (runs continuously)
- **Emissions Matcher** - Background data matching (runs periodically)
- **Econowind Score Updater** - Score recalculation (runs periodically)

Requirements:
- Services must start automatically on boot
- Services must restart automatically on failure
- Services must be manageable (start/stop/restart/status)
- Logs must be accessible
- Services must run as non-root user

## Decision
We use **systemd** for service management on Linux VPS.

### Implementation Details:
- Service files in `config/systemd/`:
  - `ais-collector.service` - AIS data collection
  - `ais-atlantic-tracker.service` - Atlantic coverage
  - `ais-web-tracker.service` - Flask web server
  - `ais-emissions-matcher.service` - Emissions matching
  - `ais-econowind-updater.service` - Score updates
- Timer files for periodic services:
  - `ais-atlantic-tracker.timer` - Runs every 6 hours
  - `ais-emissions-matcher.timer` - Runs every 5 minutes
  - `ais-econowind-updater.timer` - Runs every hour
- Installation: Copy service files to `/etc/systemd/system/`
- User: Services run as `erik` user (non-root)
- Working directory: `/var/www/apihub`
- Logs: Available via `journalctl -u <service-name>`

## Consequences

### Positive:
- ✅ **Standard Linux tool** - Built into all modern Linux distributions
- ✅ **Auto-start on boot** - Services start automatically when VPS reboots
- ✅ **Auto-restart on failure** - `Restart=always` ensures services stay running
- ✅ **Centralized logging** - `journalctl` provides unified log access
- ✅ **Dependency management** - Can specify service dependencies
- ✅ **Resource limits** - Can set memory/CPU limits per service
- ✅ **Status monitoring** - `systemctl status` shows service health

### Negative:
- ❌ **Linux only** - Doesn't work on Windows/Mac (acceptable, VPS is Linux)
- ❌ **Requires root** - Must use `sudo` to install/manage services
- ❌ **Learning curve** - Systemd syntax can be complex
- ❌ **No GUI** - Command-line only (acceptable for server management)

### Trade-offs:
- **Standard over custom**: Systemd is standard, no need for custom init scripts
- **System-level over application-level**: Services managed by OS, not application code
- **Linux-only over cross-platform**: Accepting Linux-only for VPS deployment

## Alternatives Considered

### Supervisor
- **Pros**: Cross-platform, simpler configuration, good for Python apps
- **Cons**: Additional dependency, not standard on Linux
- **Rejected**: Systemd is already available, no need for extra dependency

### Docker Compose
- **Pros**: Containerization, easy deployment, good for development
- **Cons**: Additional complexity, resource overhead, overkill for single VPS
- **Rejected**: Unnecessary complexity for our use case

### Custom init scripts
- **Pros**: Full control, no dependencies
- **Cons**: More code to write/maintain, less standard
- **Rejected**: Systemd provides better features out of the box

### PM2 (Node.js process manager)
- **Pros**: Good for Node.js apps, auto-restart, monitoring
- **Cons**: Designed for Node.js, we're using Python
- **Rejected**: Not suitable for Python services

## Implementation Details

### Service File Example
```ini
[Unit]
Description=AIS Vessel Collector
After=network.target

[Service]
Type=simple
User=erik
WorkingDirectory=/var/www/apihub
ExecStart=/var/www/apihub/venv/bin/python src/collectors/ais_collector.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Timer File Example
```ini
[Unit]
Description=Atlantic Tracker Timer

[Timer]
OnBootSec=5min
OnUnitActiveSec=6h

[Install]
WantedBy=timers.target
```

### Management Commands
```bash
# Install service
sudo systemctl enable ais-collector
sudo systemctl start ais-collector

# Check status
sudo systemctl status ais-collector

# View logs
sudo journalctl -u ais-collector -f

# Restart service
sudo systemctl restart ais-collector
```

## Related ADRs
- ADR-001: SQLite database (services access same database)
- ADR-008: Nginx reverse proxy (proxies to web-tracker service)

## References
- Systemd documentation: https://www.freedesktop.org/software/systemd/man/
- Service files: `config/systemd/*.service`
- Timer files: `config/systemd/*.timer`

