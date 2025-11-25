# 🖥️ ML Service on PC - Hybrid Deployment Guide

## Overview

This setup allows you to:
- **VPS**: Serves the web interface (lightweight, fast)
- **PC**: Runs ML training and predictions (uses your PC's resources)

The VPS automatically proxies ML requests to your PC when configured.

## Architecture

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Browser   │────────▶│     VPS     │────────▶│     PC      │
│  (User)     │         │  (Web UI)   │         │  (ML Service)│
└─────────────┘         └─────────────┘         └─────────────┘
                              │                        │
                              │ Proxies ML requests    │
                              │ to PC                  │
                              │                        │
                              └────────────────────────┘
```

## Setup Instructions

### Step 1: Find Your PC's IP Address

#### Windows:
```powershell
ipconfig
# Look for "IPv4 Address" under your active network adapter
# Example: 192.168.1.100
```

#### Linux/Mac:
```bash
ifconfig
# or
ip addr show
```

**Important**: Use your **local network IP** (usually starts with 192.168.x.x or 10.x.x.x), not your public IP.

### Step 2: Start ML Service on PC

On your PC, run:

```bash
# Navigate to project directory
cd C:\Users\gerrit\Desktop\apihub

# Activate virtual environment (if using one)
# venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies (if not already installed)
pip install flask flask-cors scikit-learn textblob

# Start ML service
python src/services/ml_service_pc.py --host 0.0.0.0 --port 5001
```

**Expected output:**
```
================================================================================
ML PREDICTOR SERVICE (PC)
================================================================================
Starting on http://0.0.0.0:5001
VPS should proxy requests to this address
================================================================================
 * Running on http://0.0.0.0:5001
```

**Keep this terminal open!** The service needs to stay running.

### Step 3: Configure VPS to Use PC

On your VPS, set the environment variable:

```bash
# SSH into VPS
ssh erik@your-vps-ip

# Edit environment file (or add to systemd service)
sudo nano /etc/systemd/system/ais-web-tracker.service
```

Add to the `[Service]` section:
```ini
[Service]
Environment="ML_PC_URL=http://YOUR_PC_IP:5001"
# Example: Environment="ML_PC_URL=http://192.168.1.100:5001"
```

**OR** set it in your shell before starting the service:
```bash
export ML_PC_URL="http://YOUR_PC_IP:5001"
```

### Step 4: Restart VPS Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Restart web tracker
sudo systemctl restart ais-web-tracker

# Check status
sudo systemctl status ais-web-tracker
```

### Step 5: Test Connection

On VPS, test if it can reach your PC:

```bash
# Test from VPS to PC
curl http://YOUR_PC_IP:5001/health

# Should return:
# {"status":"ok","service":"ml-predictor-pc","models_loaded":false}
```

## Firewall Configuration

### Windows Firewall (PC)

Allow incoming connections on port 5001:

1. Open **Windows Defender Firewall**
2. Click **Advanced settings**
3. Click **Inbound Rules** → **New Rule**
4. Select **Port** → **Next**
5. Select **TCP** → Enter port **5001** → **Next**
6. Select **Allow the connection** → **Next**
7. Check all profiles → **Next**
8. Name it "ML Service" → **Finish**

### Router Configuration (If Needed)

If VPS and PC are on different networks, you may need to:
1. Set up port forwarding on your router
2. Use a VPN or tunnel
3. Use a service like ngrok for temporary access

## Usage

### Train Models (Uses PC Resources)

1. Navigate to `/ml-predictions` page on VPS
2. Click "🚀 Train Models"
3. Training happens on your PC (may take a few minutes)
4. Results are returned to VPS and displayed

### View Predictions (Uses PC Resources)

- All prediction requests are automatically proxied to PC
- VPS just forwards the requests/responses
- No ML processing happens on VPS

## Troubleshooting

### "Connection refused" or "Connection timeout"

**Check:**
1. Is ML service running on PC? (Check terminal)
2. Is PC IP address correct?
3. Is Windows Firewall blocking port 5001?
4. Are VPS and PC on the same network?

**Test from PC itself:**
```bash
curl http://localhost:5001/health
```

**Test from VPS:**
```bash
curl http://YOUR_PC_IP:5001/health
```

### "Models not trained" error

1. Make sure you have intelligence and profile data on PC
2. Run training from PC directly first:
   ```bash
   python src/services/ml_predictor_service.py
   ```

### VPS falls back to local ML

If PC is unreachable, VPS will try to use its own ML service (if available). Check VPS logs:
```bash
sudo journalctl -u ais-web-tracker -f
```

## Running ML Service as Windows Service (Optional)

To keep ML service running automatically on PC:

### Option 1: Use Task Scheduler

1. Open **Task Scheduler**
2. Create **Basic Task**
3. Name: "ML Service"
4. Trigger: **When computer starts**
5. Action: **Start a program**
6. Program: `python`
7. Arguments: `C:\Users\gerrit\Desktop\apihub\src\services\ml_service_pc.py --host 0.0.0.0 --port 5001`
8. Start in: `C:\Users\gerrit\Desktop\apihub`

### Option 2: Use NSSM (Non-Sucking Service Manager)

```bash
# Download NSSM from https://nssm.cc/download
# Install service
nssm install MLService "C:\Python\python.exe" "C:\Users\gerrit\Desktop\apihub\src\services\ml_service_pc.py --host 0.0.0.0 --port 5001"
nssm set MLService AppDirectory "C:\Users\gerrit\Desktop\apihub"
nssm start MLService
```

## Security Considerations

⚠️ **Important**: This setup exposes your PC's ML service on your local network.

### Recommendations:

1. **Use VPN**: If VPS and PC are on different networks, use a VPN
2. **Firewall Rules**: Only allow connections from VPS IP
3. **Authentication**: Add API key authentication (future enhancement)
4. **HTTPS**: Use HTTPS if exposing over internet (not recommended)

## Disabling PC Proxy

To use VPS resources instead:

```bash
# On VPS
sudo systemctl edit ais-web-tracker
# Add:
[Service]
Environment="ML_PC_URL="
# (empty value disables proxy)

sudo systemctl restart ais-web-tracker
```

## Monitoring

### Check ML Service Status (PC)

```bash
# Health check
curl http://localhost:5001/health

# Stats
curl http://localhost:5001/stats
```

### Check VPS Proxy Status

```bash
# VPS logs
sudo journalctl -u ais-web-tracker -f | grep -i ml
```

## Performance

- **Training**: Happens on PC (uses PC CPU/RAM)
- **Predictions**: Generated on PC, cached on VPS
- **Network**: Only prediction results are transferred (small JSON)
- **Latency**: ~100-500ms depending on network

## Next Steps

1. Set up automatic startup for ML service on PC
2. Add monitoring/alerting if PC service goes down
3. Consider using a reverse proxy (nginx) on PC
4. Add authentication for security

