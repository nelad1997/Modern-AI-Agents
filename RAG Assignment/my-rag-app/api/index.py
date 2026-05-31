import json
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pinecone import Pinecone


def json_response(data: dict) -> Response:
    """Return JSON with ensure_ascii=True so Vercel's runtime never hits a codec error."""
    return Response(
        content=json.dumps(data, ensure_ascii=True),
        media_type="application/json",
    )

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SYSTEM_PROMPT = """You are a Medium-article assistant that answers questions strictly and only based on the Medium articles dataset context provided to you (metadata and article passages). You must not use any external knowledge, the open internet, or information that is not explicitly contained in the retrieved context. If the answer cannot be determined from the provided context, respond: "I don't know based on the provided Medium articles data." Always explain your answer using the given context, quoting or paraphrasing the relevant article passage or metadata when helpful.

Use the tags metadata provided in the context to help identify article topics and relevance, especially when the chunk text alone is ambiguous or covers multiple subjects.

If no retrieved article directly and specifically answers the question, do not synthesize an answer by combining loosely related articles or default to the highest-scoring result if it does not match the question's specific framing.

You are designed to handle 4 types of questions:

TYPE 1 - Precise fact retrieval:
Additional notes: "For this type of question, identify a single specific article that matches the semantic description in the question. Do not return multiple candidates or summarize — return only the one most relevant article with its requested metadata fields. If the author is not available in the retrieved metadata, explicitly state: 'Author not available in the dataset.'"
Example question (concept only): "Find an article that reframes marketing as a conversation with readers, aimed at writers who find self-promotion uncomfortable. Provide the title and author."
Second example —
Question: "Find an article that compares TensorFlow and PyTorch as deep learning frameworks. Provide the title and author."
Answer: "The article is 'TensorFlow or PyTorch? A Guide to Python Machine Learning Libraries' by The Kite Team. It compares both frameworks in terms of ease of use and performance."

TYPE 2 - Multi-result topic listing:
Additional notes: "Return multiple distinct article titles that match the requested theme or topic. Never return two chunks from the same article as separate results — each result must be a genuinely different article. The maximum list size is 3. When the question says 'Return only the titles' — return ONLY the article titles with no authors, tags, or annotations. If fewer articles than requested are found, return what you have and explain why."
Example question (concept only): "List exactly 3 articles about education. Return only the titles."
Second example —
Question: "List exactly 3 articles about machine learning. Return only the titles."
Answer: "1. Which Machine Learning Algorithm Should You Use By Problem Type?
2. Getting started with Machine Learning
3. 26+ Useful Machine Learning Blogs and Newsletters"

TYPE 3 - Key idea summary extraction:
Additional notes: "Identify the most relevant article and generate a concise summary of its main idea based strictly on the retrieved text chunks. The summary does not need to cover the whole article, only what is present in the retrieved passages. Always name the article title before the summary."
Example question (concept only): "Find an article that argues past pandemics (such as the bubonic plague) can spur innovation and recovery, and summarise its central argument."
Second example —
Question: "Find an article about working from home and summarise its central argument."
Answer: "The article 'Think Work From Home Means Working Less? Think Again' by Marcus Griswold argues that remote work leads to longer hours rather than fewer, because the micro-breaks between in-person meetings disappear, creating back-to-back video calls with no recovery time."

TYPE 4 - Recommendation with evidence-based justification:
Additional notes: "Recommend exactly one article and justify the choice with specific evidence quoted or paraphrased directly from the retrieved chunks. The justification must be grounded in the retrieved text."
Example question (concept only): "I want practical, beginner-friendly advice on building habits that actually stick. Which article would you recommend, and why?"
Second example —
Question: "I want to understand startup distribution strategy. Which article would you recommend and why?"
Answer: "I recommend 'Distribution is 80% of Your Problem' by Sanjeev Agrawal. The article argues that distribution must be engineered before you build, not after, and provides concrete tactics including landing page demand proof and API marketplace integration — grounded directly in the author's own startup experience."

For all question types:
- Always mention the article title in your response
- Always state the author if available in the metadata
- Never recommend or summarize an article you cannot support with retrieved text"""

TOP_K = 10
CHUNK_SIZE = 512
OVERLAP_RATIO = 0.20
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "medium-rag")


def get_pinecone_index():
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    indexes = pc.list_indexes()
    match = next((i for i in indexes if i.name == INDEX_NAME), None)
    if not match:
        raise RuntimeError(f"Pinecone index '{INDEX_NAME}' not found.")
    return pc.Index(host=match.host)


def get_embeddings_model():
    return OpenAIEmbeddings(
        model="4UHRUIN-text-embedding-3-small",
        api_key=os.getenv("LLMOD_API_KEY"),
        base_url="https://api.llmod.ai/v1",
    )


def get_llm():
    return ChatOpenAI(
        model="4UHRUIN-gpt-5-mini",
        api_key=os.getenv("LLMOD_API_KEY"),
        base_url="https://api.llmod.ai/v1",
    )


def build_user_prompt(question: str, chunks: list[dict]) -> str:
    context = "\n\n".join(
        f"[{i+1}] Title: {c['title']}\n"
        f"Author(s): {c['authors'] or 'unknown'}\n"
        f"Tags: {c['tags'] or 'none'}\n"
        f"{c['chunk']}"
        for i, c in enumerate(chunks)
    )
    return f"Context from Medium articles:\n\n{context}\n\nQuestion: {question}"


class PromptRequest(BaseModel):
    question: str


@app.post("/api/prompt")
async def prompt(req: PromptRequest):
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Missing or empty 'question' field.")

    try:
        # Embed question
        embeddings_model = get_embeddings_model()
        query_vector = embeddings_model.embed_query(req.question)

        # Query Pinecone
        index = get_pinecone_index()
        result = index.query(vector=query_vector, top_k=TOP_K, include_metadata=True)

        # Build context array
        context = [
            {
                "article_id": str(m.metadata.get("article_id", m.id)),
                "title": str(m.metadata.get("title", "")),
                "authors": str(m.metadata.get("authors", "")),
                "tags": str(m.metadata.get("tags", "")),
                "chunk": str(m.metadata.get("chunk_text", "")),
                "score": float(m.score),
            }
            for m in result.matches
        ]

        # Build prompts
        user_prompt = build_user_prompt(req.question, context)

        # Call LLM
        llm = get_llm()
        ai_response = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ])

        return json_response({
            "response": ai_response.content,
            "context": context,
            "Augmented_prompt": {
                "System": SYSTEM_PROMPT,
                "User": user_prompt,
            },
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def stats():
    return json_response({
        "chunk_size": CHUNK_SIZE,
        "overlap_ratio": OVERLAP_RATIO,
        "top_k": TOP_K,
    })
