# ADR-005: Hybrid AIS Data Sources (WebSocket + REST API)

## Status
Accepted

## Context
We need comprehensive vessel tracking coverage:
- **Coastal coverage**: Vessels near shore (within ~50 NM of coast)
- **Mid-ocean coverage**: Vessels crossing Atlantic Ocean (beyond terrestrial AIS range)
- **Real-time updates**: Position updates every few seconds for active vessels
- **Cost constraints**: Free tier API limits must be respected

The challenge: **Terrestrial AIS only reaches ~50 nautical miles from coast**, leaving mid-ocean vessels invisible.

## Decision
We use a **hybrid approach** combining two data sources:

1. **AISStream WebSocket** - Real-time coastal vessel tracking
   - 18 concurrent WebSocket connections (6 API keys × 3 connections each)
   - Tracks up to 900 vessels simultaneously
   - Updates every few seconds for active vessels
   - Free tier: 3 API keys

2. **Datalastic REST API** - Polled Atlantic coverage
   - Scans 5 strategic Atlantic zones every 6 hours
   - 50 NM radius per zone
   - Free tier: 20,000 credits/month
   - Usage: ~15,000 credits/month (within limit)

Both sources write to the same SQLite database (`vessel_static_data.db`), using MMSI-based upsert logic to avoid duplicates.

## Consequences

### Positive:
- ✅ **Complete coverage** - Both coastal and mid-ocean vessels tracked
- ✅ **Cost-effective** - Stays within free tier limits of both services
- ✅ **Unified database** - Single source of truth, no data synchronization needed
- ✅ **Automatic integration** - Atlantic-tracked vessels appear in web interface automatically
- ✅ **Redundancy** - If one source fails, other continues working

### Negative:
- ❌ **Update frequency difference** - Coastal vessels update every few seconds, Atlantic vessels every 6 hours
- ❌ **API key management** - Need to manage multiple API keys
- ❌ **Credit monitoring** - Must track Datalastic credit usage to stay within limits
- ❌ **Complexity** - Two different services to monitor and maintain

### Trade-offs:
- **Coverage over simplicity**: More complex setup but provides complete coverage
- **Free tier over paid**: Accepting update frequency limitations to avoid costs
- **Polling over real-time**: Atlantic coverage uses polling (6h intervals) vs. real-time WebSocket

## Implementation Details

### AISStream Collector (`ais_collector.py`)
- Connects to `wss://stream.aisstream.io/v0/stream`
- Rotates through 6 API keys
- Creates 3 connections per key (18 total)
- Filters vessels: length >= 100m, excludes container ships
- Stores in `vessels_static` and `vessel_positions` tables

### Atlantic Tracker (`atlantic_tracker.py`)
- Scans 5 zones: Mid-Atlantic North/Central/South, Western Approach, Caribbean Approach
- Runs every 6 hours via systemd timer
- Uses `vessel_inradius` API endpoint
- Filters: Excludes fishing/pleasure craft
- Same database tables as AIS collector

### Database Schema
Both services use:
- `vessels_static` - Vessel metadata (MMSI, name, type, dimensions)
- `vessel_positions` - Position history (lat, lon, timestamp)

Upsert logic ensures no duplicates when same vessel appears in both sources.

## Alternatives Considered

### Single AISStream source only
- **Pros**: Simpler, single API to manage
- **Cons**: Missing mid-ocean vessels, incomplete coverage
- **Rejected**: Incomplete coverage unacceptable

### Single Datalastic source only
- **Pros**: Complete coverage, single API
- **Cons**: Polling only (no real-time), higher cost at scale
- **Rejected**: Real-time updates are important for user experience

### Satellite AIS service (paid)
- **Pros**: Complete coverage, real-time updates
- **Cons**: Expensive ($100s/month), overkill for our needs
- **Rejected**: Cost prohibitive, free tier sufficient

## Related ADRs
- ADR-001: SQLite database (stores data from both sources)
- ADR-007: Systemd services (runs both collectors)

## References
- AISStream: https://aisstream.io/
- Datalastic: https://www.datalastic.com/
- Implementation: `src/collectors/ais_collector.py`, `src/collectors/atlantic_tracker.py`
- Documentation: `docs/dev-notes/ATLANTIC_TRACKER_GUIDE.md`

