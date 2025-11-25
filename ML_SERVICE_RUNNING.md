# ✅ ML Service is Running!

## Status

✅ **ML Service is active on port 5001**
✅ **Health check passed**: `http://localhost:5001/health`

## Your PC IP Address

Run this to find your IP:
```powershell
ipconfig
```

Look for **IPv4 Address** under your active network adapter (usually `192.168.x.x` or `10.x.x.x`)

## Next Steps

### 1. Find Your PC IP
```powershell
ipconfig
# Note the IPv4 Address (e.g., 192.168.1.100)
```

### 2. Configure VPS

SSH into your VPS and run:
```bash
# Edit service file
sudo nano /etc/systemd/system/ais-web-tracker.service

# Add this line in [Service] section:
Environment="ML_PC_URL=http://YOUR_PC_IP:5001"

# Save and restart
sudo systemctl daemon-reload
sudo systemctl restart ais-web-tracker
```

### 3. Test Connection from VPS

On VPS, test if it can reach your PC:
```bash
curl http://YOUR_PC_IP:5001/health
```

Should return: `{"status":"ok","service":"ml-predictor-pc"}`

## Service Endpoints

- **Health**: `http://localhost:5001/health`
- **Predictions**: `http://localhost:5001/predictions`
- **Stats**: `http://localhost:5001/stats`
- **Train**: `POST http://localhost:5001/train`

## Keep Service Running

The service is currently running in the background. To keep it running:

1. **Use the batch file**: `scripts\start_ml_service_pc.bat`
2. **Or run manually**:
   ```bash
   python src/services/ml_service_pc.py --host 0.0.0.0 --port 5001
   ```

## Windows Firewall

Make sure Windows Firewall allows port 5001:
1. Open Windows Defender Firewall
2. Advanced Settings → Inbound Rules → New Rule
3. Port → TCP → 5001 → Allow

## Test It

Once VPS is configured, test from web interface:
- Go to: `https://gerritsxd.com/ships/ml-predictions`
- Click "Train Models" - should use your PC!

