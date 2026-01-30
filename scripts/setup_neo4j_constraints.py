#!/usr/bin/env python3
"""Set up Neo4j constraints and indexes for the coffee-tasting-api.

Usage:
    python scripts/setup_neo4j_constraints.py

This script creates:
- Unique constraints on all node IDs
- Unique constraint on Flavor.name
- Indexes for common query patterns
- Vector indexes for embedding similarity search
"""

import sys

from neo4j import GraphDatabase

from app.core.config import settings


# Unique constraints
CONSTRAINTS = [
    ("coffee_drinker_id", "CREATE CONSTRAINT coffee_drinker_id IF NOT EXISTS FOR (u:CoffeeDrinker) REQUIRE u.id IS UNIQUE"),
    ("roaster_id", "CREATE CONSTRAINT roaster_id IF NOT EXISTS FOR (r:Roaster) REQUIRE r.id IS UNIQUE"),
    ("coffee_id", "CREATE CONSTRAINT coffee_id IF NOT EXISTS FOR (c:Coffee) REQUIRE c.id IS UNIQUE"),
    ("flavor_id", "CREATE CONSTRAINT flavor_id IF NOT EXISTS FOR (f:Flavor) REQUIRE f.id IS UNIQUE"),
    ("flavor_name", "CREATE CONSTRAINT flavor_name IF NOT EXISTS FOR (f:Flavor) REQUIRE f.name IS UNIQUE"),
    ("tasting_id", "CREATE CONSTRAINT tasting_id IF NOT EXISTS FOR (t:Tasting) REQUIRE t.id IS UNIQUE"),
    ("rating_id", "CREATE CONSTRAINT rating_id IF NOT EXISTS FOR (r:Rating) REQUIRE r.id IS UNIQUE"),
]

# Regular indexes for common queries
INDEXES = [
    ("coffee_origin", "CREATE INDEX coffee_origin IF NOT EXISTS FOR (c:Coffee) ON (c.origin_country)"),
    ("coffee_roast", "CREATE INDEX coffee_roast IF NOT EXISTS FOR (c:Coffee) ON (c.roast_level)"),
    ("flavor_category", "CREATE INDEX flavor_category IF NOT EXISTS FOR (f:Flavor) ON (f.category)"),
]

# Vector indexes for embedding similarity search (Neo4j 5.11+)
VECTOR_INDEXES = [
    ("coffee_embedding", """
        CREATE VECTOR INDEX coffee_embedding IF NOT EXISTS
        FOR (c:Coffee) ON c.embedding
        OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}
    """),
    ("flavor_embedding", """
        CREATE VECTOR INDEX flavor_embedding IF NOT EXISTS
        FOR (f:Flavor) ON f.embedding
        OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}
    """),
]


def setup_constraints(uri: str, user: str, password: str) -> None:
    """Set up all constraints and indexes."""
    driver = GraphDatabase.driver(uri, auth=(user, password))

    with driver.session() as session:
        # Create constraints
        print("Creating constraints...")
        for name, query in CONSTRAINTS:
            try:
                session.run(query)
                print(f"  ✓ {name}")
            except Exception as e:
                print(f"  ✗ {name}: {e}")

        # Create indexes
        print("\nCreating indexes...")
        for name, query in INDEXES:
            try:
                session.run(query)
                print(f"  ✓ {name}")
            except Exception as e:
                print(f"  ✗ {name}: {e}")

        # Create vector indexes
        print("\nCreating vector indexes...")
        for name, query in VECTOR_INDEXES:
            try:
                session.run(query)
                print(f"  ✓ {name}")
            except Exception as e:
                print(f"  ✗ {name}: {e}")

    driver.close()
    print("\nSetup complete")


def main() -> None:
    """Main entry point."""
    if not settings.neo4j_configured:
        print("Error: NEO4J_URI and NEO4J_PASSWORD must be set in .env")
        sys.exit(1)

    uri = settings.NEO4J_URI
    user = settings.NEO4J_USER
    password = settings.NEO4J_PASSWORD

    print(f"Setting up Neo4j constraints at: {uri}")
    setup_constraints(uri, user, password)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
