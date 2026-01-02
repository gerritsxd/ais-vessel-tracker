# ADR-002: Use Flask + Socket.IO for Backend Web Framework

## Status
Accepted

## Context
We need a web framework that can:
- Serve REST API endpoints for vessel data
- Provide real-time WebSocket updates for live vessel positions
- Handle concurrent connections (multiple users viewing the map simultaneously)
- Integrate with existing Python codebase (AIS collectors, data processors)
- Deploy easily on a VPS with minimal configuration

## Decision
We use **Flask + Flask-SocketIO** as our backend web framework.

### Implementation Details:
- Flask 3.1.2 - Core web framework
- Flask-SocketIO 5.5.1 - WebSocket support via Socket.IO protocol
- Socket.IO path: `/ships/socket.io` (works with Nginx reverse proxy)
- CORS enabled: `cors_allowed_origins="*"` (for development flexibility)
- ProxyFix middleware: Handles X-Forwarded-For headers from Nginx
- Single Flask app (`web_tracker.py`) serves:
  - Static frontend files from `frontend/dist/`
  - REST API endpoints (`/ships/api/*`)
  - WebSocket real-time updates
  - CSV data files from `frontend/public/data/`

## Consequences

### Positive:
- ✅ **Lightweight** - Minimal overhead compared to Django or FastAPI
- ✅ **Real-time support** - Socket.IO provides reliable WebSocket with fallback to polling
- ✅ **Python ecosystem** - Easy integration with existing Python code
- ✅ **Flexible routing** - Simple decorator-based API endpoints
- ✅ **Mature library** - Flask is battle-tested and widely used
- ✅ **Single process** - Simpler deployment than multi-process frameworks

### Negative:
- ❌ **Single-threaded by default** - May need async workers for high concurrency (not an issue yet)
- ❌ **Less structure** - No built-in ORM or admin panel (we use raw SQL, acceptable)
- ❌ **Manual async handling** - Socket.IO handles async, but Flask routes are synchronous

### Trade-offs:
- **Simplicity over features**: We prefer Flask's simplicity over Django's batteries-included approach
- **Real-time over REST-only**: Socket.IO provides better real-time experience than polling
- **Python over Node.js**: Existing codebase is Python, easier to maintain single language

## Alternatives Considered

### Django + Channels
- **Pros**: Full-featured framework, built-in admin, Channels for WebSocket
- **Cons**: Heavier, more complex, overkill for our API-focused app
- **Rejected**: Too much framework for our needs

### FastAPI + WebSockets
- **Pros**: Modern, async-first, automatic API docs, type hints
- **Cons**: Less mature ecosystem, Socket.IO more reliable than raw WebSockets
- **Rejected**: Socket.IO provides better browser compatibility and fallback

### Node.js + Express + Socket.IO
- **Pros**: Native Socket.IO, excellent real-time performance
- **Cons**: Would require rewriting Python collectors, losing ecosystem
- **Rejected**: Existing Python codebase is valuable, not worth rewriting

## Related ADRs
- ADR-003: React frontend (consumes Socket.IO client)
- ADR-008: Nginx reverse proxy (proxies Socket.IO connections)

## References
- Flask documentation: https://flask.palletsprojects.com/
- Flask-SocketIO documentation: https://flask-socketio.readthedocs.io/
- Implementation: `src/services/web_tracker.py`

