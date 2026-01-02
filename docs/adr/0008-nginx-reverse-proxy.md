# ADR-008: Nginx Reverse Proxy for Production

## Status
Accepted

## Context
We need to serve the Flask web application in production:
- Flask runs on `localhost:5000` (not exposed to internet)
- Need HTTPS support (SSL certificates)
- Need to handle WebSocket upgrades (Socket.IO)
- Need to serve static files efficiently
- Need to handle `/ships/` path prefix
- Need proper headers (X-Forwarded-For, etc.)

Flask's built-in development server is not suitable for production (single-threaded, no HTTPS, security issues).

## Decision
We use **Nginx as a reverse proxy** in front of Flask.

### Implementation Details:
- Nginx listens on port 80/443 (public-facing)
- Proxies requests to Flask on `localhost:5000`
- Handles WebSocket upgrades for Socket.IO (`/ships/socket.io/`)
- Serves static files directly (more efficient than Flask)
- Path prefix: `/ships/` for all routes
- SSL: Let's Encrypt certificates (via Certbot)
- Headers: Properly forwards X-Forwarded-For, Host, etc.

### Nginx Configuration:
```nginx
server {
    listen 80;
    server_name gerritsxd.com;
    
    location /ships/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Consequences

### Positive:
- ✅ **Production-ready** - Nginx is battle-tested, handles high concurrency
- ✅ **HTTPS support** - Easy SSL certificate management with Let's Encrypt
- ✅ **WebSocket support** - Properly handles Socket.IO WebSocket upgrades
- ✅ **Static file serving** - Can serve static files directly (faster than Flask)
- ✅ **Security** - Hides Flask server from direct internet access
- ✅ **Performance** - Better performance than Flask's dev server
- ✅ **Standard practice** - Common pattern for Python web apps

### Negative:
- ❌ **Additional component** - Another service to manage and configure
- ❌ **Configuration complexity** - Nginx config can be complex
- ❌ **SSL certificate management** - Must renew certificates periodically

### Trade-offs:
- **Security over simplicity**: Nginx adds complexity but provides better security
- **Performance over convenience**: Nginx is faster but requires more setup
- **Standard over custom**: Using standard reverse proxy pattern

## Alternatives Considered

### Flask directly on port 80
- **Pros**: Simpler setup, no Nginx needed
- **Cons**: Not production-ready, security issues, no HTTPS, poor performance
- **Rejected**: Not suitable for production deployment

### Gunicorn/uWSGI behind Nginx
- **Pros**: Better performance, handles multiple workers
- **Cons**: More complex setup, Socket.IO needs special configuration
- **Rejected**: Flask-SocketIO works fine with single process, Gunicorn adds complexity

### Apache mod_wsgi
- **Pros**: Alternative to Nginx
- **Cons**: Less common for Python apps, more complex configuration
- **Rejected**: Nginx is more standard for Python web apps

### Cloudflare/Cloud provider load balancer
- **Pros**: Managed service, DDoS protection
- **Cons**: Cost, vendor lock-in, overkill for single VPS
- **Rejected**: Unnecessary for our scale

## Implementation Details

### Flask Configuration
- Flask uses `ProxyFix` middleware to handle X-Forwarded-For headers
- Socket.IO path: `/ships/socket.io` (matches Nginx location)
- Flask runs on `localhost:5000` (not exposed to internet)

### Nginx Configuration Location
- Production: `/etc/nginx/sites-available/ais-tracker`
- Symlink: `/etc/nginx/sites-enabled/ais-tracker`
- Test config: `sudo nginx -t`
- Reload: `sudo systemctl reload nginx`

### SSL Certificate (Let's Encrypt)
```bash
sudo certbot --nginx -d gerritsxd.com
```
- Auto-renewal: Certbot sets up cron job
- Certificates stored: `/etc/letsencrypt/live/gerritsxd.com/`

## Related ADRs
- ADR-002: Flask backend (proxied by Nginx)
- ADR-007: Systemd services (runs Flask service)

## References
- Nginx documentation: https://nginx.org/en/docs/
- Flask-SocketIO deployment: https://flask-socketio.readthedocs.io/en/latest/deployment.html
- Let's Encrypt: https://letsencrypt.org/

