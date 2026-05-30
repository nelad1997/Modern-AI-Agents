import tiktoken

_enc = tiktoken.get_encoding("cl100k_base")


def chunk_text(text: str, chunk_size: int = 512, overlap_ratio: float = 0.15) -> list[str]:
    """Split text into token-bounded chunks with overlap."""
    overlap = int(chunk_size * overlap_ratio)
    step = chunk_size - overlap

    tokens = _enc.encode(text)
    if not tokens:
        return []

    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunks.append(_enc.decode(tokens[start:end]))
        if end == len(tokens):
            break
        start += step

    return chunks


if __name__ == "__main__":
    import csv
    import statistics

    csv_path = "medium-english-50mb.csv"
    articles = []
    with open(csv_path, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 5:
                break
            articles.append(row)

    chunk_counts = []
    for i, article in enumerate(articles):
        chunks = chunk_text(article["text"])
        chunk_counts.append(len(chunks))
        print(f"\nArticle {i}: '{article['title'][:60]}'")
        print(f"  Text length : {len(article['text'])} chars")
        print(f"  Token count : {len(_enc.encode(article['text']))}")
        print(f"  Chunks      : {len(chunks)}")
        print(f"  Chunk 0 preview: {repr(chunks[0][:80])}")
        if len(chunks) > 1:
            print(f"  Chunk 1 preview: {repr(chunks[1][:80])}")

    print(f"\n=== SUMMARY (5 articles) ===")
    print(f"  chunk_size    : 512 tokens")
    print(f"  overlap_ratio : 0.15  ({int(512*0.15)} token overlap)")
    print(f"  Chunks per article: {chunk_counts}")
    print(f"  Average chunks/article: {statistics.mean(chunk_counts):.1f}")
