# 🚢 AIS Vessel Tracker

Real-time vessel tracking system with interactive web-based map visualization. Collects AIS (Automatic Identification System) data from [AISStream.io](https://aisstream.io) and provides comprehensive vessel tracking capabilities.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## ✨ Features

### 📊 Data Collection
- **Real-time AIS data** from AISStream.io
- **Automatic flag state decoding** from MMSI
- **Comprehensive vessel database** (SQLite)
- **Auto-reconnect** with exponential backoff
- **Supports Class A & B** AIS transponders

### 🗺️ Web-Based Tracking
- **Interactive map** with Leaflet.js
- **Real-time position updates** via WebSocket
- **Color-coded markers** by vessel type
- **Click for details**: Name, flag, dimensions, speed, course
- **Auto-zoom** to show all tracked vessels

### 🎯 Smart Filtering
- Filter by vessel size (e.g., >100m)
- Exclude specific ship types (e.g., container ships)
- Track up to 50 vessels per WebSocket connection
- Multi-connection support for large fleets

### 🛠️ Utility Tools
- Interactive database queries
- CSV export
- Data quality statistics
- Ship type reference guide

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- AISStream API key ([Get one free](https://aisstream.io/apikeys))

### Installation

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/apihub.git
cd apihub

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Add your API key
echo "YOUR_AISSTREAM_API_KEY" > api.txt
```

### Usage

#### 1. Collect Vessel Data
```bash
python ais_collector.py
```
Runs continuously, collecting vessel static data and storing in SQLite database.

#### 2. View Tracked Vessels
```bash
python show_trackable_vessels.py
```
Shows all vessels matching your filter criteria.

#### 3. Real-Time Web Tracking
```bash
python web_tracker.py
```
Then open: **http://localhost:5000**

See vessels moving in real-time on an interactive map! 🌍

## 📸 Screenshots

### Interactive Map View
- Real-time vessel positions
- Color-coded by type (Tanker=Red, Cargo=Green, Passenger=Magenta)
- Click markers for detailed information

### Vessel Details Popup
- MMSI, Name, Flag State
- Length and dimensions
- Current position, speed, course
- Last update timestamp

## 🗄️ Database Schema

```sql
CREATE TABLE vessels_static (
    mmsi INTEGER PRIMARY KEY,
    name TEXT,
    ship_type INTEGER,
    length INTEGER,
    beam INTEGER,
    imo INTEGER,
    call_sign TEXT,
    flag_state TEXT,
    last_updated TEXT
);
```

## 📦 Project Structure

```
apihub/
├── ais_collector.py          # Main data collector
├── web_tracker.py             # Web-based real-time tracker
├── track_filtered_vessels.py  # Console-based tracker
├── mmsi_mid_lookup.py         # Flag state decoder
├── templates/
│   └── map.html              # Interactive map interface
├── query_vessels.py           # Database query tool
├── export_to_csv.py           # CSV export utility
├── check_data.py              # Data quality checker
├── show_trackable_vessels.py  # List filtered vessels
├── requirements.txt           # Python dependencies
├── DEPLOYMENT.md              # VPS deployment guide
└── README.md                  # This file
```

## 🌐 Deployment to VPS

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete VPS setup instructions.

Quick deploy:
```bash
# On your VPS
sudo bash setup_vps.sh
# Follow the prompts
```

## 🔧 Configuration

### Filter Criteria
Edit `web_tracker.py` or `track_filtered_vessels.py`:
```python
# Example: Track vessels >150m, excluding tankers
WHERE length >= 150
  AND (ship_type IS NULL OR ship_type NOT IN (80, 81, 82))
```

### Geographic Bounds
Edit subscription in tracker files:
```python
"BoundingBoxes": [
    [[North, West], [South, East]]
]
```

## 📊 Ship Type Codes

| Code | Type |
|------|------|
| 30 | Fishing |
| 60 | Passenger |
| 70 | Cargo |
| 80 | Tanker |
| 52 | Tug |

See `ship_type_reference.txt` for complete list.

## 🔐 Security

- **Never commit `api.txt`** - It's in `.gitignore`
- **Database is local** - Not committed to Git
- **Use HTTPS** in production (Let's Encrypt)
- **Restrict API access** if deploying publicly

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📝 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- [AISStream.io](https://aisstream.io) for AIS data API
- [Leaflet.js](https://leafletjs.com) for map visualization
- [Flask](https://flask.palletsprojects.com) for web framework
- [OpenStreetMap](https://www.openstreetmap.org) for map tiles

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/apihub/issues)
- **Documentation**: See `DEPLOYMENT.md` and `LONG_RUN_GUIDE.md`
- **AIS Stream Docs**: https://aisstream.io/documentation

## 🎯 Roadmap

- [ ] Historical track playback
- [ ] Geofencing alerts
- [ ] Email notifications
- [ ] REST API endpoints
- [ ] Mobile app
- [ ] Multi-user support

---

**Made with ❤️ for maritime enthusiasts**

⭐ Star this repo if you find it useful!
