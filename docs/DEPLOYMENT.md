# Deployment Guide for VPS

## Prerequisites on VPS
- Ubuntu/Debian Linux
- Python 3.8+
- Git
- Nginx (for production)
- Supervisor (for process management)

## Step 1: Clone Repository

```bash
cd /var/www
sudo git clone https://github.com/YOUR_USERNAME/apihub.git
cd apihub
```

## Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Step 3: Configure API Keys

Create config file from template:
```bash
cp config/aisstream_keys.example config/aisstream_keys
nano config/aisstream_keys  # Edit with your actual keys
chmod 600 config/aisstream_keys  # Secure the file
```

## Step 4: Test Locally

```bash
# Test data collector
python ais_collector.py

# Test web tracker (Ctrl+C to stop)
python web_tracker.py
```

## Step 5: Production Setup with Supervisor

Create supervisor config:
```bash
sudo nano /etc/supervisor/conf.d/ais-collector.conf
```

Add:
```ini
[program:ais-collector]
command=/var/www/apihub/venv/bin/python /var/www/apihub/ais_collector.py
directory=/var/www/apihub
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/ais-collector.err.log
stdout_logfile=/var/log/ais-collector.out.log

[program:ais-web-tracker]
command=/var/www/apihub/venv/bin/python /var/www/apihub/web_tracker.py
directory=/var/www/apihub
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/ais-web-tracker.err.log
stdout_logfile=/var/log/ais-web-tracker.out.log
```

Reload supervisor:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start ais-collector
sudo supervisorctl start ais-web-tracker
```

## Step 6: Configure Nginx

Create nginx config:
```bash
sudo nano /etc/nginx/sites-available/ais-tracker
```

Add:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # Change this

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /socket.io {
        proxy_pass http://127.0.0.1:5000/socket.io;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/ais-tracker /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Step 7: SSL with Let's Encrypt (Optional but Recommended)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Step 8: Firewall Configuration

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

## Managing the Services

### Check Status
```bash
sudo supervisorctl status
```

### View Logs
```bash
# Collector logs
sudo tail -f /var/log/ais-collector.out.log
sudo tail -f /var/log/ais-collector.err.log

# Web tracker logs
sudo tail -f /var/log/ais-web-tracker.out.log
sudo tail -f /var/log/ais-web-tracker.err.log
```

### Restart Services
```bash
sudo supervisorctl restart ais-collector
sudo supervisorctl restart ais-web-tracker
```

### Stop Services
```bash
sudo supervisorctl stop ais-collector
sudo supervisorctl stop ais-web-tracker
```

## Database Management

### Backup Database
```bash
cp vessel_static_data.db vessel_static_data.db.backup.$(date +%Y%m%d)
```

### Check Database Size
```bash
du -h vessel_static_data.db
```

### Query Database
```bash
sqlite3 vessel_static_data.db "SELECT COUNT(*) FROM vessels_static;"
```

## Monitoring

### Check if services are running
```bash
ps aux | grep python
```

### Check port usage
```bash
sudo netstat -tulpn | grep :5000
```

### Monitor resource usage
```bash
htop
```

## Troubleshooting

### Service won't start
1. Check logs: `sudo tail -f /var/log/ais-*.log`
2. Check permissions: `ls -la /var/www/apihub`
3. Test manually: `cd /var/www/apihub && source venv/bin/activate && python ais_collector.py`

### Database locked errors
- Make sure only one instance of each script is running
- Check: `sudo supervisorctl status`

### Web interface not accessible
1. Check nginx: `sudo nginx -t && sudo systemctl status nginx`
2. Check Flask is running: `sudo supervisorctl status ais-web-tracker`
3. Check firewall: `sudo ufw status`

## Updating the Application

```bash
cd /var/www/apihub
git pull origin master
source venv/bin/activate
pip install -r requirements.txt
sudo supervisorctl restart ais-collector
sudo supervisorctl restart ais-web-tracker
```

## Security Best Practices

1. **Never commit config/aisstream_keys** - It's in .gitignore
2. **Use SSL** - Set up Let's Encrypt
3. **Restrict database access** - `chmod 600 vessel_static_data.db`
4. **Secure config files** - `chmod 600 config/*_api_key.txt`
5. **Regular backups** - Set up cron job for database backups
5. **Monitor logs** - Check for errors regularly
6. **Update dependencies** - Keep packages up to date

## Performance Optimization

### For large databases (>100,000 vessels):
```bash
# Add indexes
sqlite3 vessel_static_data.db "CREATE INDEX idx_length ON vessels_static(length);"
sqlite3 vessel_static_data.db "CREATE INDEX idx_ship_type ON vessels_static(ship_type);"
```

### Nginx caching (optional):
Add to nginx config:
```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=ais_cache:10m max_size=100m;
proxy_cache ais_cache;
proxy_cache_valid 200 1m;
```

## Access Your Application

- **Web Interface**: http://your-domain.com
- **API Endpoints**:
  - http://your-domain.com/api/vessels
  - http://your-domain.com/api/stats

## Support

For issues, check:
1. Application logs
2. Nginx logs: `/var/log/nginx/error.log`
3. System logs: `sudo journalctl -u supervisor`
