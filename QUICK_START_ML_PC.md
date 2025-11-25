# 🚀 Quick Start: ML Service on PC

## TL;DR

1. **Start ML service on PC:**
   ```bash
   python src/services/ml_service_pc.py --host 0.0.0.0 --port 5001
   ```

2. **Find your PC IP:**
   ```powershell
   ipconfig
   # Look for IPv4 Address (e.g., 192.168.1.100)
   ```

3. **Configure VPS:**
   ```bash
   # On VPS, set environment variable
   export ML_PC_URL="http://YOUR_PC_IP:5001"
   # Then restart service
   sudo systemctl restart ais-web-tracker
   ```

4. **Done!** VPS now uses your PC for ML.

## Windows Quick Start

Double-click: `scripts/start_ml_service_pc.bat`

Or run in PowerShell:
```powershell
cd C:\Users\gerrit\Desktop\apihub
python src\services\ml_service_pc.py --host 0.0.0.0 --port 5001
```

## Test It

1. Open browser: `http://YOUR_PC_IP:5001/health`
2. Should see: `{"status":"ok","service":"ml-predictor-pc"}`

## Full Guide

See `docs/ML_PC_DEPLOYMENT.md` for detailed instructions.

