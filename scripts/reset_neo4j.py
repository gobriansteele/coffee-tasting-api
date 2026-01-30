#!/usr/bin/env python3
"""Reset Neo4j database - drops all constraints, indexes, and data.

Usage:
    python scripts/reset_neo4j.py

WARNING: This will delete ALL data in the Neo4j database.
"""

import sys

from neo4j import GraphDatabase

from app.core.config import settings


def reset_database(uri: str, user: str, password: str) -> None:
    """Reset the Neo4j database by dropping all constraints, indexes, and data."""
    driver = GraphDatabase.driver(uri, auth=(user, password))

    with driver.session() as session:
        # Drop all constraints
        print("Dropping constraints...")
        constraints = session.run("SHOW CONSTRAINTS").data()
        for c in constraints:
            constraint_name = c.get("name")
            if constraint_name:
                print(f"  Dropping constraint: {constraint_name}")
                session.run(f"DROP CONSTRAINT {constraint_name}")

        # Drop all indexes (except lookup indexes)
        print("Dropping indexes...")
        indexes = session.run("SHOW INDEXES YIELD name, type WHERE type <> 'LOOKUP'").data()
        for i in indexes:
            index_name = i.get("name")
            if index_name:
                print(f"  Dropping index: {index_name}")
                session.run(f"DROP INDEX {index_name}")

        # Delete all data
        print("Deleting all nodes and relationships...")
        result = session.run("MATCH (n) DETACH DELETE n RETURN count(n) as deleted")
        deleted = result.single()
        if deleted:
            print(f"  Deleted {deleted['deleted']} nodes")

    driver.close()
    print("Database reset complete")


def main() -> None:
    """Main entry point."""
    if not settings.neo4j_configured:
        print("Error: NEO4J_URI and NEO4J_PASSWORD must be set in .env")
        sys.exit(1)

    uri = settings.NEO4J_URI
    user = settings.NEO4J_USER
    password = settings.NEO4J_PASSWORD

    # Confirm with user
    print(f"This will reset the Neo4j database at: {uri}")
    print("WARNING: All data will be permanently deleted!")
    response = input("Type 'yes' to confirm: ")

    if response.lower() != "yes":
        print("Aborted")
        sys.exit(0)

    reset_database(uri, user, password)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
