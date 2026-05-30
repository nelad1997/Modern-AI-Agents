# Modern AI Agents — RAG Assignment

A Retrieval-Augmented Generation (RAG) application built with Python/FastAPI, LangChain, Pinecone, and deployed on Vercel.

**🌐 Live agent:** https://my-rag-app-eight.vercel.app
**📖 Full agent docs** (usage examples, parameters, optimization/testing writeup): [`RAG Assignment/my-rag-app/README.md`](RAG%20Assignment/my-rag-app/README.md)

## What it does

Answers questions about a dataset of ~7,600 Medium articles by:
1. Embedding the question using `text-embedding-3-small` via LLMod.ai
2. Retrieving the top-10 most relevant article chunks from a Pinecone vector index
3. Generating a grounded answer using `gpt-5-mini` — strictly from the retrieved context

## Project structure

```
RAG Assignment/
├── my-rag-app/          # FastAPI app (Vercel deployment)
│   ├── api/index.py     # Both endpoints: POST /api/prompt, GET /api/stats
│   ├── requirements.txt
│   └── vercel.json
└── scripts/             # Ingestion pipeline
    ├── chunker.py       # Token-aware chunking (512 tokens, 20% overlap)
    ├── ingest.py        # Embeds & upserts all articles to Pinecone
    ├── setup_pinecone.py
    └── validate_local.py
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/prompt` | Ask a question — returns answer, retrieved context, and augmented prompt |
| `GET`  | `/api/stats`  | Returns chunking parameters (`chunk_size`, `overlap_ratio`, `top_k`) |

## Run locally

```bash
cd RAG\ Assignment/my-rag-app
pip install -r requirements.txt
uvicorn api.index:app --reload
```

Add a `.env.local` file with:
```
LLMOD_API_KEY=...
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=medium-rag
```

## Stack

- **FastAPI** — Python API framework
- **LangChain** — LLM + embeddings orchestration
- **Pinecone** — Vector database (index: `medium-rag`, 1536-dim, cosine)
- **LLMod.ai** — OpenAI-compatible API proxy
- **Vercel** — Serverless Python deployment
