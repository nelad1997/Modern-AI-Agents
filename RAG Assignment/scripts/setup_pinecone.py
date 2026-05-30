"""
Step 4: Pinecone Setup
Creates the 'medium-rag' index (dimension=1536, metric=cosine) if it doesn't exist.
Safe to re-run — skips creation if index already exists.
"""

import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "medium-rag")
DIMENSION = 1536
METRIC = "cosine"


def main():
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key or api_key == "your_key_here":
        raise ValueError("PINECONE_API_KEY is not set in .env")

    pc = Pinecone(api_key=api_key)

    existing = [idx.name for idx in pc.list_indexes()]
    if INDEX_NAME in existing:
        print(f"Index '{INDEX_NAME}' already exists — nothing to do.")
    else:
        print(f"Creating index '{INDEX_NAME}' (dim={DIMENSION}, metric={METRIC})...")
        pc.create_index(
            name=INDEX_NAME,
            dimension=DIMENSION,
            metric=METRIC,
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        print(f"Index '{INDEX_NAME}' created successfully.")

    index = pc.Index(INDEX_NAME)
    stats = index.describe_index_stats()
    print(f"\nIndex stats:")
    print(f"  Total vectors : {stats.total_vector_count}")
    print(f"  Dimension     : {stats.dimension}")


if __name__ == "__main__":
    main()
