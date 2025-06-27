import os
import sys
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from query.chatbot_response import generate_chat_response
from query.query_db import search_db

app = FastAPI(
    title="TIPQIC RAG Chatbot API",
    description="API for the TIPQIC RAG Chatbot system",
    version="1.0.0",
)

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for request/response
class ChatRequest(BaseModel):
    message: str
    max_results: Optional[int] = 5
    include_sources: Optional[bool] = True


class SourceInfo(BaseModel):
    filename: str
    page: str
    score: float
    preview: str


class ChatResponse(BaseModel):
    response: str
    sources: List[SourceInfo]
    timestamp: str
    success: bool
    error_message: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str


@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information."""
    return {
        "message": "TIPQIC RAG Chatbot API",
        "version": "1.0.0",
        "endpoints": {"chat": "/api/chat", "health": "/api/health", "docs": "/docs"},
    }


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy", timestamp=datetime.now().isoformat(), version="1.0.0"
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint for processing user queries."""
    try:
        # Search the database
        results = search_db(request.message)

        if not results:
            return ChatResponse(
                response="I couldn't find relevant information in the documents to answer your question. Could you try rephrasing it or asking about a different topic?",
                sources=[],
                timestamp=datetime.now().isoformat(),
                success=True,
            )

        # Generate AI response
        ai_response = generate_chat_response(request.message, results)

        # Prepare sources information
        sources_info = []
        if request.include_sources:
            for doc, score in results[: request.max_results]:
                source_filename = os.path.basename(
                    doc.metadata.get("source", "Unknown")
                )
                page = str(doc.metadata.get("page", "N/A"))
                preview = doc.page_content[:200].replace("\n", " ").strip()

                sources_info.append(
                    SourceInfo(
                        filename=source_filename,
                        page=page,
                        score=score,
                        preview=preview,
                    )
                )

        return ChatResponse(
            response=ai_response,
            sources=sources_info,
            timestamp=datetime.now().isoformat(),
            success=True,
        )

    except Exception as e:
        # Log the error (in production, use proper logging)
        print(f"Error in chat endpoint: {str(e)}")

        return ChatResponse(
            response="I'm sorry, I encountered an error while processing your request. Please try again.",
            sources=[],
            timestamp=datetime.now().isoformat(),
            success=False,
            error_message=str(e),
        )


@app.get("/api/stats", response_model=dict)
async def get_stats():
    """Get basic statistics about the knowledge base."""
    try:
        # You can implement this to show database stats
        return {
            "status": "available",
            "timestamp": datetime.now().isoformat(),
            "message": "Statistics endpoint - implement based on your Chroma DB",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)