# ADR-004: Use Leaflet.js for Interactive Maps

## Status
Accepted

## Context
We need a mapping library that can:
- Display vessel positions on an interactive world map
- Handle thousands of markers efficiently
- Support real-time updates (vessels moving)
- Provide route/polyline rendering
- Work well with React
- Be customizable (custom markers, popups, controls)
- Support dark mode tiles

## Decision
We use **Leaflet.js 1.9.4** with **react-leaflet 5.0.0** wrapper for mapping.

### Implementation Details:
- Leaflet.js 1.9.4 - Core mapping library
- react-leaflet 5.0.0 - React components for Leaflet
- Tile layers:
  - OpenStreetMap (light mode)
  - CartoDB Dark Matter (dark mode)
- Custom vessel markers with ship type icons
- Polyline rendering for route history
- Viewport-based vessel loading (only load vessels in visible area)
- Map instance handling via `useMap()` hook

## Consequences

### Positive:
- ✅ **Lightweight** - ~40KB gzipped, much smaller than Google Maps
- ✅ **Open source** - Free, no API keys required for basic tiles
- ✅ **Highly customizable** - Easy to create custom markers, popups, controls
- ✅ **Good performance** - Handles 1000+ markers efficiently with clustering options
- ✅ **React integration** - react-leaflet provides clean React components
- ✅ **Mobile friendly** - Touch gestures work well on mobile devices
- ✅ **Plugin ecosystem** - Many plugins available (we use react-leaflet)

### Negative:
- ❌ **Tile server dependency** - Relies on external tile servers (OpenStreetMap, CartoDB)
- ❌ **No built-in geocoding** - Would need separate service for address lookup (not needed)
- ❌ **Limited 3D support** - 2D only (acceptable for our use case)

### Trade-offs:
- **Customization over features**: Leaflet provides more control than Google Maps, but requires more setup
- **Open source over convenience**: Free tiles vs. Google Maps API costs
- **Performance over simplicity**: Viewport filtering requires more code but enables better performance

## Alternatives Considered

### Google Maps API
- **Pros**: Rich features, excellent documentation, geocoding built-in
- **Cons**: Requires API key, usage limits, costs money at scale, less customizable
- **Rejected**: Cost and API key requirements, less customization needed

### Mapbox GL JS
- **Pros**: Beautiful styling, 3D support, excellent performance
- **Cons**: Requires API key, usage limits, costs money
- **Rejected**: Cost and API key requirements

### OpenLayers
- **Pros**: More features, supports more formats
- **Cons**: Steeper learning curve, larger bundle size, more complex API
- **Rejected**: Overkill for our needs, Leaflet is simpler

## Related ADRs
- ADR-003: React frontend (uses react-leaflet components)
- ADR-002: Flask backend (serves map data via API)

## References
- Leaflet documentation: https://leafletjs.com/
- react-leaflet documentation: https://react-leaflet.js.org/
- Implementation: `frontend/src/pages/Map.jsx`

