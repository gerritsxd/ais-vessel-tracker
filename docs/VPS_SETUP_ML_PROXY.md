# VPS Setup: ML Proxy to PC

## Step-by-Step Instructions

### Step 1: SSH into Your VPS

```bash
ssh erik@your-vps-ip
# or whatever your VPS username is
```

### Step 2: Navigate to Project Directory

```bash
cd /var/www/apihub
```

### Step 3: Pull Latest Code

```bash
git pull origin main
# or git pull if you're on main branch
```

### Step 4: Get Your PC's IP Address

**On your PC**, run:
```powershell
ipconfig
```

Look for your **IPv4 Address** (usually something like `192.168.1.100` or `10.0.0.50`)

**Important**: You need the IP address of your PC on your local network, not your public IP.

### Step 5: Configure Environment Variable

You have two options:

#### Option A: Set in Systemd Service (Recommended - Persistent)

```bash
# Edit the systemd service file
sudo nano /etc/systemd/system/ais-web-tracker.service
```

Find the `[Service]` section and add:
```ini
[Service]
# ... existing configuration ...
Environment="ML_PC_URL=http://YOUR_PC_IP:5001"
# Example: Environment="ML_PC_URL=http://192.168.1.100:5001"
```

**Save and exit** (Ctrl+X, then Y, then Enter)

#### Option B: Set in Shell (Temporary - Lost on Reboot)

```bash
export ML_PC_URL="http://YOUR_PC_IP:5001"
# Example: export ML_PC_URL="http://192.168.1.100:5001"
```

### Step 6: Reload and Restart Service

```bash
# Reload systemd to pick up changes
sudo systemctl daemon-reload

# Restart the web tracker service
sudo systemctl restart ais-web-tracker

# Check if it started successfully
sudo systemctl status ais-web-tracker
```

**Expected output:**
```
● ais-web-tracker.service - AIS Web Tracker
   Loaded: loaded (/etc/systemd/system/ais-web-tracker.service)
   Active: active (running) since ...
```

### Step 7: Test Connection to PC

**First, make sure ML service is running on your PC!**

Then on VPS, test if it can reach your PC:

```bash
# Replace with your PC's IP
curl http://YOUR_PC_IP:5001/health
```

**Expected response:**
```json
{"status":"ok","service":"ml-predictor-pc","models_loaded":false}
```

If you get `Connection refused` or timeout:
- Check that ML service is running on PC
- Check Windows Firewall allows port 5001
- Verify PC IP address is correct
- Make sure VPS and PC are on the same network (or VPN)

### Step 8: Test ML Proxy from VPS

```bash
# Test if VPS can proxy to PC
curl http://localhost:5000/ships/api/ml/stats
```

Should return ML statistics (even if models aren't trained yet).

### Step 9: Verify in Web Interface

1. Open your website: `https://gerritsxd.com/ships/ml-predictions`
2. Check if it loads (may show "Models not trained" - that's OK)
3. Click "Train Models" - this should now use your PC!

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u ais-web-tracker -n 50

# Look for errors related to ML_PC_URL or proxy
```

### Can't Reach PC

```bash
# Test from VPS
ping YOUR_PC_IP

# If ping works but curl doesn't, check firewall
# On PC, allow port 5001 in Windows Firewall
```

### Proxy Not Working

Check if environment variable is set:
```bash
# Check service environment
sudo systemctl show ais-web-tracker | grep ML_PC_URL

# Should show: ML_PC_URL=http://YOUR_PC_IP:5001
```

### Fallback to VPS ML

If PC is unreachable, VPS will try to use its own ML service. Check logs:
```bash
sudo journalctl -u ais-web-tracker -f | grep -i ml
```

## Quick Reference

### Check Service Status
```bash
sudo systemctl status ais-web-tracker
```

### View Logs
```bash
sudo journalctl -u ais-web-tracker -f
```

### Restart Service
```bash
sudo systemctl restart ais-web-tracker
```

### Disable PC Proxy (Use VPS ML Instead)
```bash
sudo systemctl edit ais-web-tracker
# Add:
[Service]
Environment="ML_PC_URL="
# (empty value disables proxy)

sudo systemctl daemon-reload
sudo systemctl restart ais-web-tracker
```

## Next Steps

1. **On PC**: Start ML service (see `QUICK_START_ML_PC.md`)
2. **On VPS**: Verify connection works
3. **Test**: Train models from web interface - should use PC!

## Notes

- The proxy is **automatic** - once configured, all ML requests go to PC
- If PC is down, VPS will try to use its own ML (if available)
- Environment variable persists across reboots (if set in systemd)
- No code changes needed on VPS - just configuration!

