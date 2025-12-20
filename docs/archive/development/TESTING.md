# 🧪 Testing Guidelines

## Running Tests

```bash
# All tests
pytest tests/

# Specific file
pytest tests/test_rule1.py

# Specific test
pytest tests/test_rule1.py::test_critical_bitrate_detection

# With output
pytest tests/ -v

# With coverage report
pytest tests/ --cov=src --cov-report=html
```

## Test Structure

```
tests/
├── test_rule1.py          # Rule 1 tests
├── test_rule4.py          # Rule 4 tests
├── test_scoring.py        # Scoring engine tests
├── test_new_scoring.py    # Integration tests
├── test_audio_loader_retry.py  # Retry mechanism
└── test_rule1_bitrate_enhancement.py  # Latest tests
```

## Writing Tests

### Basic Test Template

```python
import pytest
from flac_detective.analysis.new_scoring.rules.spectral import apply_rule_1_mp3_bitrate

def test_rule1_basic():
    """Test Rule 1 with basic MP3 signature."""
    # Setup
    cutoff_freq = 20000.0  # MP3 signature
    container_bitrate = 320.0
    
    # Execute
    (score, reasons), estimated_bitrate = apply_rule_1_mp3_bitrate(
        cutoff_freq=cutoff_freq,
        container_bitrate=container_bitrate
    )
    
    # Assert
    assert score == 50  # Rule 1 gives +50 for match
    assert estimated_bitrate == 320
    assert len(reasons) > 0
```

### Parametrized Tests

```python
@pytest.mark.parametrize("cutoff,bitrate,expected_score", [
    (20000.0, 320.0, 50),   # MP3 320k
    (19500.0, 256.0, 50),   # MP3 256k
    (22050.0, 900.0, 0),    # Authentic FLAC
])
def test_rule1_multiple_cases(cutoff, bitrate, expected_score):
    """Test Rule 1 with multiple scenarios."""
    (score, reasons), _ = apply_rule_1_mp3_bitrate(cutoff, bitrate)
    assert score == expected_score
```

## Test Coverage

Current coverage targets:
- **Rules**: 90%+ (critical detection logic)
- **Scoring**: 85%+ (verdict generation)
- **Utils**: 75%+ (helper functions)

Check coverage:
```bash
pytest tests/ --cov=src --cov-report=term-missing
```

## Integration Testing

Test with real FLAC files:

```python
def test_integration_authentic_file():
    """Test with authentic FLAC file."""
    from flac_detective.analysis.analyzer import AudioAnalyzer
    
    analyzer = AudioAnalyzer()
    context = analyzer.analyze_file("tests/samples/authentic.flac")
    
    # Should score ≤ 30
    assert context.score <= 30
    assert context.verdict == "AUTHENTIC"
```

## Test Fixtures

```python
@pytest.fixture
def sample_context():
    """Provide a test scoring context."""
    from flac_detective.analysis.new_scoring.models import ScoringContext
    
    ctx = ScoringContext(
        filepath=Path("test.flac"),
        cutoff_freq=20000.0,
        bitrate_metrics=...,
        audio_meta=...,
    )
    return ctx
```

## Performance Tests

```bash
# Run with timing
pytest tests/ -v --durations=10

# Profile specific test
pytest tests/test_scoring.py -v --profile

# Memory profiling
pytest tests/ --memory
```

## Debugging Failures

```python
# Print debug info
def test_with_debug():
    result = analyze_file("test.flac")
    print(f"\nScore: {result.score}")
    print(f"Reasons: {result.reasons}")
    assert result.score <= 30
```

Run with output:
```bash
pytest tests/test_file.py::test_with_debug -v -s
```

## CI/CD Pipeline

Tests run automatically on:
- **Push** to `main` branch
- **Pull Requests** (must pass to merge)
- **Daily** (scheduled)

Status badge: ![Tests](https://github.com/GuillainM/FLAC_Detective/workflows/Tests/badge.svg)

## Best Practices

✅ **DO:**
- Write tests for new features
- Use descriptive test names
- Test edge cases
- Keep tests independent
- Mock external dependencies

❌ **DON'T:**
- Depend on test execution order
- Use random data (use fixed seeds)
- Test implementation details
- Write overly complex tests
- Skip tests without reason

## Need Help?

- Read [DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md) for environment issues
- Check existing tests for patterns
- Open an issue with test failure details
