"""
Step 3: Local Validation
- Embed 300 articles via LangChain OpenAIEmbeddings (LLMod.ai)
- Cache embeddings to embeddings_local.json (skip if already exists)
- Cosine similarity search locally
- Test 4 question types
"""

import csv
import json
import math
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from langchain_openai import OpenAIEmbeddings

from chunker import chunk_text

EMBEDDINGS_FILE = Path(__file__).parent / "embeddings_local.json"
CSV_PATH = Path(__file__).parent.parent / "medium-english-50mb.csv"
NUM_ARTICLES = 300
CHUNK_SIZE = 512
OVERLAP_RATIO = 0.15
TOP_K = 7


def load_articles(n: int) -> list[dict]:
    articles = []
    with open(CSV_PATH, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= n:
                break
            articles.append({"article_id": str(i), "title": row["title"], "url": row["url"], "text": row["text"]})
    return articles


def build_chunks(articles: list[dict]) -> list[dict]:
    records = []
    for article in articles:
        chunks = chunk_text(article["text"], CHUNK_SIZE, OVERLAP_RATIO)
        for idx, chunk in enumerate(chunks):
            records.append({
                "article_id": article["article_id"],
                "title": article["title"],
                "url": article["url"],
                "chunk_index": idx,
                "chunk_text": chunk,
            })
    return records


def embed_and_save(records: list[dict]) -> list[dict]:
    embeddings_model = OpenAIEmbeddings(
        model="4UHRUIN-text-embedding-3-small",
        api_key=os.getenv("LLMOD_API_KEY"),
        base_url="https://api.llmod.ai/v1",
        chunk_size=256,
    )

    texts = [r["chunk_text"] for r in records]
    print(f"Embedding {len(texts)} chunks in batches of 256...")
    vectors = embeddings_model.embed_documents(texts)

    for record, vector in zip(records, vectors):
        record["embedding"] = vector

    with open(EMBEDDINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f)
    print(f"Saved {len(records)} embedded chunks to {EMBEDDINGS_FILE}")
    return records


def load_embeddings() -> list[dict]:
    with open(EMBEDDINGS_FILE, encoding="utf-8") as f:
        return json.load(f)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def search(query: str, records: list[dict], top_k: int = TOP_K) -> list[dict]:
    embeddings_model = OpenAIEmbeddings(
        model="4UHRUIN-text-embedding-3-small",
        api_key=os.getenv("LLMOD_API_KEY"),
        base_url="https://api.llmod.ai/v1",
    )
    query_vec = embeddings_model.embed_query(query)

    scored = [
        {**r, "score": cosine_similarity(query_vec, r["embedding"])}
        for r in records
    ]
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def print_results(question: str, results: list[dict]):
    print(f"\n{'='*70}")
    print(f"Q: {question}")
    print(f"{'='*70}")
    for i, r in enumerate(results, 1):
        print(f"\n  [{i}] score={r['score']:.4f} | article_id={r['article_id']}")
        print(f"      title: {r['title'][:70]}")
        print(f"      chunk: {r['chunk_text'][:150].strip()}...")


if __name__ == "__main__":
    # Load or build embeddings
    if EMBEDDINGS_FILE.exists():
        print(f"Found existing embeddings file — loading (skipping re-embed).")
        records = load_embeddings()
    else:
        print(f"No embeddings file found. Loading {NUM_ARTICLES} articles...")
        articles = load_articles(NUM_ARTICLES)
        records = build_chunks(articles)
        print(f"Built {len(records)} chunks from {NUM_ARTICLES} articles.")
        records = embed_and_save(records)

    print(f"\nLoaded {len(records)} embedded chunks.")

    # 4 question types
    questions = [
        # 1. Factual / specific fact
        "What are the effects of COVID-19 on the human brain?",
        # 2. Topic / concept explanation
        "How does smell training affect the brain?",
        # 3. Author / metadata-adjacent
        "What articles are written about mental health and psychology?",
        # 4. Broad / thematic
        "How does isolation affect young adults mentally?",
    ]

    for question in questions:
        results = search(question, records)
        print_results(question, results)
