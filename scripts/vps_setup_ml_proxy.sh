#!/bin/bash
# VPS Setup Script for ML Proxy to PC
# Run this on your VPS to configure ML proxy

set -e

echo "================================================================================"
echo "VPS ML Proxy Setup"
echo "================================================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Please run with sudo"
    exit 1
fi

# Get PC IP from user
echo "Enter your PC's IP address (e.g., 192.168.1.100):"
read PC_IP

if [ -z "$PC_IP" ]; then
    echo "❌ PC IP address is required"
    exit 1
fi

ML_PC_URL="http://${PC_IP}:5001"

echo ""
echo "Setting ML_PC_URL to: $ML_PC_URL"
echo ""

# Check if service file exists
SERVICE_FILE="/etc/systemd/system/ais-web-tracker.service"

if [ ! -f "$SERVICE_FILE" ]; then
    echo "⚠️  Service file not found: $SERVICE_FILE"
    echo "   Please create the service file first or set environment variable manually"
    exit 1
fi

# Backup service file
cp "$SERVICE_FILE" "${SERVICE_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
echo "✓ Backed up service file"

# Check if Environment line already exists
if grep -q "ML_PC_URL" "$SERVICE_FILE"; then
    # Update existing line
    sed -i "s|Environment=\"ML_PC_URL=.*\"|Environment=\"ML_PC_URL=${ML_PC_URL}\"|" "$SERVICE_FILE"
    echo "✓ Updated existing ML_PC_URL"
else
    # Add new line in [Service] section
    sed -i "/\[Service\]/a Environment=\"ML_PC_URL=${ML_PC_URL}\"" "$SERVICE_FILE"
    echo "✓ Added ML_PC_URL to service file"
fi

# Reload systemd
echo ""
echo "Reloading systemd..."
systemctl daemon-reload
echo "✓ Systemd reloaded"

# Restart service
echo ""
echo "Restarting ais-web-tracker service..."
systemctl restart ais-web-tracker
echo "✓ Service restarted"

# Check status
echo ""
echo "Checking service status..."
sleep 2
systemctl status ais-web-tracker --no-pager -l

# Test connection
echo ""
echo "================================================================================"
echo "Testing connection to PC..."
echo "================================================================================"

if curl -s --max-time 5 "http://${PC_IP}:5001/health" > /dev/null; then
    echo "✅ Successfully connected to PC ML service!"
    echo ""
    curl -s "http://${PC_IP}:5001/health" | python3 -m json.tool
else
    echo "⚠️  Could not connect to PC ML service"
    echo ""
    echo "Troubleshooting:"
    echo "1. Make sure ML service is running on PC:"
    echo "   python src/services/ml_service_pc.py --host 0.0.0.0 --port 5001"
    echo ""
    echo "2. Check Windows Firewall allows port 5001"
    echo ""
    echo "3. Verify PC IP address is correct: $PC_IP"
    echo ""
    echo "4. Test from PC itself:"
    echo "   curl http://localhost:5001/health"
fi

echo ""
echo "================================================================================"
echo "Setup Complete!"
echo "================================================================================"
echo ""
echo "Next steps:"
echo "1. Make sure ML service is running on your PC"
echo "2. Test from web interface: https://gerritsxd.com/ships/ml-predictions"
echo "3. Check logs: sudo journalctl -u ais-web-tracker -f"
echo ""

