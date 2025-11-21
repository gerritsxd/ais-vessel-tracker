# 🚀 Deploy Intelligence Dashboard - NOW!

## ✅ What's Ready to Deploy

1. **Intelligence Dashboard** web page
2. **API endpoints** for datasets, stats, downloads
3. **Intelligence Scraper V2** (DuckDuckGo-based)
4. **Navigation links** on all pages
5. **Auto-refresh** and real-time stats

---

## 🎯 Quick Deployment (5 Minutes)

### Step 1: Push to Git (Local PC)

```bash
# Make sure you're in the project directory
cd c:\Users\gerrit\Desktop\apihub

# Add all changes
git add .

# Commit
git commit -m "Add Intelligence Dashboard - view/download intelligence data"

# Push to VPS
git push origin main
```

---

### Step 2: Deploy on VPS

```bash
# SSH to VPS
ssh erik@yourserver

# Go to project
cd /var/www/apihub

# Pull latest code
git pull origin main

# Restart web service
sudo systemctl restart ais-web-tracker

# Check it's running
sudo systemctl status ais-web-tracker
```

---

### Step 3: Access the Dashboard

Open browser and go to:
```
https://gerritsxd.com/ships/intelligence
```

You should see:
- Statistics cards (will show 0 if no data yet)
- Empty datasets section
- Message: "No datasets available yet"

**This is NORMAL!** You haven't collected data yet.

---

## 📊 Collect Intelligence Data on VPS

### Option A: Test Run (2 companies, 5 minutes)

```bash
# On VPS
cd /var/www/apihub

# Test scraper
python src/utils/company_intelligence_scraper_v2.py --max-companies 2 -v
```

**Check results:**
- Look for findings in console output
- Check if file created: `data/company_intelligence_v2_*.json`
- Refresh dashboard to see data

---

### Option B: Batch Run (100 companies, overnight)

```bash
# On VPS - run in background
cd /var/www/apihub

nohup python src/utils/company_intelligence_scraper_v2.py \
  --max-companies 100 \
  -v \
  > logs/intelligence_$(date +%Y%m%d).log 2>&1 &

# Get process ID
echo $!

# Monitor progress
tail -f logs/intelligence_*.log

# Or check periodically
grep "✅" logs/intelligence_*.log | tail -20
```

**Expected results:**
- ~5-8 hours for 100 companies
- Creates: `data/company_intelligence_v2_TIMESTAMP.json`
- Dashboard auto-updates with new data

---

## 🔍 Troubleshooting

### Problem: Still 0 findings on VPS

**Causes:**
- DuckDuckGo blocking automated requests
- Company names too specific
- Network issues

**Solutions:**

1. **Increase delays** (reduce request rate):
```python
# Edit src/utils/company_intelligence_scraper_v2.py
self.min_delay = 5.0  # Was 2.0
self.max_delay = 10.0  # Was 4.0
```

2. **Try different search terms**:
```python
# Edit queries to be broader
'grants_subsidies': [
    f'{company_name} maritime green shipping',  # Removed quotes
    f'{company_name} EU funding',
],
```

3. **Use VPN/Proxy** (if VPS allows)

4. **Try on different times** (less traffic = less blocking)

---

### Problem: Web page shows errors

**Check logs:**
```bash
sudo journalctl -u ais-web-tracker -n 50
```

**Common fixes:**
```bash
# Restart service
sudo systemctl restart ais-web-tracker

# Check Python errors
tail -f /var/www/apihub/logs/*.log
```

---

## 📥 Using the Dashboard

### Download Datasets

1. Go to https://gerritsxd.com/ships/intelligence
2. Scroll to "Available Datasets"
3. Click **📥 Download** button
4. JSON file downloads to your computer

### View Statistics

- **Total Companies**: How many scraped
- **Total Findings**: Intelligence items found
- **Categories**: Breakdown by type
- **Top Companies**: Who has most findings

### Refresh Data

- Auto-refreshes every 30 seconds
- OR click **🔄 Refresh** button manually

