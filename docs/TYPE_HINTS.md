# Type Hints Documentation

This document describes the type hint implementation in FLAC Detective.

## Overview

FLAC Detective uses comprehensive type hints throughout the codebase to improve:
- Code maintainability and readability
- IDE autocompletion and error detection
- Static type checking with mypy
- Documentation clarity

## Type Checking

### Running mypy

```bash
# Check specific file
python -m mypy src/flac_detective/analysis/new_scoring/audio_loader.py --ignore-missing-imports

# Check entire project
python -m mypy src/ --ignore-missing-imports

# With configuration from pyproject.toml
python -m mypy src/ --config-file pyproject.toml
```

### Configuration

Type checking is configured in `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
strict_equality = true
ignore_missing_imports = true
```

## Type Hints in audio_loader.py

The `audio_loader.py` module demonstrates comprehensive type hint usage for the repair functionality.

### Import Types

```python
from typing import Tuple, Optional, Dict, List, Any, Generator
import numpy as np
from numpy.typing import NDArray
```

### Key Type Definitions

**NDArray Types:**
```python
NDArray[np.float64]  # For audio data from soundfile
NDArray[np.float32]  # For processed audio chunks
```

**Metadata Types:**
```python
Dict[str, Any]              # Metadata dictionary
Dict[str, List[str]]        # Tags dictionary
List[Picture]               # Album art pictures
```

**Return Types:**
```python
Tuple[Optional[NDArray[np.float64]], Optional[int]]  # Audio data + sample rate
Tuple[Optional[NDArray[np.float32]], Optional[int], bool]  # Partial read result
Generator[NDArray[np.float32], None, None]  # Streaming audio blocks
```

### Function Examples

**Basic Function:**
```python
def is_temporary_decoder_error(error_message: str) -> bool:
    """Check if an error is a temporary decoder error."""
    ...
```

**Complex Function with Multiple Types:**
```python
def load_audio_with_retry(
    file_path: str,
    max_attempts: int = 5,
    initial_delay: float = 0.2,
    backoff_multiplier: float = 2.0,
    original_filepath: Optional[str] = None,
    **kwargs: Any
) -> Tuple[Optional[NDArray[np.float64]], Optional[int]]:
    """Load audio file with retry mechanism."""
    ...
```

**Metadata Functions:**
```python
def _extract_metadata(flac_path: str) -> Optional[Dict[str, Any]]:
    """Extract all metadata from a FLAC file."""
    ...

def _restore_metadata(
    flac_path: str,
    metadata: Optional[Dict[str, Any]]
) -> bool:
    """Restore metadata to a FLAC file."""
    ...
```

**Repair Function:**
```python
def repair_flac_file(
    corrupted_path: str,
    source_path: Optional[str] = None,
    replace_source: bool = False
) -> Optional[str]:
    """Repair a corrupted FLAC file."""
    ...
```

**Generator Function:**
```python
def sf_blocks(
    file_path: str,
    blocksize: int = 16384,
    dtype: str = "float32",
    max_attempts: int = 5,
    initial_delay: float = 0.2,
    backoff_multiplier: float = 2.0,
) -> Generator[NDArray[np.float32], None, None]:
    """Read audio in chunks with retry mechanism."""
    ...
```

### Variable Annotations

**Module-Level Constants:**
```python
MUTAGEN_AVAILABLE: bool
logger: logging.Logger = logging.getLogger(__name__)
```

**Local Variables:**
```python
tracking_path: str = original_filepath or file_path
delay: float = initial_delay
last_error: Optional[Exception] = None
chunks: List[NDArray[np.float32]] = []
metadata: Optional[Dict[str, Any]] = None
```

## Type Ignore Comments

Some type ignore comments are necessary for third-party library issues:

```python
for key, value in audio.tags:  # type: ignore[union-attr]
```

This is used when:
- Third-party libraries (mutagen) have incomplete type stubs
- The actual runtime behavior is correct but mypy cannot verify it
- The workaround is documented and understood

## Benefits

### 1. IDE Support
Type hints enable:
- Intelligent autocompletion
- Parameter hints
- Error detection before runtime
- Inline documentation

### 2. Static Analysis
mypy can detect:
- Type mismatches
- Missing return statements
- Incorrect function signatures
- Unused variables

### 3. Documentation
Type hints serve as inline documentation:
- Clear parameter types
- Expected return values
- Optional vs required parameters
- Complex nested structures

### 4. Refactoring Safety
When refactoring code, type hints help:
- Identify all usages of a function
- Verify compatibility after changes
- Catch breaking changes early
- Maintain API contracts

## Best Practices

### DO:
✅ Use specific types when possible (`List[str]` not `list`)
✅ Use `Optional[T]` for nullable values
✅ Annotate all function parameters and return types
✅ Use `NDArray[np.float64]` for numpy arrays with known dtype
✅ Use type aliases for complex types
✅ Document why `type: ignore` is needed

### DON'T:
❌ Use `Any` when a more specific type is available
❌ Leave complex functions untyped
❌ Ignore mypy errors without investigation
❌ Mix different typing conventions in same file
❌ Forget to update type hints when changing function signatures

## Type Aliases

For complex repeated types, use type aliases:

```python
from typing import TypeAlias

MetadataDict: TypeAlias = Dict[str, Any]
AudioData: TypeAlias = Tuple[Optional[NDArray[np.float64]], Optional[int]]
PartialAudioData: TypeAlias = Tuple[Optional[NDArray[np.float32]], Optional[int], bool]
```

## Coverage Goals

**Current Status (audio_loader.py):**
- ✅ All functions have type hints
- ✅ All parameters annotated
- ✅ All return types specified
- ✅ Complex types properly defined
- ✅ Module-level variables annotated
- ✅ Zero mypy errors

**Project Goal:**
- Target: 100% type hint coverage for critical modules
- Minimum: 80% type hint coverage project-wide
- All new code must include type hints

## Continuous Integration

Type checking should be part of CI/CD:

```yaml
# .github/workflows/type-check.yml
- name: Type checking
  run: |
    pip install mypy
    mypy src/ --ignore-missing-imports
```

## Resources

- [PEP 484 - Type Hints](https://www.python.org/dev/peps/pep-0484/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [typing Module](https://docs.python.org/3/library/typing.html)
- [numpy.typing](https://numpy.org/doc/stable/reference/typing.html)

## Future Improvements

1. Add type stubs for third-party libraries without types
2. Increase type coverage to other modules
3. Enable stricter mypy settings
4. Add runtime type checking with typeguard for critical functions
5. Generate type documentation automatically
