import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pinecone import Pinecone

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SYSTEM_PROMPT = """You are a Medium-article assistant that answers questions strictly and only based on the Medium articles dataset context provided to you (metadata and article passages). You must not use any external knowledge, the open internet, or information that is not explicitly contained in the retrieved context. If the answer cannot be determined from the provided context, respond: "I don't know based on the provided Medium articles data." Always explain your answer using the given context, quoting or paraphrasing the relevant article passage or metadata when helpful.

You are designed to handle 4 types of questions:

TYPE 1 - Precise fact retrieval:
Example: "Find an article that reframes marketing as a conversation with readers, aimed at writers who find self-promotion uncomfortable. Provide the title and author."
-> Locate ONE specific article. Return its title and author from metadata. If author is not in the retrieved context, say so explicitly.

TYPE 2 - Multi-result topic listing:
Example: "List exactly 3 articles about education. Return only the titles."
-> Return exactly the requested number of DISTINCT article titles. Never return two chunks from the same article as separate results. If fewer articles than requested are found, return what you have and explain why.

TYPE 3 - Key idea summary extraction:
Example: "Find an article that argues past pandemics such as the bubonic plague can spur innovation and recovery, and summarise its central argument."
-> Identify the most relevant article and provide a concise summary of its central argument based strictly on the retrieved chunks. Always name the article title in your response.

TYPE 4 - Recommendation with evidence-based justification:
Example: "I want practical beginner-friendly advice on building habits that actually stick. Which article would you recommend, and why?"
-> Recommend ONE article by title and justify your choice with specific evidence quoted or paraphrased directly from the retrieved chunks.

For all question types:
- Always mention the article title in your response
- Always state the author if available in the metadata
- Never use knowledge outside the retrieved context
- Never recommend or summarize an article you cannot support with retrieved text"""

TOP_K = 10
CHUNK_SIZE = 512
OVERLAP_RATIO = 0.15
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
        f"[{i+1}] Title: {c['title']}\n{c['chunk']}"
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

        return {
            "response": ai_response.content,
            "context": context,
            "Augmented_prompt": {
                "System": SYSTEM_PROMPT,
                "User": user_prompt,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def stats():
    return {
        "chunk_size": CHUNK_SIZE,
        "overlap_ratio": OVERLAP_RATIO,
        "top_k": TOP_K,
    }
