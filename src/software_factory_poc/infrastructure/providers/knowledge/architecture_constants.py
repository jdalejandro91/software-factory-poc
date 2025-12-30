SHOPPING_CART_ARCHITECTURE = """
# Shopping Cart Architecture (Modular Monolith)

## Overview
The Shopping Cart module follows a Modular Monolith architecture within the E-commerce system.
It is designed to be purely domain-centric, isolated from external frameworks.

## Key Components
1. **Cart Entity**: Aggregate root. Manages items and total calculation.
2. **Pricing Service**: Domain service for calculating discounts and taxes.
3. **Inventory Port**: Interface for checking stock availability.

## Technical Constraints
- Use Python 3.12+
- Use Pydantic for Value Objects
- No direct database dependencies in Domain layer (use Repository pattern)
"""

DEFAULT_ARCHITECTURE = """
# General Architecture Guidelines

## Overview
Follow Clean Architecture principles.
- Isolate Domain from Infrastructure.
- Use Ports and Adapters.
"""
