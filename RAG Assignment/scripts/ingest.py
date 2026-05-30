"""
Step 5: Full Embedding & Upsert
- Processes all ~7,600 articles in batches
- Skips upsert if Pinecone index already has vectors
- Stores metadata: article_id, title, url, chunk_text
"""

import csv
import os
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone

from chunker import chunk_text

CSV_PATH = Path(__file__).parent.parent / "medium-english-50mb.csv"
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "medium-rag")
CHUNK_SIZE = 512
OVERLAP_RATIO = 0.15
EMBED_BATCH_SIZE = 256
UPSERT_BATCH_SIZE = 100


def load_all_articles() -> list[dict]:
    articles = []
    with open(CSV_PATH, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            articles.append({
                "article_id": str(i),
                "title": row["title"],
                "url": row["url"],
                "text": row["text"],
            })
    return articles


def build_all_chunks(articles: list[dict]) -> list[dict]:
    records = []
    for article in articles:
        chunks = chunk_text(article["text"], CHUNK_SIZE, OVERLAP_RATIO)
        for idx, chunk in enumerate(chunks):
            records.append({
                "id": f"{article['article_id']}_{idx}",
                "article_id": article["article_id"],
                "title": article["title"],
                "url": article["url"],
                "chunk_text": chunk,
            })
    return records


def embed_in_batches(texts: list[str], embeddings_model) -> list[list[float]]:
    all_vectors = []
    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[i:i + EMBED_BATCH_SIZE]
        vecs = embeddings_model.embed_documents(batch)
        all_vectors.extend(vecs)
        print(f"  Embedded {min(i + EMBED_BATCH_SIZE, len(texts))}/{len(texts)} chunks...")
    return all_vectors


def upsert_to_pinecone(index, records: list[dict], vectors: list[list[float]]):
    total = len(records)
    for i in range(0, total, UPSERT_BATCH_SIZE):
        batch_records = records[i:i + UPSERT_BATCH_SIZE]
        batch_vectors = vectors[i:i + UPSERT_BATCH_SIZE]
        upsert_data = [
            {
                "id": r["id"],
                "values": v,
                "metadata": {
                    "article_id": r["article_id"],
                    "title": r["title"],
                    "url": r["url"],
                    "chunk_text": r["chunk_text"],
                },
            }
            for r, v in zip(batch_records, batch_vectors)
        ]
        index.upsert(vectors=upsert_data)
        print(f"  Upserted {min(i + UPSERT_BATCH_SIZE, total)}/{total} chunks...")


def main():
    api_key = os.getenv("PINECONE_API_KEY")
    llmod_key = os.getenv("LLMOD_API_KEY")
    if not api_key or api_key == "your_key_here":
        raise ValueError("PINECONE_API_KEY is not set in .env")
    if not llmod_key or llmod_key == "your_key_here":
        raise ValueError("LLMOD_API_KEY is not set in .env")

    pc = Pinecone(api_key=api_key)

    # Resolve host from index list to avoid describe-endpoint 404
    indexes = pc.list_indexes()
    match = next((i for i in indexes if i.name == INDEX_NAME), None)
    if match is None:
        raise RuntimeError(f"Index '{INDEX_NAME}' not found in Pinecone. Create it first.")
    index = pc.Index(host=match.host)

    stats = index.describe_index_stats()
    existing_count = stats.total_vector_count
    if existing_count > 0:
        print(f"Pinecone index already has {existing_count} vectors — skipping ingest.")
        return

    embeddings_model = OpenAIEmbeddings(
        model="4UHRUIN-text-embedding-3-small",
        api_key=llmod_key,
        base_url="https://api.llmod.ai/v1",
        chunk_size=EMBED_BATCH_SIZE,
    )

    print("Loading all articles from CSV...")
    articles = load_all_articles()
    print(f"Loaded {len(articles)} articles.")

    print("Chunking articles...")
    records = build_all_chunks(articles)
    print(f"Built {len(records)} chunks total.")

    print(f"\nEmbedding {len(records)} chunks (batch_size={EMBED_BATCH_SIZE})...")
    texts = [r["chunk_text"] for r in records]
    vectors = embed_in_batches(texts, embeddings_model)

    print(f"\nUpserting to Pinecone (batch_size={UPSERT_BATCH_SIZE})...")
    upsert_to_pinecone(index, records, vectors)

    time.sleep(5)
    final_stats = index.describe_index_stats()
    print(f"\nDone. Total vectors in index: {final_stats.total_vector_count}")


if __name__ == "__main__":
    main()
