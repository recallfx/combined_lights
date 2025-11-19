---
description: Run tests using uv
---

To run tests for this project, use `uv run pytest`.

1. Run all tests:
```bash
uv run pytest
```

2. Run a specific test file:
```bash
uv run pytest tests/combined_lights/test_feedback_loops.py
```

3. Run a specific test function:
```bash
uv run pytest tests/combined_lights/test_feedback_loops.py::test_context_clobbering_race_condition
```
