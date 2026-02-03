"""
Celebrity Question API Server
FastAPI server that wraps the LangGraph Celebrity Question system
"""

# Fix for segmentation fault on Mac with Python 3.13 - MUST be before any imports
import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import logging
from dotenv import load_dotenv
import asyncio
from agent.graph import CelebrityQuestionGraph

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Celebrity Question API",
    description="AI-powered celebrity question answering system using LangGraph",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default port
        "http://localhost:3000",  # Create React App port
        "http://localhost:8080",  # Alternative Vite/dev port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the graph (singleton)
graph = None


def get_graph() -> CelebrityQuestionGraph:
    """Get or initialize the Celebrity Question Graph"""
    global graph
    if graph is None:
        logger.info("Initializing Celebrity Question Graph...")
        graph = CelebrityQuestionGraph()
        logger.info("Graph initialized successfully")
    return graph


# Request/Response models
class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    celebrity_name: str = Field(..., description="Name of the celebrity")
    question: str = Field(..., description="User's question", alias="question")
    force_ingest: bool = Field(False, description="Force re-ingestion of data")

    class Config:
        populate_by_name = True


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    answer: Optional[str] = Field(None, description="Generated answer")
    decision: Optional[str] = Field(None, description="Decision made (ingest/retrieve)")
    decision_reasoning: Optional[str] = Field(None, description="Reasoning for the decision")
    matches_count: int = Field(0, description="Number of matches found")
    error: Optional[str] = Field(None, description="Error message if any")


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    message: str


# Endpoints
@app.get("/", response_model=dict)
async def root():
    """Root endpoint"""
    return {
        "message": "Celebrity Question API is running",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    # Check if CLAUDE_KEY is configured
    api_key = os.getenv("CLAUDE_KEY")
    if not api_key:
        return HealthResponse(
            status="warning",
            message="API is running but CLAUDE_KEY is not configured"
        )

    return HealthResponse(
        status="ok",
        message="API is healthy"
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a chat message and return AI-generated response

    Args:
        request: ChatRequest with celebrity_name and question

    Returns:
        ChatResponse with answer and metadata
    """
    try:
        # Validate inputs
        if not request.celebrity_name or not request.question:
            raise HTTPException(
                status_code=400,
                detail="Both celebrity_name and question are required"
            )

        # Check API key
        api_key = os.getenv("CLAUDE_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="CLAUDE_KEY not configured. Please set it in your .env file"
            )

        logger.info(f"Processing question for {request.celebrity_name}: {request.question}")

        # Get graph instance
        celebrity_graph = get_graph()

        # Run the graph (blocking operation, so we run it in a thread pool)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            celebrity_graph.run,
            request.celebrity_name,
            request.question,
            request.force_ingest
        )

        logger.info(f"Generated answer for {request.celebrity_name}")

        # Return response
        return ChatResponse(
            answer=result.get('answer'),
            decision=result.get('decision'),
            decision_reasoning=result.get('decision_reasoning'),
            matches_count=result.get('matches_count', 0),
            error=result.get('error')
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    print("\n" + "="*60)
    print("🚀 Starting Celebrity Question API Server...")
    print("="*60)
    print("📡 API will be available at: http://localhost:8000")
    print("📖 API docs available at: http://localhost:8000/docs")
    print("="*60 + "\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
