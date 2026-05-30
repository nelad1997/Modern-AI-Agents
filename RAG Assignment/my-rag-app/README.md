# Medium RAG Agent — FastAPI on Vercel

A Retrieval-Augmented Generation (RAG) agent that answers questions about a dataset of
~7,600 Medium articles. Built with **FastAPI + LangChain + Pinecone**, deployed as a
serverless Python function on **Vercel**.

## 🌐 Live URL

```
https://my-rag-app-eight.vercel.app
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/prompt` | Ask a question. Returns the answer, the retrieved context, and the augmented prompt. |
| `GET`  | `/api/stats`  | Returns the active hyperparameters (`chunk_size`, `overlap_ratio`, `top_k`). |

---

## 💬 How to talk to the agent

### `POST /api/prompt`

**Request body:**
```json
{ "question": "your question here" }
```

**Response shape:**
```json
{
  "response": "the model's grounded answer ...",
  "context": [
    { "article_id": "123", "title": "...", "chunk": "...", "score": 0.6438 }
  ],
  "Augmented_prompt": {
    "System": "the system prompt ...",
    "User": "the context-augmented user prompt ..."
  }
}
```

### Examples

**curl (bash):**
```bash
curl -s -X POST "https://my-rag-app-eight.vercel.app/api/prompt" \
  -H "Content-Type: application/json" \
  -d '{"question": "List exactly 3 articles about education. Return only the titles."}'
```

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "https://my-rag-app-eight.vercel.app/api/prompt" `
  -Method Post -ContentType "application/json" `
  -Body '{"question": "List exactly 3 articles about education. Return only the titles."}'
```

**Python:**
```python
import requests

res = requests.post(
    "https://my-rag-app-eight.vercel.app/api/prompt",
    json={"question": "List exactly 3 articles about education. Return only the titles."},
).json()

print(res["response"])
for c in res["context"]:
    print(f'{c["score"]:.3f}  {c["title"]}')
```

**Stats:**
```bash
curl -s "https://my-rag-app-eight.vercel.app/api/stats"
# {"chunk_size": 512, "overlap_ratio": 0.2, "top_k": 10}
```

---

## ❓ Example questions

The agent is tuned for four question types (per the assignment):

1. **Precise fact retrieval** —
   *"Find an article that reframes marketing as a conversation with readers, aimed at writers who find self-promotion uncomfortable. Provide the title and author."*

2. **Multi-result topic listing** —
   *"List exactly 3 articles about education. Return only the titles."*

3. **Key-idea summary extraction** —
   *"Find an article that argues past pandemics (such as the bubonic plague) can spur innovation and recovery, and summarise its central argument."*

4. **Recommendation with evidence** —
   *"I want practical, beginner-friendly advice on building habits that actually stick. Which article would you recommend, and why?"*

The system prompt also forces honest refusals (*"I don't know based on the provided
Medium articles data."*) for out-of-corpus questions — e.g. *"Find an article written by
Elon Musk about space exploration"* — so the agent does not hallucinate authors or titles.

---

## ⚙️ Chosen parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| `chunk_size` | **512 tokens** | Token-aware splitting via `tiktoken` (`cl100k_base`). |
| `overlap_ratio` | **0.20** | ~102-token overlap between consecutive chunks. |
| `top_k` | **10** | Chunks retrieved from Pinecone per query. |
| Embedding model | `text-embedding-3-small` | 1536-dim, served via LLMod.ai. |
| Chat model | `gpt-5-mini` | Served via LLMod.ai (`base_url=https://api.llmod.ai/v1`). |
| Vector DB | Pinecone `medium-rag` | 1536-dim, cosine metric, ~27.7k vectors. |

---

## 🔬 Optimization & testing process

The pipeline was validated in **two stages** — cheap local validation first, then full
production ingestion — to avoid burning embedding cost on bad parameters.

### Stage 1 — Local validation on ~300 articles
`scripts/validate_local.py` embeds the first **300 articles** and runs a **local cosine
similarity** search (no Pinecone needed). Embeddings are cached to `embeddings_local.json`
so re-runs are free. This stage was used to:
- sanity-check chunking (`scripts/chunker.py`) and token counts,
- compare `chunk_size` / `overlap_ratio` candidates,
- confirm the 4 question types returned sensible top-k chunks,

before committing to a full embed of the whole corpus.

### Stage 2 — Full ingestion (~7,600 articles)
Once the parameters looked good, `scripts/ingest.py` chunked and embedded the **entire
dataset** and upserted it to the Pinecone `medium-rag` index in batches (embed batch 256,
upsert batch 100).

### Stage 3 — Hyperparameter comparison (overlap 0.15 → 0.20)
We re-embedded the full corpus with a wider overlap and compared retrieval head-to-head:

| | overlap = 0.15 | overlap = 0.20 |
|---|---|---|
| Total vectors | 26,473 | 27,752 |
| Q2 (education) max score | 0.386 | **0.428** |
| Q3 (pandemics) rank of correct article | 8th | **6th** |
| Per-article chunk coverage in top-10 | lower | **higher** |

The wider **0.20** overlap surfaced an extra relevant education article, ranked the correct
pandemics article higher, and gave richer per-article context — with no regressions across
the 4 assignment questions. So `overlap_ratio = 0.20` was adopted as the final value.

### Stage 4 — Behavioral / robustness testing
Beyond the 4 assignment questions we ran edge-case "trap" questions (e.g. articles by Elon
Musk / Malcolm Gladwell that do not exist in the corpus, a "climate change is a hoax"
article) to confirm the agent **refuses** rather than fabricates. All refusals behaved
correctly.

---

## 🛠️ Run locally

```bash
cd my-rag-app
pip install -r requirements.txt
uvicorn api.index:app --reload
# -> http://localhost:8000
```

Create `my-rag-app/.env.local`:
```
LLMOD_API_KEY=...
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=medium-rag
```

## 📁 Files

```
my-rag-app/
├── api/index.py      # FastAPI app — POST /api/prompt, GET /api/stats
├── requirements.txt  # fastapi, langchain, langchain-openai, pinecone, ...
├── vercel.json       # rewrites /api/(.*) -> /api/index.py
└── .env.local        # secrets (gitignored)
```

> **Note on deployment:** responses are serialized with `json.dumps(..., ensure_ascii=True)`
> so non-ASCII characters from article text never trip the Vercel Python runtime's encoding.
