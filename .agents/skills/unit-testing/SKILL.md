---
name: unit-testing
description: Generates isolated, zero-I/O unit tests using pytest. Use when testing Domain entities, Application Skills, or Agents using fakes and mocks.
---
# Unit Testing Skill

## When to use this skill
- Use this when writing tests for `core/domain/` and `core/application/`.

## How to use it
1. **ZERO I/O**: Unit tests MUST NOT hit the network, filesystem, or real databases.
2. **AAA Pattern**: Follow Arrange, Act, Assert clearly separated by blank lines. Explicitly test validation errors.

## Decision Tree: Mocking Strategy
- **Testing Application logic that interacts with State (e.g., `RunStorePort`)?**
  - *Action*: Build in-memory "Fake" implementations (e.g., `FakeRunStore`). Do not use `MagicMock`.
- **Testing Application logic that calls external APIs via Ports (e.g., `TrackerPort`)?**
  - *Action*: Use `unittest.mock.AsyncMock` or `MagicMock` for the Ports. Assert that they were called with the correct pure Domain Value Objects.