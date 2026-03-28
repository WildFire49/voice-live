#!/usr/bin/env python3
"""Build a ChromaDB schema collection from the PostgreSQL knowledge graph.

Reads table/column/view/relationship data from knowledgerag_nodes and
knowledgerag_relationships, then creates a ChromaDB collection with
rich schema documents including enum values.

Usage:
    pip install psycopg2-binary
    python scripts/build_schema_collection.py

Environment variables:
    KG_DB_HOST          - PostgreSQL host (default: 139.84.152.147)
    KG_DB_NAME          - Database name (default: mifix_ai_uat)
    KG_DB_USER          - Database user (default: vaishakh)
    KG_DB_PASSWORD      - Database password
    KG_CONNECTION_ID    - Connection ID to fetch nodes for
    CHROMA_LOCAL_PATH   - Local ChromaDB path (default: data/chromadb)
    CHROMA_HOST         - Remote ChromaDB host (overrides CHROMA_LOCAL_PATH if set)
    CHROMA_PORT         - Remote ChromaDB port (default: 8000)
    CHROMA_SCHEMA_COLLECTION - Collection name to create
"""

import json
import os
import sys
from collections import defaultdict

import chromadb
import psycopg2
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

ARCTIC_MODEL = "Snowflake/snowflake-arctic-embed-m"

# Max distinct values to include in schema docs (avoid huge enum lists)
MAX_ENUM_VALUES = 20


def get_pg_connection():
    return psycopg2.connect(
        host=os.environ.get("KG_DB_HOST", "139.84.152.147"),
        dbname=os.environ.get("KG_DB_NAME", "mifix_ai_uat"),
        user=os.environ.get("KG_DB_USER", "vaishakh"),
        password=os.environ["KG_DB_PASSWORD"],
    )


