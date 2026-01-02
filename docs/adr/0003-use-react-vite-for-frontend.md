# ADR-003: Use React + Vite for Frontend Framework

## Status
Accepted

## Context
We need a frontend framework that can:
- Display interactive maps with real-time vessel positions
- Handle complex state management (vessel filters, route history, wind data)
- Provide smooth animations and transitions
- Build efficiently for production deployment
- Integrate with Socket.IO for real-time updates
- Work with Leaflet.js for mapping

## Decision
We use **React 19.1.1 + Vite 6.0.0** as our frontend framework and build tool.

### Implementation Details:
- React 19.1.1 - UI library with hooks (useState, useEffect, useCallback, useMemo)
- Vite 6.0.0 - Build tool and dev server
- React Router DOM 7.9.5 - Client-side routing
- Framer Motion 12.23.24 - Animation library
- React Leaflet 5.0.0 - React wrapper for Leaflet.js
- Socket.IO Client 4.8.1 - Real-time updates
- Base path: `/ships/` in production (configured in `vite.config.js`)

### Key Components:
- `Map.jsx` - Main vessel tracking map (1100+ lines)
- `TargetVessels.jsx` - ML insights and vessel ranking
- `MLinsights.jsx` - Company adoption scores visualization
- `VesselDatabase.jsx` - Database browser with CSV export

## Consequences

### Positive:
- ✅ **Component-based architecture** - Reusable, maintainable UI components
- ✅ **Fast development** - Vite provides instant HMR (Hot Module Replacement)
- ✅ **Fast builds** - Vite uses esbuild for lightning-fast production builds
- ✅ **Modern React** - Hooks API provides clean state management
- ✅ **Rich ecosystem** - Large library ecosystem (Leaflet, animations, etc.)
- ✅ **Type safety** - TypeScript support available (using JSX currently)

### Negative:
- ❌ **Bundle size** - React + dependencies adds ~200KB (acceptable for web app)
- ❌ **Learning curve** - React requires understanding hooks and component lifecycle
- ❌ **Complex state** - Large components (Map.jsx is 1100+ lines, could be split)

### Trade-offs:
- **Component reusability over simplicity**: React's component model is more complex than vanilla JS but enables better code organization
- **Build speed over feature completeness**: Vite prioritizes speed over some advanced features of Webpack
- **Modern over stable**: React 19 is newer, but provides better performance and features

## Alternatives Considered

### Vue.js + Vite
- **Pros**: Simpler learning curve, excellent documentation, good performance
- **Cons**: Smaller ecosystem than React, less common in industry
- **Rejected**: React has larger ecosystem and more mapping libraries

### Vanilla JavaScript + Leaflet
- **Pros**: No framework overhead, smaller bundle size
- **Cons**: More code to write, harder to maintain complex state
- **Rejected**: React provides better structure for our complex UI

### Next.js (React framework)
- **Pros**: Server-side rendering, built-in routing, excellent DX
- **Cons**: Overkill for our SPA, adds complexity, requires Node.js server
- **Rejected**: We don't need SSR, Flask already serves static files

## Related ADRs
- ADR-002: Flask backend (serves React build)
- ADR-004: Leaflet.js for mapping (integrated via react-leaflet)
- ADR-006: CSV files for ML data (loaded by React components)

## References
- React documentation: https://react.dev/
- Vite documentation: https://vitejs.dev/
- Implementation: `frontend/src/` directory

