# 🚀 VPS Deployment Steps - ML System

## Quick Deployment

### Step 1: SSH into VPS
```bash
ssh erik@your-vps-ip
```

### Step 2: Navigate and Pull
```bash
cd /var/www/apihub
git pull origin master
```

### Step 3: Install New Dependencies
```bash
source venv/bin/activate
pip install -r config/requirements.txt
```

### Step 4: Build Frontend
```bash
cd frontend
npm install
npm run build
cd ..
```

### Step 5: Restart Services
```bash
sudo systemctl restart ais-web-tracker
sudo systemctl status ais-web-tracker
```

## Optional: Configure ML Proxy to PC

If you want VPS to use your PC for ML:

### Step 1: Get Your PC IP
On your PC, run:
```powershell
ipconfig
# Note your IPv4 Address (e.g., 192.168.1.100)
```

### Step 2: Configure VPS
```bash
# Edit service file
sudo nano /etc/systemd/system/ais-web-tracker.service

# Add this line in [Service] section:
Environment="ML_PC_URL=http://YOUR_PC_IP:5001"

# Save and restart
sudo systemctl daemon-reload
sudo systemctl restart ais-web-tracker
```

### Step 3: Test Connection
```bash
# Test from VPS to PC (replace with your PC IP)
curl http://YOUR_PC_IP:5001/health
```

## Verify Deployment

1. **Check Web Interface**: `https://gerritsxd.com/ships/ml-predictions`
2. **Check API**: `curl http://localhost:5000/ships/api/ml/stats`
3. **Check Logs**: `sudo journalctl -u ais-web-tracker -f`

## Troubleshooting

### If frontend doesn't update:
```bash
cd /var/www/apihub/frontend
rm -rf dist node_modules
npm install
npm run build
sudo systemctl restart ais-web-tracker
```

### If ML endpoints don't work:
- Check if `ML_PC_URL` is set (if using PC proxy)
- Check if PC ML service is running
- Check VPS logs: `sudo journalctl -u ais-web-tracker -n 50`

### If dependencies fail:
```bash
source venv/bin/activate
pip install --upgrade pip
pip install -r config/requirements.txt --force-reinstall
```