def fetch_nodes(cur, connection_id: str, node_type: str) -> list[dict]:
    cur.execute(
        """
        SELECT id, name, display_name, description, properties, node_metadata
        FROM config.knowledgerag_nodes
        WHERE connection_id = %s AND node_type = %s
        ORDER BY name
        """,
        (connection_id, node_type),
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def fetch_relationships(cur, connection_id: str, rel_type: str) -> list[dict]:
    cur.execute(
        """
        SELECT r.source_node_id, r.target_node_id,
               s.name AS source_name, s.node_type AS source_type,
               t.name AS target_name, t.node_type AS target_type,
               r.properties
        FROM config.knowledgerag_relationships r
        JOIN config.knowledgerag_nodes s ON r.source_node_id = s.id
        JOIN config.knowledgerag_nodes t ON r.target_node_id = t.id
        WHERE r.connection_id = %s AND r.relationship_type = %s
        """,
        (connection_id, rel_type),
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def build_table_documents(
    tables: list[dict],
    columns: list[dict],
    has_column_rels: list[dict],
) -> list[tuple[str, str, dict]]:
    """Build one document per table with columns and enum values.

    Returns list of (doc_id, document_text, metadata).
    """
    # Group columns by table
    table_id_to_node = {str(t["id"]): t for t in tables}
    columns_by_table: dict[str, list[dict]] = defaultdict(list)

    for col in columns:
        props = col["properties"] or {}
        table_name = props.get("table", "")
        if table_name:
            columns_by_table[table_name].append(col)

    docs = []
    for table in tables:
        props = table["properties"] or {}
        schema = props.get("schema", "staging_dashboard")
        row_count = props.get("row_count", -1)
        full_name = f"{schema}.{table['name']}"

        # Build column list
        table_cols = columns_by_table.get(table["name"], [])
        col_parts = []
        enum_parts = []

        for col in sorted(table_cols, key=lambda c: c["name"]):
            cp = col["properties"] or {}
            dtype = cp.get("data_type", "UNKNOWN")
            flags = []
            if cp.get("is_primary_key"):
                flags.append("PK")
            if cp.get("is_foreign_key"):
                fk_ref = cp.get("foreign_key_ref")
                flags.append(f"FK→{fk_ref}" if fk_ref else "FK")

            flag_str = f" [{','.join(flags)}]" if flags else ""
            col_parts.append(f"{col['name']} ({dtype}{flag_str})")

            # Enum values
            is_enum = cp.get("is_enum") or cp.get("is_enum_candidate")
            distinct_count = cp.get("distinct_count", 0)
            distinct_values = cp.get("distinct_values")

            if is_enum and distinct_values and distinct_count and int(distinct_count) <= MAX_ENUM_VALUES:
                if isinstance(distinct_values, str):
                    try:
                        distinct_values = json.loads(distinct_values)
                    except json.JSONDecodeError:
                        distinct_values = None
                if distinct_values and isinstance(distinct_values, list):
                    vals_str = ", ".join(str(v) for v in distinct_values)
                    enum_parts.append(f"{col['name']}: [{vals_str}]")

        row_info = f" | {row_count:,} rows" if row_count and row_count > 0 else ""
        col_str = ", ".join(col_parts) if col_parts else "no columns"
        enum_str = "\nEnum values: " + " | ".join(enum_parts) if enum_parts else ""

        doc = f"Table: {full_name}{row_info}\nColumns: {col_str}{enum_str}"

        docs.append((
            f"table_{table['name']}",
            doc,
            {"node_type": "table", "schema": schema, "name": table["name"]},
        ))

    return docs


def build_view_documents(
    views: list[dict],
    aggregates_from: list[dict],
) -> list[tuple[str, str, dict]]:
    """Build one document per view with metadata and source tables."""
    # Group source tables by view
    view_sources: dict[str, list[str]] = defaultdict(list)
    for rel in aggregates_from:
        view_sources[rel["source_name"]].append(rel["target_name"])

    docs = []
    for view in views:
        props = view["properties"] or {}
        schema = props.get("schema", "staging_dashboard")
        full_name = f"{schema}.{view['name']}"
        display = view.get("display_name", view["name"])
        desc = view.get("description", "")

        columns = props.get("columns", [])
        join_key = props.get("join_key", "")
        time_period = props.get("time_period", "")
        has_geo = props.get("has_geography_columns", False)
        needs_bm = props.get("needs_branch_master_join", False)

        col_str = ", ".join(columns) if columns else "see schema"
        sources = view_sources.get(view["name"], [])
        source_str = ", ".join(sources) if sources else "unknown"

        parts = [f"View: {full_name} | {display}"]
        if desc:
            parts.append(f"Description: {desc}")
        parts.append(f"Columns: {col_str}")
        if join_key:
            parts.append(f"Join key: {join_key}")
        if time_period:
            parts.append(f"Time period: {time_period}")
        parts.append(f"Has geography columns: {'yes' if has_geo else 'no'}")
        parts.append(f"Needs branch_master JOIN: {'yes' if needs_bm else 'no'}")
        parts.append(f"Source tables: {source_str}")

        doc = "\n".join(parts)
        docs.append((
            f"view_{view['name']}",
            doc,
            {"node_type": "view", "schema": schema, "name": view["name"]},
        ))

    return docs


def main():
    connection_id = os.environ.get(
        "KG_CONNECTION_ID", "28dfbd1e-b53e-475a-95d2-a2e7439eb417",
    )
    chroma_host = os.environ.get("CHROMA_HOST", "")
    chroma_port = int(os.environ.get("CHROMA_PORT", "8000"))
    chroma_path = os.environ.get("CHROMA_LOCAL_PATH", "data/chromadb")
    collection_name = os.environ.get(
        "CHROMA_SCHEMA_COLLECTION", f"schema_{connection_id.replace('-', '_')}",
    )

    print(f"Connection ID: {connection_id}")
    if chroma_host:
        print(f"ChromaDB remote: {chroma_host}:{chroma_port}")
    else:
        print(f"ChromaDB local: {chroma_path}")
    print(f"Collection: {collection_name}")

    # Fetch from PostgreSQL
    print("\nConnecting to PostgreSQL...")
    conn = get_pg_connection()
    cur = conn.cursor()

    tables = fetch_nodes(cur, connection_id, "table")
    columns = fetch_nodes(cur, connection_id, "column")
    views = fetch_nodes(cur, connection_id, "view")
    aggregates = fetch_relationships(cur, connection_id, "aggregates_from")

    print(f"Fetched: {len(tables)} tables, {len(columns)} columns, {len(views)} views, {len(aggregates)} relationships")

    cur.close()
    conn.close()

    # Build documents
    table_docs = build_table_documents(tables, columns, [])
    view_docs = build_view_documents(views, aggregates)
    all_docs = table_docs + view_docs

    print(f"\nBuilt {len(table_docs)} table docs + {len(view_docs)} view docs = {len(all_docs)} total")

    # Show a sample
    if all_docs:
        print(f"\n--- Sample table doc ---\n{table_docs[0][1][:500]}")
        if view_docs:
            print(f"\n--- Sample view doc ---\n{view_docs[0][1][:500]}")

    # Insert into ChromaDB
    print(f"\nCreating ChromaDB collection: {collection_name}")
    arctic_ef = SentenceTransformerEmbeddingFunction(model_name=ARCTIC_MODEL)
    if chroma_host:
        client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
    else:
        client = chromadb.PersistentClient(path=chroma_path)

    # Delete existing collection if it exists
    try:
        client.delete_collection(collection_name)
        print(f"Deleted existing collection: {collection_name}")
    except Exception:
        pass

    collection = client.create_collection(
        name=collection_name,
        embedding_function=arctic_ef,
        metadata={"description": "Database schema with columns and enum values"},
    )

    # Batch insert
    ids = [d[0] for d in all_docs]
    documents = [d[1] for d in all_docs]
    metadatas = [d[2] for d in all_docs]

    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    print(f"Inserted {len(all_docs)} documents into {collection_name}")
    print("\nDone!")


if __name__ == "__main__":
    main()
