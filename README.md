# 🚢 AIS Vessel Tracker & Intelligence Platform

Real-time maritime tracking system using hybrid AIS data sources (WebSocket streams + polled Atlantic coverage), emissions enrichment via EU MRV data, and AI-powered company intelligence. Deployed on VPS with systemd + Nginx.

🌐 **Live Demo:** [https://gerritsxd.com/ships/](https://gerritsxd.com/ships/)

![CI](https://github.com/gerritsxd/ais-vessel-tracker/actions/workflows/tests.yml/badge.svg) ![Vessels](https://img.shields.io/badge/Vessels-1050+-blue) ![Emissions Data](https://img.shields.io/badge/Emissions-16K+-green) ![Status](https://img.shields.io/badge/Status-Live-success) ![Python](https://img.shields.io/badge/Python-3.13-blue)

## ✨ Key Features

- **Real-Time AIS Ingestion**: WebSocket streams with multi-key rotation (900 vessels simultaneously)
- **Atlantic Gap Coverage**: Polled API scans for mid-ocean vessels beyond terrestrial AIS range
- **Emissions Intelligence**: EU MRV data matching with CO₂ intensity tracking
- **AI Company Profiling**: Google Gemini scrapes grants, legal violations, sustainability news
- **Wind Propulsion Scoring**: "Econowind Fit Score" identifies retrofit candidates (0-8 scale)
- **Interactive Map UI**: Leaflet.js with route history, outlier filtering, and real-time updates
- **VPS Production Ready**: Systemd services, Nginx reverse proxy, SQLite WAL mode

## 🏗️ Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   AISStream     │      │   Datalastic    │      │  Google Gemini  │
│  (WebSocket)    │      │   (REST API)    │      │     (LLM)       │
└────────┬────────┘      └────────┬────────┘      └────────┬────────┘
         │                        │                        │
         v                        v                        v
┌────────────────┐      ┌────────────────┐      ┌────────────────┐
│ ais_collector  │      │atlantic_tracker│      │ intel_scraper  │
└────────┬───────┘      └────────┬───────┘      └────────┬───────┘
         │                       │                       │
         └───────────┬───────────┴───────────┬───────────┘
                     │                       │
                     v                       v
            ┌─────────────────────────────────────────┐
            │   SQLite Database (WAL Mode)            │
            │  vessels | emissions | companies | pos  │
            └──────────────────┬──────────────────────┘
                               │
                               v
                    ┌──────────────────────┐
                    │  Flask + SocketIO    │
                    │  (web_tracker.py)    │
                    └──────────┬───────────┘
                               │
                               v
                    ┌──────────────────────┐
                    │  Web Browser         │
                    │  (Leaflet + 3D Viz)  │
                    └──────────────────────┘
```

## 🛠️ Tech Stack

**Backend**
- Python 3.13 (with type hints), Flask, Flask-SocketIO
- SQLite3 (WAL mode for concurrency)
- websocket-client, requests, BeautifulSoup4
- PyTest (unit testing)

**Frontend**
- Leaflet.js (maps), Socket.IO (real-time)
- HTML5/CSS3 (dark theme), Bootstrap

**Data Sources**
- AISStream (real-time WebSocket)
- Datalastic (Atlantic coverage)
- EU MRV Emissions Database
- ITF Global (company lookup)
- Google Gemini 2.0 Flash (AI intelligence)

**Infrastructure**
- Nginx (reverse proxy)
- Systemd (service orchestration)
- GitHub Actions CI/CD (automated testing)
- Git deployment workflow

## 🚀 How to Run

### 1. Setup Environment
```bash
git clone https://github.com/gerritsxd/ais-vessel-tracker.git
cd ais-vessel-tracker
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r config/requirements.txt
```

### 2. Configure API Keys
```bash
# Copy config templates and add your keys
cp config/aisstream_keys.example config/aisstream_keys
# Edit config/aisstream_keys with your AISStream API keys (one per line)

# Optional: Datalastic key (for Atlantic coverage)
echo "YOUR_DATALASTIC_KEY" > config/datalastic_api_key.txt

# Optional: Gemini key (for company intelligence)
echo "YOUR_GEMINI_KEY" > config/gemini_api_key.txt
```

**Get API keys:**
- AISStream: https://aisstream.io/ (free tier: 3 keys recommended)
- Datalastic: https://www.datalastic.com/ (optional, for mid-ocean coverage)
- Google Gemini: https://makersuite.google.com/app/apikey (optional, for AI analysis)

### 3. Start Services
```bash
# Terminal 1: Flask Web Server
python src/services/web_tracker.py

# Terminal 2: Real-time AIS Collection
python src/collectors/ais_collector.py

# Terminal 3 (optional): Atlantic Coverage
python src/collectors/atlantic_tracker.py
```

Open `http://localhost:5000/ships/` in your browser.

## 🧪 Testing

Run unit tests to verify parsing logic:

```bash
# Install test dependencies
pip install pytest

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_parsing.py
```

## 💡 What I Learned & Challenges Solved

**High-Volume WebSocket Management**
- Handling 10-30 position updates per minute per vessel required SQLite WAL mode to prevent database locks
- Implemented connection pooling with 18 concurrent WebSocket streams (6 API keys × 3 connections each)

**Route Outlier Detection**
- Raw AIS data contains GPS errors causing vessels to "teleport" across oceans
- Built `filter_route_outliers()` algorithm checking speed (max 60 knots), distance (max 500km jumps), and time gaps (>2 hours = segment break)

**Hybrid Data Merging**
- Real-time coastal vessels (WebSocket) + polled Atlantic vessels (REST API) → single unified API endpoint
- Challenge: Avoid duplicates while ensuring mid-ocean ships appear on map

**Free-Tier Optimization**
- Google Gemini: Strict batching (30 companies/day, 30s delays) to stay under 1,500 req/day limit
- Datalastic: 5 Atlantic zones × 4 scans/day = ~100 vessels/scan, staying under 20,000 credits/month

**Production Deployment**
- Systemd service management with auto-restart on failure
- Nginx reverse proxy for WebSocket upgrade handling
- Git-based deployment workflow: local dev → git push → VPS git pull → service restart

**Automated Testing & CI/CD**
- GitHub Actions runs pytest + flake8 linting on every push
- Catches parsing errors and syntax issues before deployment
- Green badge = confidence in production stability

## 🔮 Future Work

- [ ] **Historical Playback**: Scrubbable timeline to replay vessel movements
- [ ] **Geofencing Alerts**: Slack/Discord webhooks when specific vessels enter zones
- [ ] **Predictive ETA**: ML model for accurate arrival time based on historical speed patterns
- [ ] **Container Ship Tracking**: Expand filtering beyond current cargo/tanker focus
- [ ] **Mobile PWA**: Progressive web app for on-the-go tracking
- [ ] **Multi-Tenant Support**: Separate dashboards for different companies/fleets

## 📁 Folder Structure

```
apihub/
├── .github/
│   └── workflows/
│       └── tests.yml        # CI/CD pipeline (pytest + linting)
├── src/
│   ├── collectors/          # Data ingestion services
│   │   ├── ais_collector.py      # Real-time WebSocket (AISStream)
│   │   ├── atlantic_tracker.py   # Polled Atlantic coverage (Datalastic)
│   │   └── company_lookup.py     # ITF company scraper
│   ├── services/            # Business logic & background jobs
│   │   ├── web_tracker.py        # Flask app + REST API + SocketIO
│   │   ├── emissions_matcher.py  # EU MRV data matching
│   │   ├── econowind_score_updater.py  # Wind retrofit scoring
│   │   ├── gt_scraper.py         # Gross tonnage enrichment
│   │   └── intelligence_scraper_service_gemini.py  # AI company intel
│   └── utils/               # Helpers and one-off scripts
├── templates/               # HTML frontend
│   ├── map.html             # Main tracking interface
│   ├── database_enhanced.html    # Database browser
│   ├── fleet_visualization.html  # 3D network viz
│   └── intelligence.html    # Company intelligence dashboard
├── config/                  # Service definitions & requirements
│   ├── requirements.txt
│   ├── systemd/             # Service files for VPS
│   └── *.txt               # API keys (gitignored)
├── data/                    # SQLite DB & caches (gitignored)
├── tests/                   # Unit tests (PyTest)
│   └── test_parsing.py      # AIS message parsing tests
└── scripts/                 # Deployment & debug tools
```

## 🗄️ Database Schema

**vessels_static** - Core vessel data
- `mmsi` (PK), `name`, `ship_type`, `length`, `beam`, `imo`, `call_sign`, `flag_state`, `signatory_company`, `wind_assisted`

**vessel_positions** - Position history
- `id` (PK), `mmsi` (FK), `latitude`, `longitude`, `sog`, `cog`, `timestamp`

**eu_mrv_emissions** - Environmental data
- `imo` (PK), `vessel_name`, `company_name`, `total_co2_emissions`, `avg_co2_per_distance`, `technical_efficiency`, `econowind_fit_score`, `gross_tonnage`

**company_intelligence** - AI-scraped company data
- JSON structure with categories: grants_subsidies, legal_violations, sustainability_news, reputation, financial_pressure


## 🌐 API Endpoints

- `GET /ships/` - Main tracking map
- `GET /ships/database` - Database browser
- `GET /ships/intelligence` - Company intelligence dashboard
- `GET /ships/api/vessels` - All tracked vessels (JSON)
- `GET /ships/api/vessel/<mmsi>/route?hours=24` - Route history
- `GET /ships/api/emissions/vessel/<imo>` - Emissions data
- `WebSocket /ships/socket.io` - Real-time position updates

## 🔧 Production Monitoring

```bash
# Check service status
sudo systemctl status ais-collector ais-web-tracker ais-atlantic-tracker

# View live logs
sudo journalctl -u ais-web-tracker -f

# Database stats
sqlite3 data/vessel_static_data.db "SELECT COUNT(*) FROM vessels_static"
```

## 📊 Performance Metrics

- **Database**: ~50MB per 10,000 vessels
- **Memory**: ~200MB per service
- **CPU**: <5% on modern VPS
- **Network**: ~1-2 Mbps for 900 vessels
- **Updates**: 10-30 positions/min per vessel

## 📝 License

MIT License - See LICENSE file

## 🙏 Credits

- [AISStream.io](https://aisstream.io/) - Real-time AIS WebSocket
- [Datalastic](https://datalastic.com/) - Atlantic coverage API
- [EU MRV](https://mrv.emsa.europa.eu/) - Emissions database
- [Google Gemini](https://ai.google.dev/) - Company intelligence
- [Leaflet.js](https://leafletjs.com/) - Mapping library
- [ITF Global](https://lookup.itfglobal.org/) - Company lookup

## 🤝 Contributing

Pull requests welcome! Ensure:
- API keys stay in gitignored files
- Database migrations documented
- Code follows existing patterns
