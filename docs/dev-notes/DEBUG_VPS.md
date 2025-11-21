# Debug Gemini Scraper on VPS

Run these commands on your VPS to diagnose:

## 1. Check if service is running
```bash
sudo systemctl status ais-intelligence-scraper-gemini
```

## 2. Check if service exists
```bash
ls -la /etc/systemd/system/ais-intelligence-scraper-gemini.service
```

## 3. Check if log file exists
```bash
ls -la /var/www/apihub/logs/intelligence_scraper_gemini.log
```

## 4. Check recent systemd logs
```bash
sudo journalctl -u ais-intelligence-scraper-gemini -n 50
```

## 5. Check if API key file exists
```bash
cat /var/www/apihub/config/gemini_api_key.txt
```

## 6. Try running manually to see errors
```bash
cd /var/www/apihub
source venv/bin/activate
python src/services/intelligence_scraper_service_gemini.py
```

---

## Most Likely Issues:

### Issue 1: Service not started yet
```bash
sudo systemctl start ais-intelligence-scraper-gemini
```

### Issue 2: API key not added
```bash
nano config/gemini_api_key.txt
# Add: AIzaSyBQhDnXnHHyeOIB69eyzXeDLoCnmrKZ2nw
```

### Issue 3: Gemini package not installed
```bash
source venv/bin/activate
pip install google-generativeai
```

### Issue 4: Service file not copied
```bash
sudo cp config/systemd/ais-intelligence-scraper-gemini.service /etc/systemd/system/
sudo systemctl daemon-reload
```
