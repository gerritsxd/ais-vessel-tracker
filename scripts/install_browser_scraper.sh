#!/bin/bash

# Browser GT Scraper Installation Script
# Sets up Playwright and browser dependencies for GT scraping

echo "=========================================="
echo "BROWSER GT SCRAPER INSTALLATION"
echo "=========================================="

# Check if running on VPS
if [ "$EUID" -eq 0 ]; then
    echo "Running as root (VPS installation)"
    USER_HOME="/home/erik"
    PROJECT_DIR="/var/www/apihub"
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
else
    echo "Running as user (Local installation)"
    USER_HOME="$HOME"
    PROJECT_DIR="$(pwd)"
    PYTHON_CMD="python"
    PIP_CMD="pip"
fi

cd "$PROJECT_DIR"

echo ""
echo "1. Installing Playwright..."
$PIP_CMD install playwright==1.48.0

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Playwright"
    exit 1
fi

echo ""
echo "2. Installing Chromium browser..."
$PYTHON_CMD -m playwright install chromium

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Chromium"
    exit 1
fi

echo ""
echo "3. Installing system dependencies (Linux only)..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y \
        libnss3 \
        libatk-bridge2.0-0 \
        libdrm2 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxrandr2 \
        libgbm1 \
        libxss1 \
        libasound2
    echo "✓ System dependencies installed"
else
    echo "⚠ Not a Debian-based system, skipping system dependencies"
fi

echo ""
echo "4. Setting up database column..."
$PYTHON_CMD src/utils/add_gt_column.py

echo ""
echo "5. Testing browser scraper..."
$PYTHON_CMD src/utils/run_gt_browser_scraper_once.py

echo ""
echo "=========================================="
echo "INSTALLATION COMPLETE!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "- Test manually: $PYTHON_CMD src/utils/run_gt_browser_scraper_once.py"
echo "- Run continuous: $PYTHON_CMD src/services/gt_scraper_browser.py"
echo ""
if [ "$EUID" -eq 0 ]; then
    echo "VPS deployment:"
    echo "- sudo systemctl enable ais-gt-browser-scraper"
    echo "- sudo systemctl start ais-gt-browser-scraper"
    echo "- sudo journalctl -u ais-gt-browser-scraper -f"
else
    echo "Local development:"
    echo "- Commit changes: git add . && git commit -m 'Add browser GT scraper' && git push"
    echo "- Deploy to VPS: see docs/BROWSER_GT_SCRAPER_SETUP.md"
fi
echo ""
echo "Documentation: docs/BROWSER_GT_SCRAPER_SETUP.md"
