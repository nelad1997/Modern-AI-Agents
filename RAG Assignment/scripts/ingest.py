"""
Step 5: Full Embedding & Upsert
- Processes all ~7,600 articles in batches
- Skips upsert if Pinecone index already has vectors
- Stores metadata: article_id, title, url, chunk_text
"""

import ast
import csv
import os
import sys
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
OVERLAP_RATIO = 0.20
EMBED_BATCH_SIZE = 256
UPSERT_BATCH_SIZE = 100


def clean_list_field(raw: str) -> str:
    """Turn a stringified list like "['Shaunta Grimes']" or
    "['machine learning', 'python']" into a plain comma-separated string
    ("Shaunta Grimes" / "machine learning, python"). Falls back to a manual
    bracket/quote strip if the value isn't a valid Python literal."""
    if not raw:
        return ""
    raw = raw.strip()
    try:
        parsed = ast.literal_eval(raw)
        if isinstance(parsed, (list, tuple)):
            return ", ".join(str(x).strip() for x in parsed if str(x).strip())
        return str(parsed).strip()
    except (ValueError, SyntaxError):
        return raw.strip("[]").replace("'", "").replace('"', "").strip()


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
                "authors": clean_list_field(row.get("authors", "")),
                "tags": clean_list_field(row.get("tags", "")),
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
                "authors": article["authors"],
                "tags": article["tags"],
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
                    "authors": r["authors"],
                    "tags": r["tags"],
                    "chunk_text": r["chunk_text"],
                },
            }
            for r, v in zip(batch_records, batch_vectors)
        ]
        index.upsert(vectors=upsert_data)
        print(f"  Upserted {min(i + UPSERT_BATCH_SIZE, total)}/{total} chunks...")


def metadata_only_update(index, records: list[dict], max_workers: int = 16):
    """Update ONLY the authors/tags metadata on existing vectors, by id.
    No embedding/upsert — vectors are unchanged, other metadata keys are kept."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    total = len(records)
    done = 0

    def _update(r):
        index.update(
            id=r["id"],
            set_metadata={"authors": r["authors"], "tags": r["tags"]},
        )

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_update, r) for r in records]
        for f in as_completed(futures):
            f.result()
            done += 1
            if done % 500 == 0 or done == total:
                print(f"  Updated metadata {done}/{total} chunks...")


def main():
    force = "--force" in sys.argv
    metadata_only = "--metadata-only" in sys.argv
    api_key = os.getenv("PINECONE_API_KEY")
    llmod_key = os.getenv("LLMOD_API_KEY")
    if not api_key or api_key == "your_key_here":
        raise ValueError("PINECONE_API_KEY is not set in .env")
    # Embeddings key is only needed when we actually re-embed.
    if not metadata_only and (not llmod_key or llmod_key == "your_key_here"):
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

    # Metadata-only: chunk locally to reproduce ids, then patch authors/tags.
    if metadata_only:
        if existing_count == 0:
            raise RuntimeError("Index is empty — run a full ingest first, not --metadata-only.")
        print(f"Metadata-only update over {existing_count} existing vectors "
              "(no re-embedding).")
        print("Loading all articles from CSV...")
        articles = load_all_articles()
        print(f"Loaded {len(articles)} articles.")
        print("Chunking articles to reproduce vector ids...")
        records = build_all_chunks(articles)
        print(f"Built {len(records)} chunk ids. Patching authors/tags metadata...")
        metadata_only_update(index, records)
        print("\nDone. Metadata (authors/tags) updated in place.")
        return

    if existing_count > 0 and not force:
        print(f"Pinecone index already has {existing_count} vectors — skipping ingest.")
        print("Re-run with --force to re-embed and overwrite metadata (authors/tags).")
        return
    if existing_count > 0:
        print(f"--force: re-ingesting over {existing_count} existing vectors "
              "(same ids will be overwritten in place).")

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
