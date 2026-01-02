# ADR-009: Python Type Hints Throughout Codebase

## Status
Accepted

## Context
We have a large Python codebase with:
- Multiple services (collectors, web tracker, ML predictors)
- Complex data structures (vessel data, emissions data, company intelligence)
- Multiple developers (team collaboration)
- Long-term maintenance needs

We need to improve code maintainability, catch errors early, and improve IDE support.

## Decision
We use **Python type hints** throughout the codebase.

### Implementation Details:
- Python 3.13+ (full type hint support)
- Type hints for:
  - Function parameters and return types
  - Class attributes
  - Variables (where helpful)
- Use `typing` module: `Dict`, `List`, `Optional`, `Union`, etc.
- Use `Path` from `pathlib` for file paths
- Use dataclasses for structured data
- No strict type checking in CI (yet) - gradual adoption

### Examples:
```python
from typing import Dict, List, Optional
from pathlib import Path

def get_vessel_route(mmsi: int, hours: int = 24) -> List[Dict[str, float]]:
    """Get position history for a vessel."""
    ...

class VesselTracker:
    def __init__(self, db_path: Path, api_key: Optional[str] = None):
        self.db_path: Path = db_path
        self.api_key: Optional[str] = api_key
```

## Consequences

### Positive:
- ✅ **Better IDE support** - Autocomplete, error detection, refactoring
- ✅ **Self-documenting** - Types clarify function contracts
- ✅ **Early error detection** - Catch type errors before runtime
- ✅ **Better refactoring** - IDEs can safely rename/refactor
- ✅ **Team collaboration** - Easier for new developers to understand code
- ✅ **Gradual adoption** - Can add types incrementally

### Negative:
- ❌ **More verbose** - Type hints add lines of code
- ❌ **Learning curve** - Team must learn typing syntax
- ❌ **Runtime overhead** - None (type hints are ignored at runtime)
- ❌ **Not enforced** - Python doesn't enforce types (can use mypy for checking)

### Trade-offs:
- **Maintainability over brevity**: More code but easier to maintain
- **Documentation over speed**: Types serve as documentation
- **Gradual over strict**: Can adopt gradually, not all-at-once

## Alternatives Considered

### No type hints
- **Pros**: Less code, faster to write
- **Cons**: Harder to maintain, more bugs, worse IDE support
- **Rejected**: Long-term maintainability is important

### Strict type checking (mypy)
- **Pros**: Catches all type errors, enforces types
- **Cons**: Can be too strict, requires fixing all existing code
- **Future consideration**: Could adopt mypy later

### Type stubs only (.pyi files)
- **Pros**: Separate type information, doesn't clutter code
- **Cons**: More files to maintain, less convenient
- **Rejected**: Inline types are more convenient

## Implementation Status

### Completed:
- ✅ Core services have type hints (`web_tracker.py`, collectors)
- ✅ Utility functions have type hints
- ✅ ML predictors have type hints

### In Progress:
- 🔄 Some older files still need type hints added
- 🔄 Some complex types could use better annotations

### Future:
- Consider adding `mypy` to CI pipeline
- Consider using `dataclasses` more extensively
- Consider using `TypedDict` for dictionary structures

## Related ADRs
- None (this is a code quality decision, affects all code)

## References
- Python typing documentation: https://docs.python.org/3/library/typing.html
- Type hints guide: `docs/TYPE_HINTS_GUIDE.md`
- Implementation: Throughout codebase, see `src/` directory