---

## 🎓 Understanding the Data

### What "Findings" Mean

Each finding = One piece of intelligence:
- News article mentioning company
- Government grant announcement
- Lawsuit record
- Sustainability report
- Financial pressure indicator

### What's Predictive

**High value findings:**
- 🇩🇪 **German grants** → WASP adoption (your insight!)
- ⚖️ **Lawsuits** → Need for "facelifting" (your insight!)
- 💰 **EU ETS costs** → Financial motivation
- 📰 **Retrofit news** → Innovation culture

**Low value findings:**
- Generic news mentions
- Social media posts
- Company press releases

---

## 🔄 Continuous Collection

### Set up Weekly Scraping

```bash
# On VPS, edit crontab
crontab -e

# Add this line (runs every Monday at 2 AM):
0 2 * * 1 cd /var/www/apihub && python src/utils/company_intelligence_scraper_v2.py --max-companies 50 >> logs/intelligence_weekly.log 2>&1
```

This keeps your intelligence data **fresh**!

---

## 💡 Alternative: Manual Data Entry

If scraping doesn't work, you can manually add intelligence:

1. Create JSON file: `data/company_intelligence_v2_manual.json`
2. Format:
```json
{
  "companies": {
    "Maersk A/S": {
      "company_name": "Maersk A/S",
      "timestamp": "2025-11-17T14:00:00",
      "metadata": {
        "vessel_count": 146,
        "avg_emissions": 40835.07
      },
      "intelligence": {
        "grants_subsidies": {
          "results_count": 1,
          "findings": [
            {
              "url": "https://ec.europa.eu/...",
              "title": "Maersk receives €50M EU grant",
              "snippet": "A.P. Moller-Maersk receives funding...",
              "source": "government",
              "category": "grants_subsidies"
            }
          ]
        },
        "legal_violations": {"results_count": 0, "findings": []},
        "sustainability_news": {"results_count": 0, "findings": []},
        "reputation": {"results_count": 0, "findings": []},
        "financial_pressure": {"results_count": 0, "findings": []}
      }
    }
  },
  "total": 1,
  "timestamp": "2025-11-17T14:00:00",
  "version": "intelligence-v2-manual"
}
```

3. Save file
4. Dashboard picks it up automatically!

---

## ✅ Success Checklist

After deployment:
- [ ] Pushed code to git
- [ ] Pulled on VPS
- [ ] Restarted ais-web-tracker service
- [ ] Can access /ships/intelligence page
- [ ] Navigation links work on all pages
- [ ] Dashboard loads (even if empty)
- [ ] Tested scraper (2 companies)
- [ ] Started batch scraping (100+ companies)
- [ ] Can download datasets

---

## 🎯 Expected Timeline

| Task | Duration |
|------|----------|
| **Deploy code** | 5 minutes |
| **Test scraper** | 10 minutes |
| **Small batch (10 companies)** | 30-60 minutes |
| **Large batch (100 companies)** | 5-8 hours |
| **Full dataset (500 companies)** | 24-40 hours |

**Recommendation:** 
1. Deploy NOW (5 min)
2. Test with 5 companies (30 min)
3. If working, run 100 overnight
4. If not working, try manual data or wait for better scraping solution

---

## 📞 Quick Commands Reference

```bash
# Deploy
git add . && git commit -m "Intelligence Dashboard" && git push

# On VPS
cd /var/www/apihub && git pull && sudo systemctl restart ais-web-tracker

# Test scraper
python src/utils/company_intelligence_scraper_v2.py --max-companies 5 -v

# Batch scrape (background)
nohup python src/utils/company_intelligence_scraper_v2.py --max-companies 100 -v > intel.log 2>&1 &

# Check logs
tail -f intel.log
grep "✅" intel.log

# Access dashboard
https://gerritsxd.com/ships/intelligence
```

---

**Status:** ✅ **READY TO DEPLOY!**  
**Next step:** Run the git commands above!
