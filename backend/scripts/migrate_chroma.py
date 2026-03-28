"""
Migrate ChromaDB collections from prod to local with Snowflake Arctic embeddings.

Usage:
    cd backend && source venv/bin/activate
    python scripts/migrate_chroma.py
"""

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

PROD_HOST = "3.6.132.24"
PROD_PORT = 8000
LOCAL_PATH = "data/chromadb"
ARCTIC_MODEL = "Snowflake/snowflake-arctic-embed-m"

COLLECTIONS = [
    "query_learning_28dfbd1e_b53e_475a_95d2_a2e7439eb417_v1.0.132",
    "business_rules_28dfbd1e_b53e_475a_95d2_a2e7439eb417",
]

BATCH_SIZE = 100


def migrate():
    print(f"Loading Arctic embedding model: {ARCTIC_MODEL}")
    arctic_ef = SentenceTransformerEmbeddingFunction(model_name=ARCTIC_MODEL)

    print(f"Connecting to prod ChromaDB: {PROD_HOST}:{PROD_PORT}")
    prod_client = chromadb.HttpClient(host=PROD_HOST, port=PROD_PORT)

    print(f"Creating local ChromaDB at: {LOCAL_PATH}")
    local_client = chromadb.PersistentClient(path=LOCAL_PATH)

    for col_name in COLLECTIONS:
        print(f"\n--- Migrating: {col_name} ---")

        prod_col = prod_client.get_collection(col_name)
        count = prod_col.count()
        print(f"  Prod docs: {count}")

        if count == 0:
            print("  Skipping empty collection")
            continue

        # Delete local collection if exists, to start fresh
        try:
            local_client.delete_collection(col_name)
        except Exception:
            pass

        local_col = local_client.get_or_create_collection(
            name=col_name,
            embedding_function=arctic_ef,
        )

        # Pull all docs from prod in batches
        offset = 0
        total_migrated = 0
        while offset < count:
            result = prod_col.get(
                limit=BATCH_SIZE,
                offset=offset,
                include=["documents", "metadatas"],
            )

            ids = result["ids"]
            docs = result["documents"]
            metas = result["metadatas"]

            if not ids:
                break

            # Insert into local (Arctic embeddings generated automatically)
            local_col.add(ids=ids, documents=docs, metadatas=metas)
            total_migrated += len(ids)
            print(f"  Migrated {total_migrated}/{count} docs")

            offset += BATCH_SIZE

        print(f"  Done: {local_col.count()} docs in local collection")

    print("\nMigration complete!")
    print(f"Local ChromaDB at: {LOCAL_PATH}")
    print("Update .env: CHROMA_HOST= (empty) and CHROMA_LOCAL_PATH=data/chromadb")


if __name__ == "__main__":
    migrate()
