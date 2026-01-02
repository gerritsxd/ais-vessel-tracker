# ADR-001: Use SQLite with WAL Mode for Database

## Status
Accepted

## Context
We need a database solution for storing vessel static data, position history, emissions data, and company intelligence. The system requires:
- High write throughput (10-30 position updates per minute per vessel)
- Concurrent read access (multiple API endpoints querying simultaneously)
- Low operational overhead (no separate database server to manage)
- File-based storage for easy backup and portability
- Support for 13,000+ vessels with millions of position records

## Decision
We use **SQLite with WAL (Write-Ahead Logging) mode** as our primary database.

### Implementation Details:
- Database file: `vessel_static_data.db`
- WAL mode enabled: `PRAGMA journal_mode=WAL`
- Performance optimizations:
  - `PRAGMA synchronous=NORMAL` - Faster writes while maintaining safety
  - `PRAGMA temp_store=MEMORY` - Use RAM for temporary tables
  - `PRAGMA cache_size=-64000` - 64MB cache for faster queries
- Connection timeout: 60 seconds for route queries, 30 seconds for standard queries
- Indexes on frequently queried columns: `mmsi`, `imo`, `timestamp`

## Consequences

### Positive:
- ✅ **Zero operational overhead** - No separate database server to manage
- ✅ **Concurrent access** - WAL mode allows multiple readers and one writer simultaneously
- ✅ **File-based** - Easy backup (copy single file), portable across systems
- ✅ **Low resource usage** - ~50MB per 10,000 vessels, minimal memory footprint
- ✅ **ACID compliance** - Full transaction support with rollback capability
- ✅ **Production proven** - Used by millions of applications worldwide

### Negative:
- ❌ **Single writer limitation** - Only one process can write at a time (acceptable for our use case)
- ❌ **No network access** - Must run on same machine as application (acceptable for VPS deployment)
- ❌ **Limited scalability** - Not suitable for multi-server deployments (acceptable for single VPS)

### Trade-offs:
- **Simplicity over scalability**: We prioritize operational simplicity over horizontal scaling
- **Performance over features**: SQLite provides excellent performance for our read-heavy workload
- **File-based over network**: We accept the limitation of local-only access for the benefit of zero configuration

## Alternatives Considered

### PostgreSQL
- **Pros**: Better concurrent writes, network access, advanced features
- **Cons**: Requires separate server, more complex setup, higher resource usage
- **Rejected**: Operational overhead outweighs benefits for single-server deployment

### MySQL/MariaDB
- **Pros**: Industry standard, excellent performance
- **Cons**: Requires separate server, more complex configuration
- **Rejected**: Same reasons as PostgreSQL

### In-memory database (Redis)
- **Pros**: Extremely fast, good for real-time data
- **Cons**: No persistence by default, limited query capabilities
- **Rejected**: Need persistent storage and complex queries

## Related ADRs
- ADR-007: Systemd for service management (ensures single writer)
- ADR-008: Nginx reverse proxy (doesn't affect database choice)

## References
- SQLite WAL Mode: https://www.sqlite.org/wal.html
- Performance optimizations documented in `src/services/web_tracker.py` lines 727-730

