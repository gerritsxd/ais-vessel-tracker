# Architecture Decision Records (ADR)

This directory contains Architecture Decision Records (ADRs) for the AIS Vessel Tracker project.

## What are ADRs?

Architecture Decision Records document important architectural decisions made during the development of the project. They capture:
- **Context**: Why the decision was needed
- **Decision**: What was decided
- **Consequences**: Positive and negative impacts
- **Alternatives**: What other options were considered

## Why ADRs?

- **Documentation**: Future developers can understand why decisions were made
- **Consistency**: Ensures decisions are made thoughtfully and documented
- **Onboarding**: New team members can quickly understand the architecture
- **History**: Track how the architecture evolved over time

## ADR Index

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-001](0001-use-sqlite-with-wal-mode.md) | Use SQLite with WAL Mode for Database | Accepted |
| [ADR-002](0002-use-flask-socketio-for-backend.md) | Use Flask + Socket.IO for Backend Web Framework | Accepted |
| [ADR-003](0003-use-react-vite-for-frontend.md) | Use React + Vite for Frontend Framework | Accepted |
| [ADR-004](0004-use-leaflet-for-mapping.md) | Use Leaflet.js for Interactive Maps | Accepted |
| [ADR-005](0005-hybrid-ais-data-sources.md) | Hybrid AIS Data Sources (WebSocket + REST API) | Accepted |
| [ADR-006](0006-csv-files-for-ml-scores.md) | CSV Files for ML Scores Instead of Database/API | Accepted |
| [ADR-007](0007-systemd-for-service-management.md) | Systemd for Service Management | Accepted |
| [ADR-008](0008-nginx-reverse-proxy.md) | Nginx Reverse Proxy for Production | Accepted |
| [ADR-009](0009-python-type-hints.md) | Python Type Hints Throughout Codebase | Accepted |
| [ADR-010](0010-git-based-deployment.md) | Git-Based Deployment Workflow | Accepted |

## How to Create a New ADR

When making a significant architectural decision:

1. **Create a new ADR file**: `docs/adr/00XX-short-title.md`
2. **Use the template**:
   ```markdown
   # ADR-00XX: Short Title

   ## Status
   Proposed | Accepted | Rejected | Deprecated | Superseded

   ## Context
   [Describe the issue or problem that requires a decision]

   ## Decision
   [Describe the decision that was made]

   ## Consequences
   ### Positive:
   - ✅ [Benefit 1]
   - ✅ [Benefit 2]

   ### Negative:
   - ❌ [Drawback 1]
   - ❌ [Drawback 2]

   ## Alternatives Considered
   - [Alternative 1]: [Why rejected]
   - [Alternative 2]: [Why rejected]

   ## Related ADRs
   - ADR-XXX: [Related decision]

   ## References
   - [Links to relevant documentation or code]
   ```

3. **Update this README** with the new ADR
4. **Commit and push** the ADR

## ADR Statuses

- **Proposed**: Decision is being discussed
- **Accepted**: Decision has been made and implemented
- **Rejected**: Decision was considered but not adopted
- **Deprecated**: Decision is no longer relevant (superseded or obsolete)
- **Superseded**: Decision has been replaced by a newer ADR

## Related Documentation

- [Project README](../../README.md) - Overview of the project
- [Deployment Guide](../DEPLOYMENT.md) - How to deploy the application
- [Development Guide](../DEVELOPMENT.md) - Development setup and guidelines

