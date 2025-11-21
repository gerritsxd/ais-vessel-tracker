#!/bin/bash
# Deploy script for VPS after restructuring

echo "=========================================="
echo "AIS Vessel Tracker - VPS Deployment Fix"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on VPS
if [ ! -d "/var/www/apihub" ]; then
    echo -e "${RED}Error: /var/www/apihub not found. Are you on the VPS?${NC}"
    echo "If running locally, use: ssh your-vps 'bash -s' < deploy_to_vps.sh"
    exit 1
fi

cd /var/www/apihub

echo -e "${YELLOW}Step 1: Pulling latest changes from repository...${NC}"
git pull origin main
if [ $? -ne 0 ]; then
    echo -e "${RED}Git pull failed! Please check manually.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Code updated${NC}"
echo ""

echo -e "${YELLOW}Step 1.5: Building frontend...${NC}"
if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm could not be found. Please install Node.js/npm.${NC}"
    echo "sudo apt install nodejs npm"
    exit 1
fi

cd frontend
npm install
if [ $? -ne 0 ]; then
    echo -e "${RED}npm install failed!${NC}"
    exit 1
fi

npm run build
if [ $? -ne 0 ]; then
    echo -e "${RED}npm run build failed!${NC}"
    exit 1
fi
cd ..
echo -e "${GREEN}✓ Frontend built successfully${NC}"
echo ""

echo -e "${YELLOW}Step 2: Checking database structure...${NC}"
if [ ! -f "vessel_static_data.db" ]; then
    echo -e "${RED}Error: vessel_static_data.db not found!${NC}"
    echo "Database should be created by ais-collector service"
    exit 1
fi

# Check for emissions table
echo "Checking if eu_mrv_emissions table exists..."
TABLE_EXISTS=$(sqlite3 vessel_static_data.db "SELECT name FROM sqlite_master WHERE type='table' AND name='eu_mrv_emissions';" 2>/dev/null)

if [ -z "$TABLE_EXISTS" ]; then
    echo -e "${YELLOW}⚠ eu_mrv_emissions table NOT found${NC}"
    echo ""
    echo "Checking if MRV data file exists..."
    MRV_FILE=$(ls data/2024-v99-*.xlsx 2>/dev/null | head -n 1)
    
    if [ -z "$MRV_FILE" ]; then
        echo -e "${RED}Error: EU MRV Excel file not found in data/ directory${NC}"
        echo "Please upload: 2024-v99-22102025-EU MRV Publication of information.xlsx"
        echo "To: /var/www/apihub/data/"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Found: $MRV_FILE${NC}"
    echo ""
    echo -e "${YELLOW}Importing emissions data (this will take 1-2 minutes)...${NC}"
    
    source venv/bin/activate
    python src/utils/import_mrv_data.py
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Emissions data imported successfully${NC}"
    else
        echo -e "${RED}Error importing emissions data${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ eu_mrv_emissions table exists${NC}"
    
    # Show record count
    EMISSIONS_COUNT=$(sqlite3 vessel_static_data.db "SELECT COUNT(*) FROM eu_mrv_emissions;" 2>/dev/null)
    echo "  Records: $EMISSIONS_COUNT"
fi
echo ""

echo -e "${YELLOW}Step 3: Checking systemd services...${NC}"

# Check each service
for service in ais-collector ais-web-tracker; do
    if systemctl is-active --quiet $service; then
        echo -e "${GREEN}✓ $service is running${NC}"
    else
        echo -e "${RED}✗ $service is NOT running${NC}"
        echo "  Starting $service..."
        sudo systemctl start $service
    fi
done

# Check optional services
for service in ais-emissions-matcher ais-econowind-updater; do
    if systemctl is-enabled --quiet $service 2>/dev/null; then
        if systemctl is-active --quiet $service; then
            echo -e "${GREEN}✓ $service is running${NC}"
        else
            echo -e "${YELLOW}⚠ $service is installed but not running${NC}"
        fi
    fi
done
echo ""

echo -e "${YELLOW}Step 4: Restarting web tracker...${NC}"
sudo systemctl restart ais-web-tracker
sleep 2

if systemctl is-active --quiet ais-web-tracker; then
    echo -e "${GREEN}✓ ais-web-tracker restarted successfully${NC}"
else
    echo -e "${RED}✗ ais-web-tracker failed to start${NC}"
    echo "Check logs with: sudo journalctl -u ais-web-tracker -n 50"
    exit 1
fi
echo ""

echo -e "${YELLOW}Step 5: Testing endpoints...${NC}"

# Test the main endpoints
test_endpoint() {
    local url=$1
    local name=$2
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:5000$url" 2>/dev/null)
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✓ $name: $HTTP_CODE${NC}"
        return 0
    else
        echo -e "${RED}✗ $name: $HTTP_CODE${NC}"
        return 1
    fi
}

test_endpoint "/ships/" "Main page"
test_endpoint "/ships/database" "Database page"
test_endpoint "/ships/api/stats" "Stats endpoint"
test_endpoint "/ships/api/vessels/combined?limit=10" "Combined vessels"
test_endpoint "/ships/api/emissions/stats" "Emissions stats"
test_endpoint "/ships/api/emissions/match-stats" "Match stats"

echo ""
echo -e "${YELLOW}Step 6: Database statistics...${NC}"

# Show database stats
python3 << 'PYTHON_SCRIPT'
import sqlite3

conn = sqlite3.connect('vessel_static_data.db')
cursor = conn.cursor()

# Vessels count
cursor.execute("SELECT COUNT(*) FROM vessels_static")
vessels_count = cursor.fetchone()[0]
print(f"  Total vessels in AIS database: {vessels_count:,}")

# Vessels with IMO
cursor.execute("SELECT COUNT(*) FROM vessels_static WHERE imo IS NOT NULL AND imo > 0")
imo_count = cursor.fetchone()[0]
print(f"  Vessels with IMO number: {imo_count:,}")

try:
    # Emissions count
    cursor.execute("SELECT COUNT(*) FROM eu_mrv_emissions")
    emissions_count = cursor.fetchone()[0]
    print(f"  Vessels in emissions database: {emissions_count:,}")
    
    # Matched count
    cursor.execute("""
        SELECT COUNT(*)
        FROM vessels_static v
        INNER JOIN eu_mrv_emissions e ON v.imo = e.imo
    """)
    matched = cursor.fetchone()[0]
    match_rate = (matched / imo_count * 100) if imo_count > 0 else 0
    print(f"  Matched vessels (AIS + Emissions): {matched:,} ({match_rate:.1f}%)")
except Exception as e:
    print(f"  Error querying emissions: {e}")

conn.close()
PYTHON_SCRIPT

echo ""
echo "=========================================="
echo -e "${GREEN}Deployment completed!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Visit: https://gerritsxd.com/ships/database"
echo "2. Check browser console for errors (F12)"
echo "3. If issues persist, check logs:"
echo "   sudo journalctl -u ais-web-tracker -f"
echo ""
