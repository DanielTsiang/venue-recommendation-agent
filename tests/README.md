# Tests

Comprehensive test suite for the Venue Recommendation Agent.

## Quick Start

```bash
# All tests (unit + integration)
uv run pytest

# Unit tests only (fast, no API keys)
uv run pytest -m "not integration"

# Integration tests only (requires API keys)
uv run pytest -m integration

# With coverage
uv run pytest --cov=src --cov-report=html
```

## Test Structure

```
tests/
├── test_agent.py                # Root agent wiring
├── test_config.py               # Configuration validation
├── test_mcp_server.py           # MCP server tools
├── test_recommendation_agent.py # Recommendation agent + memory callback
├── test_search_agent.py         # Search agent
├── test_yelp_client.py          # Yelp API client
├── integration/
│   └── test_end_to_end.py       # End-to-end with real APIs
├── conftest.py                  # Shared fixtures
└── README.md
```

## Unit vs Integration

| | Unit Tests | Integration Tests |
|---------|-----------|-------------------|
| **Speed** | Fast (< 5s) | Slower (real APIs) |
| **API Keys** | Not required | Required in `.env` |
| **Mocking** | Full mocking | Minimal mocking |
| **When** | Always (CI/local) | Before releases |
| **Marker** | None | `@pytest.mark.integration` |

## API Keys

Integration tests require valid keys in `.env`:

```env
YELP_API_KEY=your_actual_yelp_api_key
GOOGLE_API_KEY=your_actual_google_api_key
```

**Behavior:**
- ✅ Valid keys → Tests run
- ⏭️ Missing keys → Tests skipped
- ❌ Placeholder keys → Error raised

## Test Pattern

All tests use **Given-When-Then**:

```python
def test_example(self, mocker):
    # Given: Setup
    mock = mocker.Mock()

    # When: Action
    result = function(mock)

    # Then: Assertions
    assert result == expected
```

## Common Issues

**Tests skipped:**
```bash
cp .env.example .env  # Add real API keys
```

**ImportError:**
```bash
cd /path/to/project && uv run pytest
```

**Timeouts:**
```bash
uv run pytest -m "not integration"  # Skip slow tests
```

## CI/CD

```yaml
# Always run unit tests
- run: uv run pytest -m "not integration"

# Run integration with secrets
- env:
    YELP_API_KEY: ${{ secrets.YELP_API_KEY }}
    GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
  run: uv run pytest -m integration
```
