# TITAN - AI Agent Instructions

## Project

TITAN (Trading Intelligence & Tactical Analysis Network)

Institutional-grade trading intelligence platform focused on disciplined analysis, capital preservation, and modular architecture.

---

## Core Principles

- Never fabricate market data.
- Never fabricate API responses.
- Preserve backward compatibility unless explicitly requested.
- Keep modules small and cohesive.
- Prefer composition over inheritance.
- Write deterministic, testable code.
- Use type hints throughout.

---

## Coding Standards

- Target Python 3.14+
- Follow Black formatting.
- Pass Ruff with zero errors.
- Pass MyPy with zero errors.
- Pass Pytest before considering work complete.

---

## Development Workflow

Before making changes:

1. Read the affected module.
2. Understand existing architecture.
3. Make the smallest correct change.
4. Update tests when behavior changes.
5. Update documentation when appropriate.

After every task run:

ruff check .
black --check .
mypy titan
pytest

---

## Testing Rules

Unit tests:
- No network access.
- No broker API calls.
- No YFinance dependency.

Integration tests:
- Broker SDKs.
- YFinance.
- External APIs.

---

## Broker Layer

Broker implementations must remain optional.

Core TITAN modules must not depend directly on broker SDKs.

Use abstraction interfaces.

---

## Architecture

Keep clear separation:

titan/
    analysis/
    broker/
    config/
    core/
    market/
    options/
    risk/
    execution/
    portfolio/
    cli/

No circular imports.

---

## Documentation

Whenever new functionality is added:

- Update docs.
- Add tests.
- Add type hints.
- Keep public APIs documented.

---

## Goal

Prioritize correctness, maintainability, and capital preservation over adding features quickly.
